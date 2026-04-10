"""
应用配置
"""
from typing import Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "后台管理服务"
    DEBUG: Union[bool, str] = True
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # HTTPS 配置
    SSL_ENABLED: bool = False
    SSL_CERT_FILE: str = ""
    SSL_KEY_FILE: str = ""
    
    # 服务配置
    SERVICE_NAME: str = "admin-service"
    SERVICE_IP: str = "localhost"
    SERVICE_WEIGHT: int = 1
    SERVICE_TAGS: str = "admin,management"
    SERVICE_DESCRIPTION: str = "后台管理服务"
    
    # Gateway 配置
    GATEWAY_URL: str = "http://localhost:8000"
    SERVICE_TTL: int = 300

    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://admin:123123@localhost:3306/admin"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "123123"
    
    # Token 配置
    TOKEN_EXPIRATION_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def is_debug(self) -> bool:
        """安全的 DEBUG 值"""
        if isinstance(self.DEBUG, bool):
            return self.DEBUG
        return str(self.DEBUG).lower() in ("true", "1", "yes")


settings = Settings()
