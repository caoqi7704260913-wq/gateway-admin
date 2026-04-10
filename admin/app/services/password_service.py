"""
密码哈希服务
"""
from passlib.hash import bcrypt


class PasswordService:
    
    @staticmethod
    def hash(password: str) -> str:
        """密码哈希"""
        return bcrypt.hash(password)
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.verify(plain_password, hashed_password)


password_service = PasswordService()
