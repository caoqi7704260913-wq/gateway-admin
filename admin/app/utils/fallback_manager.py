"""
降级管理器

提供服务的降级策略，确保在依赖服务不可用时系统仍能运行
"""
from typing import Optional, Dict, Any
from loguru import logger


class FallbackManager:
    """
    降级管理器
    
    管理各种服务的降级策略：
    - Redis 降级：使用内存缓存
    - Gateway 降级：本地模式运行
    - Database 降级：只读模式
    """
    
    def __init__(self):
        # 降级状态
        self._fallback_states: Dict[str, bool] = {
            "redis": False,
            "gateway": False,
            "database": False,
        }
        
        # 内存缓存（Redis 降级时使用）
        self._memory_cache: Dict[str, Any] = {}
        
        # 默认配置（Gateway 降级时使用）
        self._default_configs = {
            "cors": {
                "origins": ["*"],
                "credentials": True,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "headers": ["Authorization", "Content-Type"]
            },
            "hmac_enabled": False  # Gateway 不可用时禁用 HMAC 验证
        }
    
    def set_fallback(self, service: str, enabled: bool):
        """设置服务降级状态"""
        if service in self._fallback_states:
            old_state = self._fallback_states[service]
            self._fallback_states[service] = enabled
            
            if enabled and not old_state:
                logger.warning(f"⚠️  Service '{service}' entered fallback mode")
            elif not enabled and old_state:
                logger.info(f"✅ Service '{service}' recovered from fallback mode")
    
    def is_fallback(self, service: str) -> bool:
        """检查服务是否处于降级状态"""
        return self._fallback_states.get(service, False)
    
    # ========== Redis 降级策略 ==========
    
    async def cache_get(self, key: str) -> Optional[str]:
        """
        获取缓存值（支持降级）
        
        优先从 Redis 获取，失败则从内存缓存获取
        """
        if not self.is_fallback("redis"):
            try:
                from app.utils.redis_manager import get_client
                client = get_client()
                return await client.get(key)
            except Exception as e:
                logger.warning(f"Redis get failed, using memory cache: {e}")
                self.set_fallback("redis", True)
        
        # 降级：从内存缓存获取
        return self._memory_cache.get(key)
    
    async def cache_set(self, key: str, value: str, ttl: int = 3600):
        """
        设置缓存值（支持降级）
        
        优先写入 Redis，失败则写入内存缓存
        """
        if not self.is_fallback("redis"):
            try:
                from app.utils.redis_manager import redis_manager
                if redis_manager.client:
                    await redis_manager.client.setex(key, ttl, value)
                    return
            except Exception as e:
                logger.warning(f"Redis set failed, using memory cache: {e}")
                self.set_fallback("redis", True)
        
        # 降级：写入内存缓存
        self._memory_cache[key] = value
    
    async def cache_delete(self, key: str):
        """删除缓存（支持降级）"""
        if not self.is_fallback("redis"):
            try:
                from app.utils.redis_manager import redis_manager
                if redis_manager.client:
                    await redis_manager.client.delete(key)
                    return
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
                self.set_fallback("redis", True)
        
        # 降级：从内存缓存删除
        self._memory_cache.pop(key, None)
    
    # ========== Gateway 降级策略 ==========
    
    def should_register_to_gateway(self) -> bool:
        """
        检查是否应该注册到 Gateway
        
        如果 Gateway 降级，则不注册
        """
        return not self.is_fallback("gateway")
    
    def get_default_cors_config(self) -> Dict[str, Any]:
        """获取默认 CORS 配置（Gateway 不可用时使用）"""
        return self._default_configs["cors"].copy()
    
    def is_hmac_enabled(self) -> bool:
        """检查是否启用 HMAC 验证"""
        return not self.is_fallback("gateway") and self._default_configs["hmac_enabled"]
    
    # ========== Database 降级策略 ==========
    
    def is_database_readonly(self) -> bool:
        """
        检查数据库是否为只读模式
        
        数据库降级时，只允许读取操作
        """
        return self.is_fallback("database")
    
    def check_write_permission(self, operation: str = "write") -> bool:
        """
        检查是否有写权限
        
        Args:
            operation: 操作类型（write, update, delete）
            
        Returns:
            是否允许写入
        """
        if self.is_database_readonly():
            logger.warning(f"Database is in readonly mode, operation '{operation}' rejected")
            return False
        return True
    
    # ========== 恢复策略 ==========
    
    async def try_recover_redis(self) -> bool:
        """尝试恢复 Redis 连接"""
        if not self.is_fallback("redis"):
            return True
        
        try:
            from app.utils.redis_manager import redis_manager
            if redis_manager.client:
                await redis_manager.client.ping()
                self.set_fallback("redis", False)
                logger.info("✅ Redis connection recovered")
                return True
        except Exception as e:
            logger.debug(f"Redis recovery failed: {e}")
        
        return False
    
    async def try_recover_gateway(self) -> bool:
        """尝试恢复 Gateway 连接"""
        if not self.is_fallback("gateway"):
            return True
        
        try:
            from app.utils.http_client import http_client
            from config import settings
            
            response = await http_client.get(
                f"{settings.GATEWAY_URL}/health",
                timeout=3.0
            )
            
            if response.status_code == 200:
                self.set_fallback("gateway", False)
                logger.info("✅ Gateway connection recovered")
                return True
        except Exception as e:
            logger.debug(f"Gateway recovery failed: {e}")
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取降级状态"""
        return {
            "fallback_states": self._fallback_states.copy(),
            "memory_cache_size": len(self._memory_cache),
            "database_readonly": self.is_database_readonly(),
            "hmac_enabled": self.is_hmac_enabled(),
        }


# 全局实例
fallback_manager = FallbackManager()
