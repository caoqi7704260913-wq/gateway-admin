"""
服务来源认证中间件

只允许以下来源访问 Admin 服务：
1. Gateway（通过 X-Forwarded-By Header 标识）
2. 已在 Redis/Consul 中注册的内部服务
"""
from typing import Optional, Set, List
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger
from config.settings import settings
from app.utils.path_matcher import parse_public_paths, is_public_path


class ServiceSourceAuthMiddleware(BaseHTTPMiddleware):
    """
    服务来源认证中间件
    
    验证请求来源是否为：
    - Gateway
    - 已注册到 Redis/Consul 的内部服务
    """
    
    def __init__(self, app, redis_manager=None, consul_manager=None):
        super().__init__(app)
        self.redis = redis_manager
        self.consul = consul_manager
        
        # 从配置读取公开路径
        self.public_patterns = parse_public_paths(settings.PUBLIC_PATHS)
        logger.info(f"Public paths loaded: {self.public_patterns}")
        
        # 缓存已注册的服务列表（性能优化）
        self._registered_services_cache: Set[str] = set()
        self._cache_ttl = 60  # 缓存 60 秒
        self._last_update = 0
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        
        # 跳过公开端点
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # 获取请求来源信息
        client_host = request.client.host if request.client else None
        service_name_header = request.headers.get("X-Service-Name")
        forwarded_by = request.headers.get("X-Forwarded-By")
        
        # 判断请求来源
        is_from_gateway = forwarded_by == "gateway"
        is_from_registered_service = await self._is_from_registered_service(
            service_name_header, client_host
        )
        
        # 安全策略：只允许 Gateway 或已注册服务
        if not (is_from_gateway or is_from_registered_service):
            logger.warning(
                f"🚫 Unauthorized access attempt from {client_host} "
                f"(Service: {service_name_header}) to {request.url.path}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "code": 403,
                    "message": "Forbidden: Only Gateway or registered services can access this endpoint",
                    "data": None
                }
            )
        
        # 记录请求来源
        if is_from_gateway:
            request.state.caller_source = "gateway"
            request.state.caller_service = "gateway"
            logger.debug(f"✅ Access allowed from Gateway to {request.url.path}")
        else:
            request.state.caller_source = "internal_service"
            request.state.caller_service = service_name_header
            logger.debug(f"✅ Access allowed from {service_name_header} to {request.url.path}")
        
        return await call_next(request)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """
        判断是否是公开端点（不需要来源验证）
        
        从配置文件读取公开路径列表，支持通配符
        """
        return is_public_path(path, self.public_patterns)
    
    async def _is_from_registered_service(
        self, 
        service_name: Optional[str], 
        client_host: Optional[str]
    ) -> bool:
        """
        判断请求是否来自已注册的服务
        
        验证步骤：
        1. 检查服务名是否在 Redis/Consul 注册列表中
        2. （可选）验证 IP 地址是否匹配注册的实例
        """
        
        if not service_name:
            return False
        
        # 从缓存或注册中心获取已注册的服务列表
        registered_services = await self._get_registered_services()
        
        # 检查服务名是否在注册列表中
        if service_name in registered_services:
            logger.debug(f"✅ Service '{service_name}' is registered")
            
            # 可选：进一步验证 IP 地址
            # if client_host and not await self._verify_service_ip(service_name, client_host):
            #     logger.warning(f"⚠️ Service '{service_name}' IP mismatch: {client_host}")
            #     return False
            
            return True
        
        logger.warning(f"❌ Service '{service_name}' is NOT registered")
        return False
    
    async def _get_registered_services(self) -> Set[str]:
        """
        获取所有已注册的服务名称（带缓存）
        
        优先从 Redis 获取，Consul 作为降级方案
        """
        
        now = time.time()
        
        # 缓存未过期，直接返回
        if now - self._last_update < self._cache_ttl:
            return self._registered_services_cache
        
        service_names = set()
        
        # 1. 从 Redis 获取（主要来源）
        if self.redis:
            try:
                keys = await self.redis.keys("service:*:*")
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    
                    parts = key.split(":")
                    if len(parts) >= 2:
                        service_name = parts[1]
                        # 排除自身
                        if service_name != settings.SERVICE_NAME:
                            service_names.add(service_name)
                
                logger.debug(f"📋 Registered services from Redis: {service_names}")
            
            except Exception as e:
                logger.error(f"❌ Failed to get registered services from Redis: {e}")
        
        # 2. 从 Consul 获取（降级方案）
        if not service_names and self.consul:
            try:
                consul_services = self.consul.get_services()
                for svc_name in consul_services.keys():
                    if svc_name != "consul" and svc_name != settings.SERVICE_NAME:
                        service_names.add(svc_name)
                
                logger.debug(f"📋 Registered services from Consul (fallback): {service_names}")
            
            except Exception as e:
                logger.error(f"❌ Failed to get registered services from Consul: {e}")
        
        # 更新缓存
        if service_names:
            self._registered_services_cache = service_names
            self._last_update = now
        
        return service_names
    
    async def _verify_service_ip(self, service_name: str, client_host: str) -> bool:
        """
        验证服务的 IP 地址是否匹配注册信息
        
        Args:
            service_name: 服务名称
            client_host: 客户端 IP
        
        Returns:
            IP 是否匹配
        """
        
        if not self.redis:
            return True  # Redis 不可用时跳过 IP 验证
        
        try:
            # 获取该服务的所有注册实例
            pattern = f"service:{service_name}:*"
            keys = await self.redis.keys(pattern)
            
            for key in keys:
                instance_data = await self.redis.hgetall(key)
                if instance_data:
                    registered_ip = instance_data.get("ip")
                    if isinstance(registered_ip, bytes):
                        registered_ip = registered_ip.decode('utf-8')
                    
                    if registered_ip == client_host:
                        logger.debug(f"✅ IP verified: {client_host}")
                        return True
            
            logger.warning(f"❌ IP verification failed for {service_name}: {client_host}")
            return False
        
        except Exception as e:
            logger.error(f"❌ IP verification error: {e}")
            return True  # 出错时不阻止请求（降级策略）
