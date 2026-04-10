#redis管理器
# Redis连接池管理模块

import asyncio
import threading
from typing import Optional, Dict, Set, List, Any
import logging

import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster

from config import settings

# 配置日志
logger = logging.getLogger(__name__)


class RedisManager:
    """Redis连接池管理器（支持单机和集群模式，线程安全）"""

    _instance: Optional['RedisManager'] = None
    _lock: threading.Lock = threading.Lock()
    _init_lock: threading.Lock = threading.Lock()
    
    _pool: Optional[Any] = None
    _cluster: Optional[Any] = None
    _is_cluster_mode: bool = False

    def __new__(cls):
        """单例模式（线程安全）"""
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化Redis连接池"""
        with self._init_lock:
            if self._pool is None and self._cluster is None:
                self._init_pool()

    def _init_pool(self):
        """初始化Redis连接池"""
        try:
            self._is_cluster_mode = settings.REDIS_CLUSTER_MODE
            if self._is_cluster_mode:
                self._init_cluster()
            else:
                self._init_standalone()
        except Exception as e:
            logger.error(f"Redis连接池初始化失败: {str(e)}")
            raise

    def _init_standalone(self):
        """初始化单机模式连接池"""
        self._pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=settings.REDIS_DECODE_RESPONSES,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        )
        logger.info(f"Redis单机模式连接池初始化成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")

    def _init_cluster(self):
        """初始化集群模式连接"""
        cluster_nodes = settings.REDIS_CLUSTER_NODES
        if not cluster_nodes:
            cluster_nodes = [f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"]
            logger.warning("未配置集群节点，使用单机地址作为唯一节点")

        # 使用第一个节点作为连接入口
        primary_node = cluster_nodes[0]
        if ':' in primary_node:
            host, port = primary_node.split(':', 1)
            url = f"redis://:{settings.REDIS_PASSWORD}@{host}:{port}/0" if settings.REDIS_PASSWORD else f"redis://{host}:{port}/0"
        else:
            url = f"redis://:{settings.REDIS_PASSWORD}@{primary_node}:6379/0" if settings.REDIS_PASSWORD else f"redis://{primary_node}:6379/0"

        self._cluster = RedisCluster.from_url(
            url,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=settings.REDIS_DECODE_RESPONSES,
        )
        logger.info(f"Redis集群模式初始化成功: {cluster_nodes}")

    def _get_client(self) -> Any:
        """获取Redis客户端"""
        if self._is_cluster_mode:
            return self._cluster
        return redis.Redis(connection_pool=self._pool)

    async def _close_client(self, client: Any):
        """关闭客户端（集群模式下无需关闭）"""
        if not self._is_cluster_mode and client is not None:
            await client.aclose()

    async def get_connection(self):
        """获取Redis连接（兼容旧接口）"""
        return self._get_client()

    async def get_client(self):
        """获取Redis客户端（测试连接用）"""
        return self._get_client()
    async def keys(self, pattern: str) -> list:
        """获取匹配的键列表"""
        client = self._get_client()
        try:
            return await client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS操作失败: {str(e)}")
            return []
        finally:
            await self._close_client(client)

    async def close(self):
        """关闭Redis连接池"""
        if self._is_cluster_mode:
            if self._cluster:
                await self._cluster.aclose()
                logger.info("Redis集群连接已关闭")
        else:
            if self._pool:
                await self._pool.disconnect()
                logger.info("Redis单机连接池已关闭")

    async def __aenter__(self):
        """支持上下文管理器"""
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb):
        """上下文管理器退出时关闭连接池"""
        await self.close()

    async def get(self, key: str) -> Optional[str]:
        """
        获取键值

        Args:
            key: 键名

        Returns:
            Optional[str]: 键值，如果不存在则返回None
        """
        client = self._get_client()
        try:
            return await client.get(key)
        except Exception as e:
            logger.error(f"Redis GET操作失败: {str(e)}")
            return None
        finally:
            await self._close_client(client)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        设置键值

        Args:
            key: 键名
            value: 键值
            ex: 过期时间（秒）

        Returns:
            bool: 是否设置成功
        """
        client = self._get_client()
        try:
            await client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis SET操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def delete(self, key: str) -> bool:
        """
        删除键

        Args:
            key: 键名

        Returns:
            bool: 是否删除成功
        """
        client = self._get_client()
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            bool: 键是否存在
        """
        client = self._get_client()
        try:
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 键名
            seconds: 过期时间（秒）

        Returns:
            bool: 是否设置成功
        """
        client = self._get_client()
        try:
            await client.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Args:
            key: 键名

        Returns:
            int: 剩余时间（秒），-1表示永不过期，-2表示键不存在
        """
        client = self._get_client()
        try:
            return await client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL操作失败: {str(e)}")
            return -2
        finally:
            await self._close_client(client)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希表中的字段值

        Args:
            name: 哈希表名
            key: 字段名

        Returns:
            Optional[str]: 字段值
        """
        client = self._get_client()
        try:
            return await client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET操作失败: {str(e)}")
            return None
        finally:
            await self._close_client(client)

    async def hset(self, name: str, key: str, value: str) -> bool:
        """
        设置哈希表中的字段值

        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值

        Returns:
            bool: 是否设置成功
        """
        client = self._get_client()
        try:
            await client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"Redis HSET操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def hgetall(self, name: str) -> Dict[str, str]:
        """
        获取哈希表中的所有字段

        Args:
            name: 哈希表名

        Returns:
            Dict[str, str]: 哈希表中的所有字段
        """
        client = self._get_client()
        try:
            return await client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL操作失败: {str(e)}")
            return {}
        finally:
            await self._close_client(client)

    async def hdel(self, name: str, *keys) -> bool:
        """
        删除哈希表中的字段

        Args:
            name: 哈希表名
            keys: 字段名

        Returns:
            bool: 是否删除成功
        """
        client = self._get_client()
        try:
            await client.hdel(name, *keys)
            return True
        except Exception as e:
            logger.error(f"Redis HDEL操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def lpush(self, name: str, *values) -> int:
        """
        将一个或多个值插入到列表头部

        Args:
            name: 列表名
            values: 值

        Returns:
            int: 列表长度
        """
        client = self._get_client()
        try:
            return await client.lpush(name, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH操作失败: {str(e)}")
            return 0
        finally:
            await self._close_client(client)

    async def rpush(self, name: str, *values) -> int:
        """
        将一个或多个值插入到列表尾部

        Args:
            name: 列表名
            values: 值

        Returns:
            int: 列表长度
        """
        client = self._get_client()
        try:
            return await client.rpush(name, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH操作失败: {str(e)}")
            return 0
        finally:
            await self._close_client(client)

    async def lpop(self, name: str) -> Optional[str]:
        """
        移出并获取列表的第一个元素

        Args:
            name: 列表名

        Returns:
            Optional[str]: 元素值
        """
        client = self._get_client()
        try:
            return await client.lpop(name)
        except Exception as e:
            logger.error(f"Redis LPOP操作失败: {str(e)}")
            return None
        finally:
            await self._close_client(client)

    async def rpop(self, name: str) -> Optional[str]:
        """
        移出并获取列表的最后一个元素

        Args:
            name: 列表名

        Returns:
            Optional[str]: 元素值
        """
        client = self._get_client()
        try:
            return await client.rpop(name)
        except Exception as e:
            logger.error(f"Redis RPOP操作失败: {str(e)}")
            return None
        finally:
            await self._close_client(client)

    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """
        获取列表指定范围内的元素

        Args:
            name: 列表名
            start: 起始位置
            end: 结束位置

        Returns:
            List[str]: 元素列表
        """
        client = self._get_client()
        try:
            return await client.lrange(name, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE操作失败: {str(e)}")
            return []
        finally:
            await self._close_client(client)

    async def sadd(self, name: str, *values) -> int:
        """
        向集合添加一个或多个成员

        Args:
            name: 集合名
            values: 成员值

        Returns:
            int: 新添加的成员数量
        """
        client = self._get_client()
        try:
            return await client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Redis SADD操作失败: {str(e)}")
            return 0
        finally:
            await self._close_client(client)

    async def srem(self, name: str, *values) -> int:
        """
        移除集合中的一个或多个成员

        Args:
            name: 集合名
            values: 成员值

        Returns:
            int: 移除的成员数量
        """
        client = self._get_client()
        try:
            return await client.srem(name, *values)
        except Exception as e:
            logger.error(f"Redis SREM操作失败: {str(e)}")
            return 0
        finally:
            await self._close_client(client)

    async def smembers(self, name: str) -> Set[str]:
        """
        获取集合中的所有成员

        Args:
            name: 集合名

        Returns:
            Set[str]: 成员集合
        """
        client = self._get_client()
        try:
            return await client.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS操作失败: {str(e)}")
            return set()
        finally:
            await self._close_client(client)

    async def sismember(self, name: str, value: str) -> bool:
        """
        判断成员是否是集合的成员

        Args:
            name: 集合名
            value: 成员值

        Returns:
            bool: 是否是成员
        """
        client = self._get_client()
        try:
            return await client.sismember(name, value)
        except Exception as e:
            logger.error(f"Redis SISMEMBER操作失败: {str(e)}")
            return False
        finally:
            await self._close_client(client)

    async def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """
        向有序集合添加一个或多个成员

        Args:
            name: 有序集合名
            mapping: 成员和分数的映射

        Returns:
            int: 新添加的成员数量
        """
        client = self._get_client()
        try:
            return await client.zadd(name, mapping)
        except Exception as e:
            logger.error(f"Redis ZADD操作失败: {str(e)}")
            return 0
        finally:
            await self._close_client(client)

    async def zrem(self, name: str, *values) -> int:
        """
        移除有序集合中的一个或多个成员

        Args:
            name: 有序集合名
            values: 成员值

        Returns:
            int: 移除的成员数量
        """
        client = self._get_client()
        try:
            return await client.zrem(name, *values)
        except Exception as e:
            logger.error(f"Redis ZREM操作失败: {str(e)}")
            return 0
        finally:
            await self._close_client(client)

    async def zrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        """
        获取有序集合中指定范围内的成员

        Args:
            name: 有序集合名
            start: 起始位置
            end: 结束位置

        Returns:
            List[str]: 成员列表
        """
        client = self._get_client()
        try:
            return await client.zrange(name, start, end)
        except Exception as e:
            logger.error(f"Redis ZRANGE操作失败: {str(e)}")
            return []
        finally:
            await self._close_client(client)

    async def zscore(self, name: str, value: str) -> Optional[float]:
        """
        获取有序集合中成员的分数

        Args:
            name: 有序集合名
            value: 成员值

        Returns:
            Optional[float]: 成员分数
        """
        client = self._get_client()
        try:
            return await client.zscore(name, value)
        except Exception as e:
            logger.error(f"Redis ZSCORE操作失败: {str(e)}")
            return None
        finally:
            await self._close_client(client)


# 创建全局Redis管理器实例
redis_manager = None


def get_redis_manager() -> RedisManager:
    """
    获取Redis管理器实例

    Returns:
        RedisManager: Redis管理器实例
    """
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisManager()
    return redis_manager
