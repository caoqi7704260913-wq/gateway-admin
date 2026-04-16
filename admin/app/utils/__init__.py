"""
工具函数包

包含通用工具类：
- database_pool: 数据库连接池管理
- fallback_manager: 降级管理器
- http_client: HTTP 客户端
- redis_manager: Redis 连接管理（支持集群）
- path_matcher: 路径匹配工具
"""

from app.utils.database_pool import db_manager, get_db, get_db_async
from app.utils.fallback_manager import fallback_manager
from app.utils.http_client import http_client
from app.utils.redis_manager import redis_manager
from app.utils.path_matcher import is_public_path, parse_public_paths

__all__ = [
    "db_manager",
    "fallback_manager",
    "get_db",
    "get_db_async",
    "http_client",
    "redis_manager",
    "is_public_path",
    "parse_public_paths",
]
