"""
服务发现模块，负责维护服务注册信息和健康状态

- 服务注册：服务实例启动时向注册中心注册自己的信息
- 服务发现：其他服务或客户端通过注册中心查询可用的服务实例列表
- 健康检查/注销：由 Gateway health_checker 自动完成
- 容灾降级：Redis → 本地缓存
"""
import json
import os
from typing import Optional
from loguru import logger   
from config import settings
from config.settings import BASE_DIR
from app.utils.redis_manager import get_redis_manager
from app.models.service import ServiceBase


class ServiceDiscovery:

    def __init__(self):
        self.redis_manager = get_redis_manager()
        # 本地缓存路径
        self._cache_file = os.path.join(BASE_DIR, "data", "services_cache.json")
        # 内存缓存: {f"{service_name}:{service_id}": ServiceBase}
        self._local_cache: dict[str, ServiceBase] = {}
        # 加载本地缓存
        self._load_local_cache()

    def _load_local_cache(self):
        """加载本地缓存"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self._local_cache[key] = ServiceBase(**value)
                    logger.info(f"Loaded {len(self._local_cache)} services from local cache")
        except Exception as e:
            logger.warning(f"Failed to load local cache: {e}")

    def _save_local_cache(self):
        """保存本地缓存到文件"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            data = {k: v.model_dump() for k, v in self._local_cache.items()}
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save local cache: {e}")

    def _cache_key(self, service_name: str, service_id: str) -> str:
        """生成缓存键"""
        return f"{service_name}:{service_id}"

    async def register_service(self, service: ServiceBase) -> bool:
        """
        注册服务实例到注册中心（Redis + 本地缓存）
        
        Args:
            service: 服务实例对象
        
        Returns:
            是否成功注册
        """
        redis_ok = False
        
        # 0. 清理同一服务的其他实例（避免重复注册）
        try:
            # 清理 Redis 中的旧实例
            pattern = f"service:{service.name}:*"
            existing_keys = await self.redis_manager.keys(pattern)
            for key in existing_keys:
                # 跳过当前 ID
                if key.endswith(f":{service.id}"):
                    continue
                # 删除旧实例
                await self.redis_manager.delete(key)
                logger.info(f"Removed old instance from Redis: {key}")
                
                # 从本地缓存中删除
                cache_key = key.replace("service:", "").replace(":", ":", 1)
                if cache_key in self._local_cache:
                    del self._local_cache[cache_key]
                    logger.info(f"Removed from local cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old instances: {e}")
        
        # 1. 注册到 Redis
        try:
            redis_key = f"service:{service.name}:{service.id}"
            await self.redis_manager.set(redis_key, json.dumps(service.model_dump()), ex=settings.REDIS_TTL)
            logger.info(f"Service registered in Redis: {service.name} (ID: {service.id})")
            redis_ok = True
        except Exception as e:
            logger.error(f"Failed to register service in Redis: {e}")
        
        # 2. 同步到本地缓存（始终更新，作为兜底）
        self._local_cache[self._cache_key(service.name, service.id)] = service
        self._save_local_cache()
        
        return redis_ok

    async def unregister_service(self, service_name: str, service_id: str) -> bool:
        """
        注销服务实例（从 Redis 和本地缓存中删除）
        
        Args:
            service_name: 服务名称
            service_id: 服务实例 ID
        
        Returns:
            是否成功注销
        """
        redis_ok = False
        
        # 1. 从 Redis 删除
        try:
            redis_key = f"service:{service_name}:{service_id}"
            await self.redis_manager.delete(redis_key)
            logger.info(f"Service removed from Redis: {service_name} (ID: {service_id})")
            redis_ok = True
        except Exception as e:
            logger.error(f"Failed to remove service from Redis: {e}")
        
        # 3. 从本地缓存删除
        cache_key = self._cache_key(service_name, service_id)
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
            self._save_local_cache()
            logger.info(f"Service removed from local cache: {cache_key}")
        
        return redis_ok

    async def get_healthy_services(self, service_name: str) -> list[ServiceBase]:
        """
        获取健康的服务实例列表（降级策略：Redis → 本地缓存）
        
        Args:
            service_name: 服务名称
        
        Returns:
            健康的服务实例列表
        """
        pattern = f"service:{service_name}:*"
        
        # 1. 尝试从 Redis 获取
        try:
            keys = await self.redis_manager.keys(pattern)
            if keys:
                services = []
                for key in keys:
                    try:
                        value = await self.redis_manager.get(key)
                        if value:
                            data = json.loads(value)
                            if data.get('status') != 'unhealthy':
                                services.append(ServiceBase(**data))
                    except Exception as e:
                        logger.warning(f"Failed to parse service data: {e}")
                return services
        except Exception as e:
            logger.error(f"Failed to get services from Redis: {e}")
        
        # 2. Redis 失败，返回本地缓存
        logger.warning(f"Using local cache as fallback for service: {service_name}")
        return [
            svc for key, svc in self._local_cache.items()
            if key.startswith(f"{service_name}:") and svc.status != "unhealthy"
        ]

    async def get_service(self, service_name: str, service_id: Optional[str] = None) -> Optional[ServiceBase]:
        """
        获取指定服务实例（降级策略：Redis → 本地缓存）
        
        Args:
            service_name: 服务名称
            service_id: 服务实例 ID（可选）
        
        Returns:
            服务实例或 None
        """
        # 1. 优先从 Redis 获取
        if service_id:
            redis_key = f"service:{service_name}:{service_id}"
            try:
                value = await self.redis_manager.get(redis_key)
                if value:
                    return ServiceBase(**json.loads(value))
            except Exception as e:
                logger.error(f"Failed to get service from Redis: {e}")
        else:
            services = await self.get_healthy_services(service_name)
            return services[0] if services else None
        
        # 2. Redis 没有或失败，从本地缓存获取
        logger.warning(f"Using local cache as fallback for service: {service_name}:{service_id}")
        cache_key = self._cache_key(service_name, service_id) if service_id else None
        if cache_key:
            return self._local_cache.get(cache_key)
        else:
            services = [svc for key, svc in self._local_cache.items() if key.startswith(f"{service_name}:")]
            return services[0] if services else None



# 单例实例
_service_discovery: Optional[ServiceDiscovery] = None


def get_service_discovery() -> ServiceDiscovery:
    """获取服务发现单例"""
    global _service_discovery
    if _service_discovery is None:
        _service_discovery = ServiceDiscovery()
    return _service_discovery
