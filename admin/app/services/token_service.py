"""
Token 管理服务
"""
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, cast
from config import settings
from app.models.schemas import Token
from app.utils.database_pool import db_manager
from app.utils.redis_manager import redis_manager
from loguru import logger
class TokenService:
    
    @staticmethod
    async def create_token(admin, device: Optional[str] = None, ip: Optional[str] = None) -> str:
        """异步创建 Token"""
        #from app.utils.redis_manager import redis_manager
        #from loguru import logger
        
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
        try:
            # 写入 Redis
            await redis_manager.set(token_key, json.dumps(token_data), ex=settings.TOKEN_EXPIRATION_MINUTES * 60)
            
            # 写入 MySQL
            with db_manager.get_session() as session:
                token_record = Token(
                    token=token_str,
                    admin_id=admin.id,
                    device=device,
                    ip=ip,
                    expires_at=expires_at
                )
                session.add(token_record)
                session.commit()
                logger.info(f"Token saved to MySQL: {token_str[:16]}...")

        except Exception as e:
            logger.error(f"Failed to save token: {e}", exc_info=True)
        logger.info(f"Token created: {token_str[:16]}...")
        
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
    async def delete_token(token: str) -> bool:
        """删除 Token（双删 Redis + MySQL）"""
        #from app.utils.redis_manager import redis_manager
        #from loguru import logger
        
        token_key = f"token:{token}"
        
        # 1. 删除 Redis
        redis_deleted = await redis_manager.delete(token_key) > 0
        
        # 2. 删除 MySQL
        try:
            with db_manager.get_session() as session:
                from sqlalchemy import select
                stmt = select(Token).where(Token.token == token)
                result = session.scalars(stmt).first()
                if result:
                    session.delete(result)
                    session.commit()
                    logger.info(f"Token deleted from MySQL: {token[:16]}...")
                    return True
        except Exception as e:
            logger.error(f"Failed to delete token from MySQL: {e}", exc_info=True)
        
        return redis_deleted


token_service = TokenService()
