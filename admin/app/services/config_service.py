"""
配置管理服务（CORS 和 HMAC Key 存储在 Redis）
"""
from typing import Optional
from app.utils.redis_manager import redis_manager


class ConfigService:
    # Redis key 前缀
    KEY_CORS = "config:cors"
    KEY_HMAC = "config:hmac"
    
    # 默认 CORS 配置
    DEFAULT_CORS = {
        "allow_origins": ["*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"]
    }
    
    @classmethod
    async def get_cors_config(cls) -> dict:
        """获取 CORS 配置"""
        data = await redis_manager.get(cls.KEY_CORS)
        if data:
            import json
            return json.loads(data)
        return cls.DEFAULT_CORS.copy()
    
    @classmethod
    async def set_cors_config(cls, config: dict) -> bool:
        """设置 CORS 配置"""
        import json
        return await redis_manager.set(cls.KEY_CORS, json.dumps(config))
    
    @classmethod
    async def get_hmac_key(cls, app_id: str) -> Optional[str]:
        """获取 HMAC Key"""
        key = f"{cls.KEY_HMAC}:{app_id}"
        return await redis_manager.get(key)
    
    @classmethod
    async def set_hmac_key(cls, app_id: str, secret_key: str) -> bool:
        """设置 HMAC Key"""
        key = f"{cls.KEY_HMAC}:{app_id}"
        return await redis_manager.set(key, secret_key)
    
    @classmethod
    async def delete_hmac_key(cls, app_id: str) -> bool:
        """删除 HMAC Key"""
        key = f"{cls.KEY_HMAC}:{app_id}"
        return await redis_manager.delete(key) > 0
    
    @classmethod
    async def get_all_hmac_keys(cls) -> dict:
        """获取所有 HMAC Keys"""
        pattern = f"{cls.KEY_HMAC}:*"
        keys = await redis_manager.keys(pattern)
        result = {}
        for key in keys:
            app_id = key.replace(f"{cls.KEY_HMAC}:", "")
            value = await redis_manager.get(key)
            if value:
                result[app_id] = value
        return result


config_service = ConfigService()
