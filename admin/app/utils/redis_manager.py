"""
Redis 客户端管理器

提供全局唯一的 Redis 客户端实例，统一管理连接池和生命周期
支持单机模式和集群模式
"""
import asyncio
import threading
from typing import Optional, Any

from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster

from config import settings

# 全局客户端实例
_client: Optional[Redis] = None
_cluster: Optional[RedisCluster] = None
_lock: threading.Lock = threading.Lock()
_is_cluster_mode: bool = False


def _init_pool():
    """初始化连接池"""
    global _client, _cluster, _is_cluster_mode
    
    _is_cluster_mode = settings.REDIS_CLUSTER_MODE
    
    if _is_cluster_mode:
        _init_cluster()
    else:
        _init_standalone()


def _init_standalone():
    """初始化单机模式"""
    global _client
    from redis.asyncio import ConnectionPool
    
    pool = ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        max_connections=min(settings.REDIS_POOL_SIZE, 20),
        decode_responses=settings.REDIS_DECODE_RESPONSES,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    )
    _client = Redis(connection_pool=pool)


def _init_cluster():
    """初始化集群模式"""
    global _cluster
    
    cluster_nodes = settings.REDIS_CLUSTER_NODES
    if not cluster_nodes:
        cluster_nodes = [f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"]

    primary_node = cluster_nodes[0]
    if ':' in primary_node:
        host, port = primary_node.split(':', 1)
        url = f"redis://:{settings.REDIS_PASSWORD}@{host}:{port}/0" if settings.REDIS_PASSWORD else f"redis://{host}:{port}/0"
    else:
        port = settings.REDIS_PORT
        url = f"redis://:{settings.REDIS_PASSWORD}@{primary_node}:{port}/0" if settings.REDIS_PASSWORD else f"redis://{primary_node}:{port}/0"

    _cluster = RedisCluster.from_url(
        url,
        max_connections=settings.REDIS_POOL_SIZE,
        decode_responses=settings.REDIS_DECODE_RESPONSES,
    )
    _client = _cluster


def get_client() -> Redis:
    """获取全局 Redis 客户端实例（线程安全，延迟初始化）"""
    global _client
    
    if _client is None:
        with _lock:
            if _client is None:
                _init_pool()
    
    return _client


async def init():
    """初始化 Redis（兼容旧接口）"""
    get_client()


async def close():
    """关闭 Redis 客户端"""
    global _client, _cluster
    
    with _lock:
        if _client is not None:
            await _client.aclose()
            _client = None
            _cluster = None


async def ping() -> bool:
    """检查 Redis 连接是否正常"""
    try:
        client = get_client()
        result = client.ping()
        return result is True or result == b"PONG" or result == "PONG"
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis PING 操作失败: {e}")
        return False


# ==================== 便捷方法（直接代理到客户端） ====================

async def keys(pattern: str) -> list:
    """获取匹配的键列表"""
    try:
        client = get_client()
        return await client.keys(pattern)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis KEYS 操作失败: {e}")
        return []


async def get(key: str) -> Optional[str]:
    """获取键值"""
    try:
        client = get_client()
        return await client.get(key)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis GET 操作失败: {e}")
        return None


async def set(key: str, value: Any, ex: Optional[int] = None) -> bool:
    """设置键值"""
    try:
        import json
        client = get_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await client.set(key, value, ex=ex)
        return True
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis SET 操作失败: {e}")
        return False


async def delete(key: str) -> bool:
    """删除键"""
    try:
        client = get_client()
        await client.delete(key)
        return True
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis DELETE 操作失败: {e}")
        return False


async def exists(key: str) -> bool:
    """检查键是否存在"""
    try:
        client = get_client()
        return await client.exists(key) > 0
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis EXISTS 操作失败: {e}")
        return False


async def expire(key: str, seconds: int) -> bool:
    """设置键的过期时间"""
    try:
        client = get_client()
        await client.expire(key, seconds)
        return True
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis EXPIRE 操作失败: {e}")
        return False


async def ttl(key: str) -> int:
    """获取键的剩余过期时间"""
    try:
        client = get_client()
        return await client.ttl(key)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis TTL 操作失败: {e}")
        return -2


async def hget(name: str, key: str) -> Optional[str]:
    """获取哈希表中的字段值"""
    try:
        client = get_client()
        return await client.hget(name, key)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis HGET 操作失败: {e}")
        return None


async def hset(name: str, key: str, value: str) -> bool:
    """设置哈希表中的字段值"""
    try:
        client = get_client()
        await client.hset(name, key, value)
        return True
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis HSET 操作失败: {e}")
        return False


async def hgetall(name: str) -> dict:
    """获取哈希表中的所有字段"""
    try:
        client = get_client()
        return await client.hgetall(name)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis HGETALL 操作失败: {e}")
        return {}


async def hdel(name: str, *keys) -> bool:
    """删除哈希表中的字段"""
    try:
        client = get_client()
        await client.hdel(name, *keys)
        return True
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis HDEL 操作失败: {e}")
        return False


# ==================== 兼容旧接口的包装类 ====================

class RedisManager:
    """兼容旧接口的包装类，所有方法代理到模块级函数"""
    
    _instance: Optional['RedisManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def init(self):
        """初始化 Redis"""
        await init()
    
    async def close(self):
        """关闭 Redis"""
        await close()
    
    async def ping(self) -> bool:
        """检查连接"""
        return await ping()
    
    async def keys(self, pattern: str) -> list:
        return await keys(pattern)
    
    async def get(self, key: str) -> Optional[str]:
        return await get(key)
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        return await set(key, value, ex)
    
    async def delete(self, key: str) -> bool:
        return await delete(key)
    
    async def exists(self, key: str) -> bool:
        return await exists(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        return await expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        return await ttl(key)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        return await hget(name, key)
    
    async def hset(self, name: str, key: str, value: str) -> bool:
        return await hset(name, key, value)
    
    async def hgetall(self, name: str) -> dict:
        return await hgetall(name)
    
    async def hdel(self, name: str, *keys) -> bool:
        return await hdel(name, *keys)


def get_redis_manager() -> RedisManager:
    """获取 Redis 管理器实例"""
    return RedisManager()


# 全局实例（兼容旧代码）
redis_manager = RedisManager()
