"""
本地缓存管理器
基于 cachetools 实现多级缓存策略
"""
from typing import Optional, Any
from cachetools import TTLCache, LRUCache


class CacheManager:
    """本地缓存管理器"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存数量
            ttl: 默认过期时间（秒）
        """
        # TTL 缓存：适合有时效性的数据（如 Token 黑名单）
        self._ttl_cache = TTLCache(maxsize=max_size, ttl=ttl)
        
        # LRU 缓存：适合频繁访问的热点数据
        self._lru_cache = LRUCache(maxsize=max_size)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, use_lru: bool = False) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），仅对 TTL 缓存有效
            use_lru: 是否使用 LRU 缓存
        """
        if use_lru:
            self._lru_cache[key] = value
        else:
            if ttl:
                # 创建临时 TTL 缓存
                temp_cache = TTLCache(maxsize=1, ttl=ttl)
                temp_cache[key] = value
                self._ttl_cache[key] = value
            else:
                self._ttl_cache[key] = value
    
    def get(self, key: str, use_lru: bool = False) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            use_lru: 是否从 LRU 缓存获取
            
        Returns:
            缓存值，不存在返回 None
        """
        if use_lru:
            return self._lru_cache.get(key)
        return self._ttl_cache.get(key)
    
    def delete(self, key: str, use_lru: bool = False) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            use_lru: 是否从 LRU 缓存删除
            
        Returns:
            是否删除成功
        """
        if use_lru:
            if key in self._lru_cache:
                del self._lru_cache[key]
                return True
        else:
            if key in self._ttl_cache:
                del self._ttl_cache[key]
                return True
        return False
    
    def clear(self, use_lru: bool = False) -> None:
        """
        清空缓存
        
        Args:
            use_lru: 是否清空 LRU 缓存
        """
        if use_lru:
            self._lru_cache.clear()
        else:
            self._ttl_cache.clear()
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        self._ttl_cache.clear()
        self._lru_cache.clear()
    
    def has(self, key: str, use_lru: bool = False) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
            use_lru: 是否检查 LRU 缓存
            
        Returns:
            是否存在
        """
        if use_lru:
            return key in self._lru_cache
        return key in self._ttl_cache
    
    @property
    def ttl_size(self) -> int:
        """TTL 缓存当前大小"""
        return len(self._ttl_cache)
    
    @property
    def lru_size(self) -> int:
        """LRU 缓存当前大小"""
        return len(self._lru_cache)


# 全局缓存实例
cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    return cache_manager
