"""Redis连接池"""
import threading
from typing import Optional

from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster
from config.settings import settings


class RedisPool:
    _instance: Optional['Redis'] = None #单机    
    _instance_cluster: Optional['RedisCluster'] = None # 集群模式实例
    _lock = threading.Lock()
    _is_cluster_mode: bool = False
    _is_connected: bool = False
    _is_connected_cluster: bool = False

    def _init_pool(self):
        """初始化连接池"""
        self._is_cluster_mode = settings.REDIS_CLUSTER_MODE
        if self._is_cluster_mode:
            self._init_cluster()
        else:
            self._init_normal()

    def _init_normal(self):
        """单机模式初始化连接池"""
        from redis.asyncio import ConnectionPool

        pool = ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            max_connections=min(settings.REDIS_POOL_SIZE, 10),
            decode_responses=settings.REDIS_DECODE_RESPONSES,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        )
        self._instance = Redis(connection_pool=pool)

    def _init_cluster(self):
        """集群模式初始化连接池"""
        cluster_nodes = settings.REDIS_CLUSTER_NODES
        if not cluster_nodes:
            cluster_nodes_str = f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        else:
            cluster_nodes_str = cluster_nodes

        if isinstance(cluster_nodes_str, str): # 判断是否为字符串，是则进行处理
            nodes_list = [node.strip() for node in cluster_nodes_str.split(',') if node.strip()]
        else: # 否则直接使用
            nodes_list = cluster_nodes_str # 使用列表形式

        startup_nodes = []
        for node in nodes_list:
            if ':' in node:
                host, port = node.split(':', 1)
                startup_nodes.append({"host": host, "port": int(port)})
            else:
                startup_nodes.append({"host": node, "port": settings.REDIS_PORT})

        self._instance_cluster = RedisCluster(
            startup_nodes=startup_nodes,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=settings.REDIS_DECODE_RESPONSES,
        )
        self._instance = self._instance_cluster

    def get_instance(self) -> Redis:
        """获取Redis实例（单例）"""
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._init_pool()
                    self._is_connected = True
        return self._instance
    
    async def close(self):
        """关闭Redis连接"""
        if self._instance:
            await self._instance.aclose() # 关闭Redis连接
            self._instance = None
            self._is_connected = False
    
redis_pool = RedisPool() # 创建Redis连接池实例
"""Redis连接池实例"""
def get_redis_pool():
    """获取Redis连接池实例"""
    return redis_pool

