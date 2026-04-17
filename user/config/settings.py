"""
应用配置
"""
import os
from typing import Union
from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    APP_NAME: str = "用户服务"
    APP_DESCRIPTION: str = "用户服务"
    APP_VERSION: str = "0.1.0"
    DEBUG: Union[bool, str] = True
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    

    @property
    def is_debug(self) -> bool:
        """安全的 DEBUG 值"""
        if isinstance(self.DEBUG, bool):
            return self.DEBUG
        return str(self.DEBUG).lower() in ("true", "1", "yes")

    # HTTPS 配置
    SSL_ENABLED: bool = False
    SSL_CERT_FILE: str = ""
    SSL_KEY_FILE: str = ""
    
    # 服务配置
    SERVICE_NAME: str = "user-service"
    SERVICE_IP: str = "127.0.0.1"
    SERVICE_WEIGHT: int = 1
    SERVICE_TAGS: str = "user,api"
    SERVICE_DESCRIPTION: str = "用户服务"
    
    # HMAC 白名单配置（这些路径不需要 HMAC 签名验证）
    HMAC_WHITELIST: str = "/api/auth/*,/api/captcha/*"
    
    # Gateway 配置
    GATEWAY_URL: str = "http://localhost:9000"
    GATEWAY_APP_ID: str = "gateway"  # Gateway 的应用 ID
    SERVICE_TTL: int = 300
    HMAC_SECRET_KEY: str = ""  # HMAC 密钥（从 Redis 获取，留空表示使用默认）

    # 数据库配置
    DATABASE_URL: str = "mysql+pymysql://root:123123@localhost:3306/user_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "123123"
    REDIS_DB: int = 0
    
    # Redis 集群配置
    REDIS_CLUSTER_MODE: bool = False
    REDIS_CLUSTER_NODES: str = ""  # 逗号分隔的节点列表，如 "host1:6379,host2:6379"
    REDIS_POOL_SIZE: int = 20
    REDIS_DECODE_RESPONSES: bool = True
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    
    # Token 配置
    TOKEN_EXPIRATION_MINUTES: int = 60
    
    # 限流配置
    RATE_LIMIT_ENABLED: bool = True  # 是否启用限流
    RATE_LIMIT_MAX_REQUESTS: int = 100  # 时间窗口内最大请求数
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # 时间窗口大小（秒）
    
    # 公开路径白名单（支持通配符 *）
    PUBLIC_PATHS: str = "/healthz,/docs,/openapi.json,/redoc,/api/auth/*,/api/captcha/*"
    
    # 审计日志敏感路径（支持通配符 *）
    AUDIT_SENSITIVE_PATHS: str = "/api/users/*,/api/profiles/*"
    
    # 初始化配置
    INIT_DEFAULT_DATA: bool = False  # 是否初始化默认数据

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
