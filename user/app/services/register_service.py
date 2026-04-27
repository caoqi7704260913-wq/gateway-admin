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
from typing import Optional, Dict, Any
from loguru import logger
from app.utils.redis_pool import get_redis_pool
from app.utils.httpx_pool import get_httpx_pool
from app.utils.cache_manager import cache_manager, get_cache_manager
from config.settings import  settings

class RegisterService:

    def __init__(self):
        self.redis_pool = get_redis_pool()
        self.httpx_pool = get_httpx_pool()
        self.cache = get_cache_manager()
        self.gateway_url = settings.GATEWAY_URL # Gateway 的地址
        self.gateway_app_id = settings.GATEWAY_APP_ID # Gateway 的应用 ID
         # 根据 SSL 配置动态选择协议
        protocol = "https" if settings.SSL_ENABLED else "http"
        # 生成固定的服务 ID（基于主机名和端口，确保重启后 ID 不变）
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

    async def _get_hmac_key_signature(self) -> bool:
        redis_instance = self.redis_pool.get_instance()
        hmac_key = await redis_instance.get(f"config:hmac:{self.gateway_app_id}")
        if not hmac_key:
             hmac_key = self.cache.get(f"config:hmac:{self.gateway_app_id}")
        if not hmac_key:
             logger.warning("HMAC Key 不存在")  # Log warning if HMAC key is not found in Redis or cache
             return False  # Return False if HMAC key is not found in Redis or cache
        self._hmac_key = hmac_key
        return True
    

    async def _get_cors_config(self):
        redis_instance = self.redis_pool.get_instance()
        cors_config = await redis_instance.get("config:cors")
        if not cors_config:
             cors_config = self.cache.get("config:cors")
        if not cors_config:
             raise Exception("CORS 配置不存在")
        return cors_config

    def _generate_hmac_signature(self, body="", timestamp=None, nonce=None):
        """
        生成 HMAC 签名
        Args:
        body: 请求体
        timestamp: 时间戳
        nonce: 随机数
        
        Returns:
        签名
        """
        if timestamp is None:
            timestamp = str(int(time.time()))
        if nonce is None:
            nonce =  hashlib.md5(f"{timestamp}{self._app_id}".encode()).hexdigest()[:16]

        message = f"{timestamp}{nonce}{body}"
        signature = hmac.new(
            self._hmac_key.encode(), 
            message.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return {
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature
        }


    async def register(self)->bool:
        """注册服务到 Gateway"""
        try:
            if not self._registered:
                await self._register()
        except Exception as e:
            logger.error(f"注册服务到 Gateway 失败: {e}")
            self._registered = False
            return False
        return True

    async def _register(self) -> None:
        """注册服务到 Gateway"""
        logger.info("开始注册服务到 Gateway")
         # 步骤 4: 准备注册数据
        try:
            if not await self._get_hmac_key_signature():
                logger.error("HMAC Key 不存在，无法注册服务到 Gateway")
                return
            import json
            body = json.dumps(self.service_info, ensure_ascii=False)    # JSON 格式的请求体
            headers = self._generate_hmac_signature(body=body)
            headers["Content-Type"] = "application/json"
          
            response = await self.httpx_pool.post(
               f"{self.gateway_url}/api/services/register",  # 注册服务的接口   
                content=body,
                headers=headers,
                timeout=5.0
            )
            if response.status_code == 200:
                logger.info("注册服务到 Gateway 成功")
                self._registered = True
            else:
                logger.error(f"注册服务到 Gateway 失败: {response.status_code}")
                self._registered = False
        except Exception as e:
            logger.error(f"注册服务到 Gateway 失败: {e}")
            self._registered = False
            logger.warning("注册服务到 Gateway 失败，将使用本地模式运行")  # Log warning if registration fails, using local mode
           
    async def unregister(self)->bool:
        """从 Gateway 注销服务"""
        
        if not self._registered:
            return True
        import json
        body = json.dumps(self.service_info, ensure_ascii=False)    # JSON 格式的请求体
        headers = self._generate_hmac_signature(body=body)
        headers["Content-Type"] = "application/json"
        try:
            response = await self.httpx_pool.delete(
            f"{self.gateway_url}/api/services/unregister",  # 注销服务的接口
            headers=headers,
            content=body,
            timeout=5.0
            )
            self._registered = False

            logger.info("从 Gateway 注销服务成功")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"从 Gateway 注销服务失败: {e}")
            return False

    async def heartbeat(self):
        """向 Gateway 发送心跳包"""
        logger.warning("Heartbeat method is deprecated. Gateway uses active health checking.")
        # 不再执行心跳逻辑，Gateway 使用主动健康检查


register_service = RegisterService()
