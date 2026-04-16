"""
请求路由转发模块

核心功能：
- 路由匹配（根据路径转发到对应服务）
- 负载均衡选择后端
- 请求转发
- 熔断保护
- HMAC 签名验证（内部服务通信安全）
"""

from typing import Optional,Any
import time
import hmac
import hashlib
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger
from config import settings
from app.services.discovery import get_service_discovery
from app.services.load_balancer import get_load_balancer
from app.services.circuit_breaker import get_circuit_breaker, CircuitOpenError
from app.utils.httpx_manager import get_http_client
from app.utils.redis_manager import get_redis_manager


class Router:
    """请求路由器"""

    def __init__(self):
        self.discovery = get_service_discovery()
        self.load_balancer = get_load_balancer()
        self.http_client = get_http_client()
        self.redis = get_redis_manager()
        self.circuit_breakers: dict[str, Any] = {}  # 按服务名的熔断器

    def _get_circuit_breaker(self, service_name: str):
        """获取服务的熔断器"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = get_circuit_breaker(
                name=f"service:{service_name}",
                failure_threshold=5,
                success_threshold=2,
                timeout=30
            )
        return self.circuit_breakers[service_name]
    
    async def _generate_hmac_signature(self, method: str, path: str, target_service: str) -> tuple[str, str]:
        """
        生成 HMAC 签名
        
        Args:
            method: HTTP 方法
            path: 请求路径
            target_service: 目标服务名称
        
        Returns:
            (signature, timestamp) 元组
        """
        # 从 Redis 获取 HMAC Key
        hmac_key = await self._get_hmac_key(target_service)
        if not hmac_key:
            logger.error(f"HMAC key not found for service: {target_service}")
            # 如果没有密钥，使用默认密钥（仅开发环境）
            hmac_key = "default-dev-key-change-in-production"
        
        with open('d:/python_project/gateway/router_debug.log', 'a', encoding='utf-8') as f:
            f.write(f"   HMAC Key (first 8): {hmac_key[:8]}...\n")
        
        # 生成时间戳（使用整数，与 Admin 期望的格式一致）
        timestamp = str(int(time.time()))
        
        # 构建签名字符串
        message = f"{method}:{path}:{timestamp}"
        
        # 计算签名
        signature = hmac.new(
            hmac_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    async def _get_hmac_key(self, service_name: str) -> Optional[str]:
        """
        从 Redis 获取服务的 HMAC Key
        
        Args:
            service_name: 服务名称
        
        Returns:
            HMAC Key 或 None
        """
        redis_key = f"config:hmac:{service_name}"
        
        # 1. 尝试从 Redis 获取
        if self.redis:
            try:
                key = await self.redis.get(redis_key)
                if key:
                    logger.debug(f"HMAC key retrieved from Redis: {service_name}")
                    return key
            except Exception as e:
                logger.warning(f"Failed to get HMAC key from Redis: {e}")
        
        # 2. 都失败，返回 None
        logger.warning(f"HMAC key not found in Redis: {service_name}")
        return None
    
    async def route(self, request: Request) -> Response:
        """
        路由转发请求
        
        Args:
            request: 原始请求
        
        Returns:
            后端服务响应
        """
        path = request.url.path
        
        # 1. 解析路由：path -> service_name
        service_name = self._match_route(path)
        if not service_name:
            return JSONResponse(
                status_code=404,
                content={"error": "Route not found", "path": path}
            )
        
        # 2. 获取健康的后端服务
        backends = await self.discovery.get_healthy_services(service_name)
        if not backends:
            logger.warning(f"No healthy backend for service: {service_name}")
            return JSONResponse(
                status_code=503,
                content={"error": "Service unavailable", "service": service_name}
            )

        # 3. 负载均衡选择后端
        backend = await self.load_balancer.select(backends)
        if not backend:
            return JSONResponse(
                status_code=503,
                content={"error": "No backend available"}
            )

        # 4. 转发请求（带熔断保护）
        return await self._forward(request, backend, service_name)
    
    def _match_route(self, path: str) -> Optional[str]:
        """
        路径匹配：提取服务名称
        
        规则：/service-name/path -> service-name
        例如：/admin-service/api/auth/login -> admin-service
              /user-service/api/v1 -> user-service
        
        Args:
            path: 请求路径
        
        Returns:
            服务名称，未匹配返回 None
        """
        # 去掉开头的 /
        path = path.lstrip("/")
        
        # 第一段作为服务名
        parts = path.split("/")
        if not parts or not parts[0]:
            return None
        
        return parts[0]
    
    async def _forward(self, request: Request, backend, service_name: str) -> Response:
        """
        转发请求到后端（带熔断保护）

        Args:
            request: 原始请求
            backend: 选中的后端服务
            service_name: 服务名称

        Returns:
            后端响应
        """
        cb = self._get_circuit_breaker(service_name)

        try:
            return await cb.execute(self._do_forward, request, backend, service_name)
        except CircuitOpenError:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service temporarily unavailable",
                    "service": service_name,
                    "circuit_state": "open"
                }
            )
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return JSONResponse(
                status_code=502,
                content={"error": "Bad gateway", "detail": str(e)}
            )

    async def _do_forward(self, request: Request, backend, service_name: str) -> Response:
        """
        执行请求转发

        Args:
            request: 原始请求
            backend: 选中的后端服务

        Returns:
            后端响应
        """
        # 构建目标 URL（不做路径转换，保持原路径）
        base_url = backend.url.rstrip("/")
        path = request.url.path.lstrip("/")
        
        # 去掉第一段路径（服务名）
        remaining_path = "/".join(path.split("/")[1:]) if "/" in path else ""
        
        # 避免双斜杠
        if remaining_path:
            target_url = f"{base_url}/{remaining_path}"
        else:
            target_url = base_url

        # 构建请求头
        headers = dict(request.headers)
        
        # ⚠️ 重要：删除前端传来的签名相关 headers，避免与后端服务的签名冲突
        headers.pop('x-signature', None)
        headers.pop('X-Signature', None)
        headers.pop('x-timestamp', None)
        headers.pop('X-Timestamp', None)
        headers.pop('x-nonce', None)
        headers.pop('X-Nonce', None)
        
        headers["X-Forwarded-For"] = request.client.host if request.client else ""
        headers["X-Forwarded-Host"] = request.headers.get("host", "")
        headers["X-Forwarded-Proto"] = request.url.scheme
        headers.pop("host", None)
        headers.pop("content-length", None)
        
        # 添加内部服务通信标识和 HMAC 签名
        headers["X-Forwarded-By"] = "gateway"
        
        # 计算转发后的路径（用于生成签名）
        forwarded_path = target_url.replace(base_url, "")
        if not forwarded_path.startswith("/"):
            forwarded_path = "/" + forwarded_path
        
        signature, timestamp = await self._generate_hmac_signature(
            method=request.method,
            path=forwarded_path,  # 使用转发后的路径
            target_service=service_name
        )
        
        headers["X-Signature"] = signature
        headers["X-Timestamp"] = timestamp

        try:
            body = await request.body()

            response = await self.http_client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                timeout=settings.REQUEST_TIMEOUT
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        except TimeoutError:
            logger.error(f"Request timeout: {target_url}")
            raise  # 让熔断器记录失败

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise  # 让熔断器记录失败


# 单例实例
_router: Optional[Router] = None


def get_router() -> Router:
    """获取路由器单例"""
    global _router
    if _router is None:
        _router = Router()
    return _router
