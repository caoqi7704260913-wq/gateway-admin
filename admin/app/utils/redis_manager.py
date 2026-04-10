"""
Redis 管理工具
"""
import json
import redis.asyncio as redis
from typing import Optional, Any
from config import settings


class RedisManager:
    """Redis 连接管理器"""
    
    _instance: Optional["RedisManager"] = None
    _client: Optional[redis.Redis] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(self):
        """初始化 Redis 连接"""
        if self._initialized:
            return
        
        self._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
            max_connections=20,
            socket_keepalive=True,
            socket_connect_timeout=5
        )
        self._initialized = True
    
    async def close(self):
        """关闭 Redis 连接"""
        if self._client and self._initialized:
            await self._client.close()
            self._client = None
            self._initialized = False
    
    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        return await self.client.get(key)
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """设置值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await self.client.set(key, value, ex=ex)
    
    async def delete(self, key: str) -> int:
        """删除键"""
        return await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return await self.client.exists(key) > 0
    
    async def keys(self, pattern: str) -> list:
        """获取匹配的所有键"""
        return await self.client.keys(pattern)


redis_manager = RedisManager()
