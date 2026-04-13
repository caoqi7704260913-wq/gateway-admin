"""
应用配置
"""
import os
from typing import Union
from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    GATEWAY_URL: str = "http://localhost:9000"
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
    
    # 限流配置
    RATE_LIMIT_ENABLED: bool = True  # 是否启用限流
    RATE_LIMIT_MAX_REQUESTS: int = 100  # 时间窗口内最大请求数
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # 时间窗口大小（秒）
    
    # 初始化配置
    INIT_DEFAULT_DATA: bool = False  # 是否初始化默认数据（管理员、角色、权限等）

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
