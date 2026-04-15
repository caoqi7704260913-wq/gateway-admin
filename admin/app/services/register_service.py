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
from config import settings
from app.utils.http_client import http_client
from app.utils.fallback_manager import fallback_manager
from app.services.config_service import config_service


class RegisterService:
    
    def __init__(self):
        self.gateway_url = settings.GATEWAY_URL
        
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
                "protocol": protocol  # 添加协议信息到元数据
            }
        }
        self._registered = False
        self._hmac_key = None
        self._app_id = settings.SERVICE_NAME
    
    def _generate_hmac_signature(self, body="", timestamp=None, nonce=None):
        """
        生成 HMAC 签名
        
        Args:
            body: 请求体
            timestamp: 时间戳
            nonce: 随机数
            
        Returns:
            签名字典
        """
        if timestamp is None:
            timestamp = str(int(time.time()))
        if nonce is None:
            nonce = hashlib.md5(f"{timestamp}{self._app_id}".encode()).hexdigest()[:16]
        
        message = f"{self._app_id}\n{timestamp}\n{nonce}\n{body}"
        signature = hmac.new(
            self._hmac_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        return {
            "X-App-ID": self._app_id,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": base64.b64encode(signature).decode()
        }
    
    async def _get_hmac_key_from_redis(self) -> bool:
        """
        从 Redis 获取 HMAC Key（支持 Consul 降级）
        
        Returns:
            是否成功获取
        """
        try:
            # 尝试从 Redis 获取 HMAC Key
            hmac_key = await config_service.get_hmac_key(self._app_id)
            
            if hmac_key:
                self._hmac_key = hmac_key
                logger.info(f"从 Redis 获取 HMAC Key 成功: {self._app_id}")
                return True
            else:
                logger.warning(f"Redis 中未找到 HMAC Key: {self._app_id}，将自动生成")
                return False
        except Exception as e:
            logger.error(f"从 Redis 获取 HMAC Key 失败: {e}")
            # Redis 失败时，尝试从 Consul 获取（如果配置了）
            if hasattr(settings, 'CONSUL_ENABLED') and settings.CONSUL_ENABLED:
                try:
                    from app.utils.consul_manager import get_consul_manager
                    consul = get_consul_manager()
                    key = consul.get_kv(f"config/hmac/{self._app_id}")
                    if key:
                        self._hmac_key = key
                        logger.info(f"从 Consul 降级获取 HMAC Key 成功: {self._app_id}")
                        return True
                except Exception as ce:
                    logger.error(f"从 Consul 获取 HMAC Key 也失败: {ce}")
            return False
    
    async def _create_hmac_key_if_needed(self):
        """如果 Redis 中没有 HMAC Key，则创建一个新的（双写 Redis + Consul）"""
        if not self._hmac_key:
            try:
                import secrets
                new_key = secrets.token_urlsafe(32)
                
                # 1. 写入 Redis
                await config_service.set_hmac_key(self._app_id, new_key)
                
                # 2. 降级写入 Consul
                if hasattr(settings, 'CONSUL_ENABLED') and settings.CONSUL_ENABLED:
                    try:
                        from app.utils.consul_manager import get_consul_manager
                        consul = get_consul_manager()
                        consul.set_kv(f"config/hmac/{self._app_id}", new_key)
                        logger.info(f"HMAC Key 已同步到 Consul")
                    except Exception as ce:
                        logger.warning(f"同步 HMAC Key 到 Consul 失败: {ce}")
                
                self._hmac_key = new_key
                logger.info(f"已创建新的 HMAC Key: {self._app_id}")
            except Exception as e:
                logger.error(f"创建 HMAC Key 失败: {e}")
    
    async def _get_cors_config_from_redis(self):
        """从 Redis 获取 CORS 配置并应用"""
        try:
            cors_config = await config_service.get_cors_config()
            if cors_config:
                logger.info(f"从 Redis 获取 CORS 配置成功")
                logger.debug(f"   Origins: {cors_config.get('allow_origins', [])}")
                logger.debug(f"   Methods: {cors_config.get('allow_methods', [])}")
            else:
                logger.warning("Redis 中未找到 CORS 配置，使用默认配置")
        except Exception as e:
            logger.error(f"从 Redis 获取 CORS 配置失败: {e}")
    
    async def register(self) -> bool:
        """
        注册到 Gateway（支持降级）
        
        完整流程：
        1. 从 Redis 获取 HMAC Key
        2. 如果没有则创建新的
        3. 从 Redis 获取 CORS 配置
        4. 生成 HMAC 签名
        5. 发送注册请求到 Gateway
        
        降级策略：
        - Gateway 不可用时，本地模式运行
        - Redis 不可用时，使用内存缓存
        """
        try:
            # 检查是否应该注册到 Gateway
            if not fallback_manager.should_register_to_gateway():
                logger.warning("Gateway in fallback mode, running in local mode")
                self._registered = False
                return False
            
            # 步骤 1: 从 Redis 获取 HMAC Key
            has_key = await self._get_hmac_key_from_redis()
            
            # 步骤 2: 如果没有则创建
            if not has_key:
                await self._create_hmac_key_if_needed()
            
            # 步骤 3: 从 Redis 获取 CORS 配置
            await self._get_cors_config_from_redis()
            
            # 步骤 4: 准备注册数据
            import json
            body = json.dumps(self.service_info, ensure_ascii=False)
            
            # 步骤 5: 生成 HMAC 签名
            headers = self._generate_hmac_signature(body=body)
            headers["Content-Type"] = "application/json"
            
            # 步骤 6: 发送注册请求
            response = await http_client.post(
                f"{self.gateway_url}/api/services/register",
                content=body,
                headers=headers,
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                self.service_info["id"] = result.get("service_id")
                self._registered = True
                logger.info(f"Admin service registered successfully")
                logger.info(f"   Service ID: {result.get('service_id')}")
                logger.info(f"   URL: {self.service_info['url']}")
                return True
            else:
                logger.error(f"Failed to register: {response.status_code} - {response.text}")
                # 注册失败，启用降级
                fallback_manager.set_fallback("gateway", True)
                return False
        except Exception as e:
            logger.error(f"Failed to register to Gateway: {e}")
            # 异常时启用降级
            fallback_manager.set_fallback("gateway", True)
            logger.warning("Running in local mode (Gateway unavailable)")
            return False
    
    async def unregister(self) -> bool:
        """从 Gateway 注销"""
        if not self._registered:
            return True
        try:
            # 生成签名
            import json
            body = json.dumps({"service_name": settings.SERVICE_NAME})
            headers = self._generate_hmac_signature(body=body)
            headers["Content-Type"] = "application/json"
            
            response = await http_client.delete(
                f"{self.gateway_url}/api/services/{settings.SERVICE_NAME}",
                content=body,
                headers=headers,
                timeout=5.0
            )
            self._registered = False
            logger.info(f"Admin service unregistered")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to unregister from Gateway: {e}")
            return False
    
    async def heartbeat(self):
        """
        心跳保活（已废弃）
        
        注意：Gateway 使用主动健康检查机制，定期探测 /healthz 端点
        不需要服务主动发送心跳。此方法保留仅为向后兼容。
        """
        logger.warning("Heartbeat method is deprecated. Gateway uses active health checking.")
        # 不再执行心跳逻辑


register_service = RegisterService()
