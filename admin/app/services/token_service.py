"""
Token 管理服务
"""
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, cast
from config import settings


class TokenService:
    
    @staticmethod
    def create_token_sync(admin, device: Optional[str] = None, ip: Optional[str] = None) -> str:
        """同步创建 Token"""
        from app.utils.redis_manager import redis_manager
        
        token_str = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(minutes=settings.TOKEN_EXPIRATION_MINUTES)
        
        # 存储到 Redis
        token_key = f"token:{token_str}"
        token_data = {
            "admin_id": admin.id,
            "username": admin.username,
            "device": device,
            "ip": ip,
            "expires_at": expires_at.isoformat()
        }
        
        # 同步执行
        import redis
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        client.setex(token_key, settings.TOKEN_EXPIRATION_MINUTES * 60, json.dumps(token_data))
        
        return token_str
    
    @staticmethod
    async def create_token(admin, device: Optional[str] = None, ip: Optional[str] = None) -> str:
        """异步创建 Token"""
        from app.utils.redis_manager import redis_manager
        
        token_str = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(minutes=settings.TOKEN_EXPIRATION_MINUTES)
        
        token_key = f"token:{token_str}"
        token_data = {
            "admin_id": admin.id,
            "username": admin.username,
            "device": device,
            "ip": ip,
            "expires_at": expires_at.isoformat()
        }
        await redis_manager.set(token_key, token_data, ex=settings.TOKEN_EXPIRATION_MINUTES * 60)
        
        return token_str
    
    @staticmethod
    async def verify_token(token: str) -> Optional[dict]:
        """验证 Token"""
        from app.utils.redis_manager import redis_manager
        token_key = f"token:{token}"
        data = await redis_manager.get(token_key)
        if data:
            return cast(dict, json.loads(data))
        return None
    
    @staticmethod
    def verify_token_sync(token: str) -> Optional[dict]:
        """同步验证 Token"""
        import redis
        token_key = f"token:{token}"
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        data = cast(Optional[str], client.get(token_key))
        if data:
            return json.loads(data)
        return None
    
    @staticmethod
    async def delete_token(token: str) -> bool:
        """删除 Token"""
        from app.utils.redis_manager import redis_manager
        token_key = f"token:{token}"
        return await redis_manager.delete(token_key) > 0
    
    @staticmethod
    def delete_token_sync(token: str) -> bool:
        """同步删除 Token"""
        import redis
        token_key = f"token:{token}"
        client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True
        )
        return bool(client.delete(token_key))


token_service = TokenService()
