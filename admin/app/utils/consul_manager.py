"""
Consul 客户端管理器

提供服务发现、KV 存储等功能
支持集群模式，作为 Redis 的降级方案
"""
from typing import Optional, Dict, List, Any
import consul
from config import settings
from loguru import logger


class ConsulManager:
    """Consul 管理器"""
    
    _instance: Optional["ConsulManager"] = None
    _client: Optional[consul.Consul] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def init(self):
        """初始化 Consul 客户端"""
        if self._initialized:
            return
        
        if not settings.CONSUL_ENABLED:
            logger.warning("Consul is disabled in settings")
            return
        
        try:
            self._client = consul.Consul(
                host=settings.CONSUL_HOST,
                port=settings.CONSUL_PORT,
                token=settings.CONSUL_TOKEN if settings.CONSUL_TOKEN else None
            )
            
            # 测试连接
            self._client.agent.self()
            self._initialized = True
            logger.info(f"Consul connected: {settings.CONSUL_HOST}:{settings.CONSUL_PORT}")
        
        except Exception as e:
            logger.error(f"Failed to connect to Consul: {e}")
            self._client = None
            self._initialized = False
    
    def close(self):
        """关闭 Consul 客户端"""
        self._client = None
        self._initialized = False
        logger.info("Consul client closed")
    
    @property
    def client(self) -> Optional[consul.Consul]:
        """获取 Consul 客户端"""
        if not self._initialized or self._client is None:
            return None
        return self._client
    
    def get_services(self) -> Dict[str, Any]:
        """
        获取所有已注册的服务
        
        Returns:
            服务字典 {service_name: service_info}
        """
        if not self.client:
            logger.warning("Consul client not available")
            return {}
        
        try:
            _, services = self.client.catalog.services()
            return services
        except Exception as e:
            logger.error(f"Failed to get services from Consul: {e}")
            return {}
    
    def get_service_instances(self, service_name: str) -> List[Dict]:
        """
        获取指定服务的所有实例
        
        Args:
            service_name: 服务名称
        
        Returns:
            实例列表
        """
        if not self.client:
            logger.warning("Consul client not available")
            return []
        
        try:
            _, instances = self.client.catalog.service(service_name)
            return instances
        except Exception as e:
            logger.error(f"Failed to get service instances from Consul: {e}")
            return []
    
    def get_kv(self, key: str, default=None) -> Optional[str]:
        """
        获取 KV 存储的值
        
        Args:
            key: 键名
            default: 默认值
        
        Returns:
            值或默认值
        """
        if not self.client:
            logger.warning("Consul client not available")
            return default
        
        try:
            _, data = self.client.kv.get(key)
            if data and data.get('Value'):
                return data['Value'].decode('utf-8')
            return default
        except Exception as e:
            logger.error(f"Failed to get KV from Consul: {e}")
            return default
    
    def set_kv(self, key: str, value: str) -> bool:
        """
        设置 KV 存储的值
        
        Args:
            key: 键名
            value: 值
        
        Returns:
            是否成功
        """
        if not self.client:
            logger.warning("Consul client not available")
            return False
        
        try:
            return self.client.kv.put(key, value)
        except Exception as e:
            logger.error(f"Failed to set KV to Consul: {e}")
            return False
    
    def delete_kv(self, key: str) -> bool:
        """
        删除 KV 存储的值
        
        Args:
            key: 键名
        
        Returns:
            是否成功
        """
        if not self.client:
            logger.warning("Consul client not available")
            return False
        
        try:
            return self.client.kv.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete KV from Consul: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        检查 Consul 健康状态
        
        Returns:
            是否健康
        """
        if not self.client:
            return False
        
        try:
            self.client.agent.self()
            return True
        except Exception:
            return False


# 全局实例
consul_manager = ConsulManager()
