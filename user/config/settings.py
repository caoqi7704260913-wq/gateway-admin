"""
应用配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    SERVICE_NAME: str = "user-service"
    SERVICE_IP: str = "localhost"
    PORT: int = 8002
    HOST: str = "0.0.0.0"
    
    # Gateway 配置
    GATEWAY_URL: str = "http://localhost:9000"
    SSL_ENABLED: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/user_db"
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "123123"
    REDIS_DB: int = 0
    
    # 服务元数据
    SERVICE_TAGS: str = "user,api"
    SERVICE_WEIGHT: int = 100
    SERVICE_DESCRIPTION: str = "User Service"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
