"""
服务发现模块，负责维护服务注册信息和健康状态

- 服务注册：服务实例启动时向注册中心注册自己的信息
- 服务发现：其他服务或客户端通过注册中心查询可用的服务实例列表
- 健康检查/注销：由 Gateway health_checker 自动完成
"""
import json
from typing import Optional
from loguru import logger   
from config import settings
from app.utils.redis_manager import get_redis_manager
from app.utils.consul_manager import get_consul_manager
from app.models.service import ServiceBase


class ServiceDiscovery:

    def __init__(self):
        self.redis_manager = get_redis_manager()
        self.consul_manager = get_consul_manager()

    async def register_service(self, service: ServiceBase) -> bool:
        """
        注册服务实例到注册中心（双写模式：Redis + Consul）
        
        Args:
            service: 服务实例对象
        
        Returns:
            是否成功注册
        """
        redis_ok = False
        consul_ok = False
        
        # 1. 注册到 Redis（始终写入，作为缓存/快速访问）
        try:
            redis_key = f"service:{service.name}:{service.id}"
            await self.redis_manager.set(redis_key, json.dumps(service.model_dump()), ex=settings.REDIS_TTL)
            logger.info(f"Service registered in Redis: {service.name} (ID: {service.id})")
            redis_ok = True
        except Exception as e:
            logger.error(f"Failed to register service in Redis: {e}")
        
        # 2. 注册到 Consul（如果启用）
        if settings.CONSUL_ENABLED:
            try:
                tags = service.metadata.get("tags", []) if service.metadata else []
                if service.url and service.url.startswith("https"):
                    tags = [t for t in tags if not t.startswith("protocol:")]
                    tags.append("protocol:https")
                
                check = {
                    "ttl": f"{settings.REDIS_TTL}s",
                    "status": "passing"
                }
                
                consul_ok = self.consul_manager.register_service(
                    name=service.name,
                    service_id=service.id,
                    address=service.ip or service.host,
                    port=service.port,
                    tags=tags,
                    check=check
                )
                if consul_ok:
                    logger.info(f"Service registered in Consul: {service.name} (ID: {service.id})")
            except Exception as e:
                logger.error(f"Failed to register service in Consul: {e}")
        
        # 返回结果：至少有一个成功
        return redis_ok or consul_ok

    async def get_healthy_services(self, service_name: str) -> list[ServiceBase]:
        """
        获取健康的服务实例列表
        
        Args:
            service_name: 服务名称
        
        Returns:
            健康的服务实例列表
        """
        pattern = f"service:{service_name}:*"
        
        try:
            keys = await self.redis_manager.keys(pattern)
            if not keys:
                if not settings.CONSUL_ENABLED:
                    return []
                return await self._get_services_from_consul(service_name)
            
            services = []
            for key in keys:
                try:
                    value = await self.redis_manager.get(key)
                    if value:
                        data = json.loads(value)
                        # 只返回健康的服务
                        if data.get('status') != 'unhealthy':
                            services.append(ServiceBase(**data))
                except Exception as e:
                    logger.warning(f"Failed to parse service data: {e}")
            
            return services
        except Exception as e:
            logger.error(f"Failed to get healthy services from Redis: {e}")
            if settings.CONSUL_ENABLED:
                return await self._get_services_from_consul(service_name)
            return []

    async def get_service(self, service_name: str, service_id: Optional[str] = None) -> Optional[ServiceBase]:
        """
        获取指定服务实例
        
        Args:
            service_name: 服务名称
            service_id: 服务实例 ID（可选）
        
        Returns:
            服务实例或 None
        """
        if service_id:
            redis_key = f"service:{service_name}:{service_id}"
            try:
                value = await self.redis_manager.get(redis_key)
                if value:
                    return ServiceBase(**json.loads(value))
            except Exception as e:
                logger.error(f"Failed to get service: {e}")
        else:
            services = await self.get_healthy_services(service_name)
            return services[0] if services else None
        return None

    async def _get_services_from_consul(self, service_name: str) -> list[ServiceBase]:
        """从 Consul 获取服务列表"""
        try:
            services = self.consul_manager.get_services()
            result = []
            for service_id, info in services.items():
                if service_name in service_id or info.get('Service') == service_name:
                    # 从 Tags 中提取协议
                    protocol = "http"
                    tags = info.get('Tags') or []
                    if isinstance(tags, list):
                        for tag in tags:
                            if isinstance(tag, str) and tag.startswith("protocol:"):
                                protocol = tag.split("protocol:", 1)[1]
                                break
                    
                    result.append(ServiceBase(
                        id=service_id,
                        name=info.get('Service', service_name),
                        host=info.get('Address', ''),
                        ip=info.get('Address', ''),
                        port=info.get('Port', 0),
                        url=f"{protocol}://{info.get('Address')}:{info.get('Port')}",
                        weight=1,
                        status="healthy"
                    ))
            return result
        except Exception as e:
            logger.error(f"Failed to get services from Consul: {e}")
            return []


# 单例实例
_service_discovery: Optional[ServiceDiscovery] = None


def get_service_discovery() -> ServiceDiscovery:
    """获取服务发现单例"""
    global _service_discovery
    if _service_discovery is None:
        _service_discovery = ServiceDiscovery()
    return _service_discovery
