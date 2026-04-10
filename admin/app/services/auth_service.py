"""
认证服务
"""
from datetime import datetime
from typing import Optional, Tuple
from sqlmodel import select
from app.models.schemas import Admin
from app.services.password_service import password_service
from app.services.token_service import token_service
from app.database_pool import db_manager


class AuthService:
    
    @staticmethod
    def login(username: str, password: str, device: Optional[str] = None, ip: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
        """
        登录
        Returns: (是否成功, 错误信息/Token, 用户信息)
        """
        with db_manager.get_session() as session:
            admin = session.exec(select(Admin).where(Admin.username == username)).first()
            
            if not admin:
                return False, "用户名或密码错误", None
            
            if admin.status != 1:
                return False, "账号已被禁用", None
            
            if not password_service.verify(password, admin.password_hash):
                return False, "用户名或密码错误", None
            
            # 更新登录信息
            admin.last_login_time = datetime.now()
            admin.last_login_ip = ip
            session.add(admin)
            session.commit()
            
            # 创建 Token
            token = token_service.create_token_sync(admin, device, ip)
            
            return True, token, {
                "id": admin.id,
                "username": admin.username,
                "nickname": admin.nickname
            }
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """验证 Token"""
        return token_service.verify_token_sync(token)
    
    @staticmethod
    def logout(token: str) -> bool:
        """登出"""
        return token_service.delete_token_sync(token)


auth_service = AuthService()
