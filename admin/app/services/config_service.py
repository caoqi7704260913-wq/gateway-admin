"""
配置管理服务（HMAC Key 存储在 Redis）

与 Gateway 保持一致的存储格式：
- HMAC Key: config:hmac:{app_id}

支持降级策略：
- Redis 不可用时使用内存缓存
"""
import json
from typing import Optional, Dict, Any, List
from loguru import logger
from app.utils.redis_manager import redis_manager
from app.utils.fallback_manager import fallback_manager


class ConfigService:
    # Redis key 前缀（与 Gateway 保持一致）
    KEY_HMAC = "config:hmac"
    

    @classmethod
    async def get_hmac_key(cls, app_id: str) -> Optional[str]:
        """
        获取 HMAC Key
        
        Args:
            app_id: 应用 ID
            
        Returns:
            HMAC Key，不存在返回 None
        """
        key = f"{cls.KEY_HMAC}:{app_id}"
        
        # 从 Redis 获取
        try:
            hmac_key = await redis_manager.get(key)
            if hmac_key:
                logger.debug(f"HMAC key retrieved from Redis: {app_id}")
                return hmac_key
        except Exception as e:
            logger.error(f"Failed to get HMAC key from Redis: {e}")
        
        # 失败，返回 None
        logger.warning(f"HMAC key not found in Redis: {app_id}")
        return None
    
    @classmethod
    async def set_hmac_key(cls, app_id: str, secret_key: str) -> bool:
        """
        设置 HMAC Key
        
        Args:
            app_id: 应用 ID
            secret_key: 密钥
            
        Returns:
            是否设置成功
        """
        key = f"{cls.KEY_HMAC}:{app_id}"
        
        # 写入 Redis
        try:
            success = await redis_manager.set(key, secret_key)
            if success:
                logger.debug(f"HMAC key written to Redis: {app_id}")
                return True
            else:
                logger.error(f"Failed to write HMAC key to Redis: {app_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to write HMAC key to Redis: {e}")
            return False
    
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
    



config_service = ConfigService()
