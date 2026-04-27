"""
本地缓存服务模块，提供缓存数据的获取和存储功能
支持 TTL 过期和异步持久化
"""
import json
import os
import time
from typing import Optional, Any
from app.utils.cache_manager import cache_manager
from app.utils.redis_pool import get_redis_pool
from app.utils.fallback_manager import fallback_manager
from loguru import logger
from config.settings import BASE_DIR


class CacheServices:
    """缓存服务 - 支持  + 本地缓存 + TTL + 持久化"""

    def __init__(self):
        self.cache_manager = cache_manager
        self.fallback_manager = fallback_manager
        
        # 本地缓存（带 TTL）
        self._local_cache: dict[str, dict[str, Any]] = {}
        
        # 持久化文件路径
        self._cache_file = os.path.join(BASE_DIR, "data", "local_cache.json")
        
    async def get(self, key: str) -> Optional[Any]:
        """从缓存中获取数据，支持本地缓存和  缓存"""
        


