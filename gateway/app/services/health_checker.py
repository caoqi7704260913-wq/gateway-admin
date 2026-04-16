"""
健康检查管理服务

负责定期检查服务实例的健康状态
实现Gateway主动探测的心跳机制
"""

import asyncio
import json
from typing import Optional
from loguru import logger
from config import settings
from app.utils.redis_manager import get_redis_manager
from app.utils.httpx_manager import get_http_client
from app.models.service import ServiceBase

class HealthChecker:

    def __init__(self, name: str, host: str, port: int, interval: int = 10):
        self.name = name
        self.host = host
        self.port = port
        self.interval = interval
        self.redis_manager = get_redis_manager()
        self.http_client = get_http_client()
        self._running = False  # 添加运行状态标志

    async def _get_healthy_services(self, service_name: str) -> list[ServiceBase]:
        """
        获取健康的服务实例列表
        
        Args:
            service_name: 服务名称
            
        Returns:
            健康的服务实例列表
        """
        # 获取所有匹配的服务实例
        pattern = f"service:{service_name}:*"
        try:
            keys = await self.redis_manager.keys(pattern)
            if not keys:
                return []
            # 从redis获取服务实例
            services = await self._get_services_by_keys(keys)
            return services
        except Exception as e:
            logger.error(f"Failed to get services from redis: {e}")
            return []
        


    async def _check_service_health(self, service_instance: ServiceBase) -> bool:
        """
            检查服务实例的健康状态
        
        Args:
            service_instance: 服务实例信息
            
             Returns:
            服务实例是否健康
        """
        # 从url中提取协议(http/https)，如果失败则默认http
        protocol = "http"
        if service_instance.url:
            if service_instance.url.startswith("https"):
                protocol = "https"
        
        # 使用 ip 而非 host（host 可能是 0.0.0.0）
        target_host = service_instance.ip if hasattr(service_instance, 'ip') and service_instance.ip else service_instance.host
        url = f"{protocol}://{target_host}:{service_instance.port}/healthz"
        try:
            logger.info(f"Checking health: {url}")
            response = await self.http_client.get(url, timeout=5)
            logger.info(f"Health check result: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to check health of service {service_instance.name}: {e}")
            logger.error(f"URL: {url}, Exception type: {type(e).__name__}")
            return False
        
    
    async def start_health_check(self):
        """
        启动健康检查循环
        """
        self._running = True  # 设置运行状态
        logger.info(f"Health checker started for service: {self.name}")
        
        # 首次检查前等待 3 秒，给服务启动时间
        #await asyncio.sleep(3)
        
        while self._running:  # 使用运行状态控制循环
            try:
                # 获取所有服务实例
                services = await self._get_healthy_services(self.name)
                for service in services:
                    is_healthy = await self._check_service_health(service)
                    if is_healthy:
                        logger.info(f"Service {service.name} is healthy")
                    else:
                        logger.warning(f"Service {service.name} is unhealthy")
                    await self._update_service_status(service, is_healthy)
            except asyncio.CancelledError:
                logger.info(f"Health checker for {self.name} cancelled")
                break
            except Exception as e:
                logger.error(f"Error during health check: {e}")
            
            # 使用 wait_for 支持快速退出
            try:
                await asyncio.wait_for(asyncio.sleep(self.interval), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
        
        logger.info(f"Health checker stopped for service: {self.name}")

    async def stop(self):
        """停止健康检查"""
        self._running = False
        logger.info(f"Stopping health checker for service: {self.name}")

    async def _update_service_status(self, service_instance: ServiceBase, is_healthy: bool):
        """
        更新服务实例的健康状态
        
        Args:
            service_instance: 服务实例信息
            is_healthy: 服务实例是否健康
        """
        redis_key = f"service:{service_instance.name}:{service_instance.id}"
        
        if is_healthy:
            # 健康：更新状态 + 刷新 TTL
            try:
                data = await self.redis_manager.get(redis_key)
                if data:
                    service_data = json.loads(data)
                    service_data['status'] = 'healthy'
                    await self.redis_manager.set(redis_key, json.dumps(service_data), ex=settings.REDIS_TTL)
            except Exception as e:
                logger.warning(f"Failed to update healthy service: {e}")
        else:
            # 不健康：注销服务实例
            try:
                await self.redis_manager.delete(redis_key)
                logger.warning(f"Service unregistered (unhealthy): {service_instance.name} (ID: {service_instance.id})")
                
                # 清理本地缓存（保持2级缓存一致性）
                from app.services.discovery import get_service_discovery
                discovery = get_service_discovery()
                cache_key = discovery._cache_key(service_instance.name, service_instance.id)
                if cache_key in discovery._local_cache:
                    del discovery._local_cache[cache_key]
                    discovery._save_local_cache()
                    logger.debug(f"Removed from local cache: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to deregister unhealthy service: {e}")
    

    async def _get_services_by_keys(self, keys: list[str]) -> list[ServiceBase]:
        """
        根据键列表获取服务实例

        Args:
            keys: Redis键列表

        Returns:
            服务实例列表
        """
        if not keys:
            return []

        services = []
        for key in keys:
            try:
                value = await self.redis_manager.get(key)
                if value is not None:
                    service_data = json.loads(value)
                    services.append(ServiceBase(**service_data))
            except Exception as e:
                logger.error(f"Failed to parse service data for key {key}: {e}")
        return services