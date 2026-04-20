"""
Redis 客户端管理器

提供全局唯一的 Redis 客户端实例，统一管理连接池和生命周期
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
        max_connections=min(settings.REDIS_POOL_SIZE, 10),
        decode_responses=settings.REDIS_DECODE_RESPONSES,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    )
    _client = Redis(connection_pool=pool)


def _init_cluster():
    """初始化集群模式"""
    global _cluster, _client
    
    cluster_nodes = settings.REDIS_CLUSTER_NODES
    if not cluster_nodes:
        cluster_nodes_str = f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    else:
        cluster_nodes_str = cluster_nodes

    if isinstance(cluster_nodes_str, str):
        nodes_list = [node.strip() for node in cluster_nodes_str.split(',') if node.strip()]
    else:
        nodes_list = cluster_nodes_str

    startup_nodes = []
    for node in nodes_list:
        if ':' in node:
            host, port = node.split(':', 1)
            startup_nodes.append({"host": host, "port": int(port)})
        else:
            startup_nodes.append({"host": node, "port": settings.REDIS_PORT})

    _cluster = RedisCluster(
        startup_nodes=startup_nodes,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
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
        # ping() 是同步方法，返回布尔值或字符串 "PONG"
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


async def set(key: str, value: str, ex: Optional[int] = None) -> bool:
    """设置键值"""
    try:
        client = get_client()
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


async def lpush(name: str, *values) -> int:
    """将值插入到列表头部"""
    try:
        client = get_client()
        return await client.lpush(name, *values)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis LPUSH 操作失败: {e}")
        return 0


async def rpush(name: str, *values) -> int:
    """将值插入到列表尾部"""
    try:
        client = get_client()
        return await client.rpush(name, *values)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis RPUSH 操作失败: {e}")
        return 0


async def lpop(name: str) -> Optional[str]:
    """移出并获取列表的第一个元素"""
    try:
        client = get_client()
        return await client.lpop(name)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis LPOP 操作失败: {e}")
        return None


async def rpop(name: str) -> Optional[str]:
    """移出并获取列表的最后一个元素"""
    try:
        client = get_client()
        return await client.rpop(name)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis RPOP 操作失败: {e}")
        return None


async def lrange(name: str, start: int, end: int) -> list:
    """获取列表指定范围内的元素"""
    try:
        client = get_client()
        return await client.lrange(name, start, end)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis LRANGE 操作失败: {e}")
        return []


async def sadd(name: str, *values) -> int:
    """向集合添加成员"""
    try:
        client = get_client()
        return await client.sadd(name, *values)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis SADD 操作失败: {e}")
        return 0


async def srem(name: str, *values) -> int:
    """移除集合中的成员"""
    try:
        client = get_client()
        return await client.srem(name, *values)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis SREM 操作失败: {e}")
        return 0


async def smembers(name: str) -> set:
    """获取集合中的所有成员"""
    try:
        client = get_client()
        return await client.smembers(name)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis SMEMBERS 操作失败: {e}")
        return set()


async def sismember(name: str, value: str) -> bool:
    """判断成员是否是集合的成员"""
    try:
        client = get_client()
        return await client.sismember(name, value)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis SISMEMBER 操作失败: {e}")
        return False


async def zadd(name: str, mapping: dict) -> int:
    """向有序集合添加成员"""
    try:
        client = get_client()
        return await client.zadd(name, mapping)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis ZADD 操作失败: {e}")
        return 0


async def zrem(name: str, *values) -> int:
    """移除有序集合中的成员"""
    try:
        client = get_client()
        return await client.zrem(name, *values)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis ZREM 操作失败: {e}")
        return 0


async def zrange(name: str, start: int = 0, end: int = -1) -> list:
    """获取有序集合中指定范围内的成员"""
    try:
        client = get_client()
        return await client.zrange(name, start, end)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis ZRANGE 操作失败: {e}")
        return []


async def zscore(name: str, value: str) -> Optional[float]:
    """获取有序集合中成员的分数"""
    try:
        client = get_client()
        return await client.zscore(name, value)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis ZSCORE 操作失败: {e}")
        return None


async def zremrangebyscore(name: str, min_score: float, max_score: float) -> int:
    """移除有序集合中指定分数范围的成员"""
    try:
        client = get_client()
        return await client.zremrangebyscore(name, min_score, max_score)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis ZREMRANGEBYSCORE 操作失败: {e}")
        return 0


async def zcard(name: str) -> int:
    """获取有序集合的成员数"""
    try:
        client = get_client()
        return await client.zcard(name)
    except Exception as e:
        from loguru import logger
        logger.error(f"Redis ZCARD 操作失败: {e}")
        return 0


# ==================== 兼容旧接口 ====================

class RedisManager:
    """兼容旧接口的包装类，所有方法代理到模块级函数"""
    
    _instance: Optional['RedisManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def keys(self, pattern: str) -> list:
        return await keys(pattern)
    
    async def get(self, key: str) -> Optional[str]:
        return await get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
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
    
    async def lpush(self, name: str, *values) -> int:
        return await lpush(name, *values)
    
    async def rpush(self, name: str, *values) -> int:
        return await rpush(name, *values)
    
    async def lpop(self, name: str) -> Optional[str]:
        return await lpop(name)
    
    async def rpop(self, name: str) -> Optional[str]:
        return await rpop(name)
    
    async def lrange(self, name: str, start: int, end: int) -> list:
        return await lrange(name, start, end)
    
    async def sadd(self, name: str, *values) -> int:
        return await sadd(name, *values)
    
    async def srem(self, name: str, *values) -> int:
        return await srem(name, *values)
    
    async def smembers(self, name: str) -> set: # type: ignore
        return await smembers(name)
    
    async def sismember(self, name: str, value: str) -> bool:
        return await sismember(name, value)
    
    async def zadd(self, name: str, mapping: dict) -> int:
        return await zadd(name, mapping)
    
    async def zrem(self, name: str, *values) -> int:
        return await zrem(name, *values)
    
    async def zrange(self, name: str, start: int = 0, end: int = -1) -> list:
        return await zrange(name, start, end)
    
    async def zscore(self, name: str, value: str) -> Optional[float]:
        return await zscore(name, value)
    
    async def zremrangebyscore(self, name: str, min_score: float, max_score: float) -> int:
        return await zremrangebyscore(name, min_score, max_score)
    
    async def zcard(self, name: str) -> int:
        return await zcard(name)
    
    async def close(self):
        await close()
    
    async def ping(self) -> bool:
        return await ping()


def get_redis_manager() -> RedisManager:
    """获取 Redis 管理器实例（兼容旧代码）"""
    return RedisManager()
