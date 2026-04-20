"""
服务注册到 Gateway

完整的注册流程：
1. 从 Redis 获取 HMAC Key（用于签名）
2. 从 Redis 获取 CORS 配置
3. 生成 HMAC 签名
4. 注册到 Gateway

降级策略：
- Gateway 不可用时本地模式运行
- Redis 不可时使用内存缓存
"""
import asyncio
import time
import hashlib
import hmac
import base64
from loguru import logger
from sqlalchemy import BooleanClauseList
from app.utils.redis_pool import get_redis_pool
from app.utils.httpx_pool import httpx_pool
from app.utils.cache_manager import cache_manager
from config.settings import  settings

class RegisterService:

    def __init__(self):
        self.redis = get_redis_pool()
        self.httpx = httpx_pool
        self.cache = cache_manager
        self.gateway_url = settings.GATEWAY_URL # Gateway 的地址
        self.gateway_app_id = settings.GATEWAY_APP_ID # Gateway 的应用 ID
         # 根据 SSL 配置动态选择协议
        protocol = "https" if settings.SSL_ENABLED else "http"
        # 生成固定的服务 ID（基于主机名和端口，确保重启后 ID 不变）
        import hashlib
        service_id_str = f"{settings.SERVICE_NAME}-{settings.SERVICE_IP}-{settings.PORT}"
        fixed_service_id = hashlib.md5(service_id_str.encode()).hexdigest()[:12]  
        self.service_info = {
            "id": fixed_service_id,  # 使用固定 ID
            "name": settings.SERVICE_NAME,
            "host": settings.HOST,
            "ip": settings.SERVICE_IP,
            "port": settings.PORT,
            "url": f"{protocol}://{settings.SERVICE_IP}:{settings.PORT}",
            "weight": settings.SERVICE_WEIGHT,
            "metadata": {
                "tags": settings.SERVICE_TAGS.split(",") if settings.SERVICE_TAGS else [],
                "description": settings.SERVICE_DESCRIPTION,
                "protocol": protocol,  # 添加协议信息到元数据
                "global_whitelist": [path.strip() for path in settings.HMAC_WHITELIST.split(",") if path.strip()] if settings.HMAC_WHITELIST else []  # HMAC 白名单
            }
        }
        self._registered = False
        self._hmac_key = None  
        self._app_id = settings.SERVICE_NAME

    def _get_hmac_key_signature(self)->BooleanClauseList:
        # 先从 Redis 获取 HMAC Key如果没有则从本地缓存中获取
        hmac_key = self.redis.get(f"hmac:{self.gateway_app_id}")
        if not hmac_key:
             hmac_key = self.cache.get(f"hmac:{self.gateway_app_id}")
        if not hmac_key:
             logger.warning("HMAC Key 不存在")  # Log warning if HMAC key is not found in Redis or cache
             return False  # Return False if HMAC key is not found in Redis or cache
        self._hmac_key = hmac_key
        return True
    

    def _get_cors_config(self):
        # 从 Redis 获取 CORS 配置
        cors_config = self.redis.get(f"cors:{self.gateway_app_id}")
        if not cors_config:
             cors_config = self.cache.get(f"cors:{self.gateway_app_id}")
        if not cors_config:
             raise Exception("CORS 配置不存在")
        return cors_config

    def _generate_hmac_signature(self, body="", timestamp=None, nonce=None):
          pass
