"""
配置管理服务（CORS 和 HMAC Key 存储在 Redis + Consul）

与 Gateway 保持一致的存储格式：
- HMAC Key: config:hmac:{app_id}
- CORS Config: config:cors

支持降级策略：
- Redis 不可用时使用 Consul
- Consul 不可用时使用内存缓存
- Gateway 不可时使用默认配置
"""
import json
from typing import Optional, Dict, Any, List
from loguru import logger
from app.utils.redis_manager import redis_manager
from app.utils.consul_manager import consul_manager
from app.utils.fallback_manager import fallback_manager


class ConfigService:
    # Redis key 前缀（与 Gateway 保持一致）
    KEY_CORS = "config:cors"
    KEY_HMAC = "config:hmac"
    
    # 默认 CORS 配置（与 Gateway 保持一致）
    DEFAULT_CORS = {
        "origins": ["http://localhost:9527", "http://127.0.0.1:9527"],
        "credentials": True,
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "headers": ["Authorization", "Content-Type", "X-Requested-With"]
    }
    
    @classmethod
    async def get_cors_config(cls) -> Optional[Dict[str, Any]]:
        """
        获取 CORS 配置（支持降级）
        
        Returns:
            CORS 配置字典，不存在返回默认配置
        """
        try:
            # 尝试从 Redis 获取
            data = await fallback_manager.cache_get(cls.KEY_CORS)
            if data:
                return json.loads(data)
            
            # 降级：使用默认配置
            logger.warning("Using default CORS config (fallback mode)")
            return fallback_manager.get_default_cors_config()
        except Exception as e:
            logger.error(f"Error getting CORS config: {e}")
            return fallback_manager.get_default_cors_config()
    
    @classmethod
    async def set_cors_config(cls, config: Dict[str, Any]) -> bool:
        """
        设置 CORS 配置
        
        Args:
            config: CORS 配置字典
            
        Returns:
            是否设置成功
        """
        try:
            return await redis_manager.set(cls.KEY_CORS, json.dumps(config))
        except Exception as e:
            print(f"Error setting CORS config: {e}")
            return False
    
    @classmethod
    async def init_default_cors(cls) -> bool:
        """
        初始化默认 CORS 配置（如果不存在）
        
        Returns:
            是否成功
        """
        try:
            existing = await cls.get_cors_config()
            if not existing:
                await cls.set_cors_config(cls.DEFAULT_CORS)
                print("Initialized default CORS config")
                return True
            return True
        except Exception as e:
            print(f"Error initializing CORS config: {e}")
            return False
    
    @classmethod
    async def get_hmac_key(cls, app_id: str) -> Optional[str]:
        """
        获取 HMAC Key（支持 Redis → Consul 降级）
        
        Args:
            app_id: 应用 ID
            
        Returns:
            HMAC Key，不存在返回 None
        """
        key = f"{cls.KEY_HMAC}:{app_id}"
        
        # 1. 尝试从 Redis 获取
        try:
            hmac_key = await redis_manager.get(key)
            if hmac_key:
                logger.debug(f"HMAC key retrieved from Redis: {app_id}")
                return hmac_key
        except Exception as e:
            logger.warning(f"Failed to get HMAC key from Redis: {e}")
        
        # 2. 降级：从 Consul 获取
        try:
            if consul_manager.client:  # 检查 client 是否存在
                consul_path = f"config/hmac/{app_id}"
                hmac_key = consul_manager.get_kv(consul_path)
                if hmac_key:
                    logger.info(f"HMAC key retrieved from Consul (fallback): {app_id}")
                    
                    # 可选：将 Consul 的数据回写到 Redis
                    try:
                        await redis_manager.set(key, hmac_key)
                        logger.debug(f"Synced HMAC key from Consul to Redis: {app_id}")
                    except Exception as sync_error:
                        logger.warning(f"Failed to sync HMAC key to Redis: {sync_error}")
                    
                    return hmac_key
        except Exception as e:
            logger.warning(f"Failed to get HMAC key from Consul: {e}")
        
        # 3. 都失败，返回 None
        logger.warning(f"HMAC key not found in Redis or Consul: {app_id}")
        return None
    
    @classmethod
    async def set_hmac_key(cls, app_id: str, secret_key: str) -> bool:
        """
        设置 HMAC Key（同时写入 Redis 和 Consul）
        
        Args:
            app_id: 应用 ID
            secret_key: 密钥
            
        Returns:
            是否设置成功
        """
        key = f"{cls.KEY_HMAC}:{app_id}"
        redis_success = False
        consul_success = False
        
        # 1. 写入 Redis
        try:
            redis_success = await redis_manager.set(key, secret_key)
            if redis_success:
                logger.debug(f"HMAC key written to Redis: {app_id}")
        except Exception as e:
            logger.error(f"Failed to write HMAC key to Redis: {e}")
        
        # 2. 写入 Consul（降级备份）
        try:
            if consul_manager.client:  # 检查 client 是否存在
                consul_path = f"config/hmac/{app_id}"
                consul_success = consul_manager.set_kv(consul_path, secret_key)
                if consul_success:
                    logger.debug(f"HMAC key written to Consul: {app_id}")
        except Exception as e:
            logger.error(f"Failed to write HMAC key to Consul: {e}")
        
        # 至少一个成功即视为成功
        success = redis_success or consul_success
        if not success:
            logger.error(f"Failed to write HMAC key to both Redis and Consul: {app_id}")
        
        return success
    
    @classmethod
    async def delete_hmac_key(cls, app_id: str) -> bool:
        """
        删除 HMAC Key
        
        Args:
            app_id: 应用 ID
            
        Returns:
            是否删除成功
        """
        try:
            key = f"{cls.KEY_HMAC}:{app_id}"
            result = await redis_manager.delete(key)
            return result > 0
        except Exception as e:
            print(f"Error deleting HMAC key: {e}")
            return False
    
    @classmethod
    async def get_all_hmac_keys(cls) -> Dict[str, str]:
        """
        获取所有 HMAC Keys
        
        Returns:
            {app_id: secret_key} 字典
        """
        try:
            pattern = f"{cls.KEY_HMAC}:*"
            keys = await redis_manager.keys(pattern)
            result = {}
            for key in keys:
                app_id = key.replace(f"{cls.KEY_HMAC}:", "")
                value = await redis_manager.get(key)
                if value:
                    result[app_id] = value
            return result
        except Exception as e:
            print(f"Error getting all HMAC keys: {e}")
            return {}
    
    @classmethod
    async def add_cors_origin(cls, origin: str) -> bool:
        """
        添加 CORS Origin
        
        Args:
            origin: 源地址
            
        Returns:
            是否添加成功
        """
        try:
            config = await cls.get_cors_config() or cls.DEFAULT_CORS.copy()
            origins = config.get("origins", [])
            if origin not in origins:
                origins.append(origin)
                config["origins"] = origins
                return await cls.set_cors_config(config)
            return True
        except Exception as e:
            print(f"Error adding CORS origin: {e}")
            return False
    
    @classmethod
    async def remove_cors_origin(cls, origin: str) -> bool:
        """
        移除 CORS Origin
        
        Args:
            origin: 源地址
            
        Returns:
            是否移除成功
        """
        try:
            config = await cls.get_cors_config() or cls.DEFAULT_CORS.copy()
            origins = config.get("origins", [])
            if origin in origins:
                origins.remove(origin)
                config["origins"] = origins
                return await cls.set_cors_config(config)
            return True
        except Exception as e:
            print(f"Error removing CORS origin: {e}")
            return False


config_service = ConfigService()
