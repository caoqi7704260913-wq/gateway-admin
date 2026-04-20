"""
项目配置文件
管理应用的各种配置参数
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Union


# Gateway 项目根目录（当前文件所在目录的上级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    """应用配置类"""

    # 应用配置
    APP_NAME: str = "Gateway API"
    APP_VERSION: str = "1.0.0"
    DEBUG: Union[bool, str] = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "release")
        return True
    
    @property
    def is_debug(self) -> bool:
        """安全的 DEBUG 值"""
        if isinstance(self.DEBUG, bool):
            return self.DEBUG
        return str(self.DEBUG).lower() in ("true", "1", "yes")

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 9000

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "123123"
    REDIS_DB: int = 0
    REDIS_CLUSTER_MODE: bool = False # 是否启用Redis集群模式
    REDIS_CLUSTER_NODES: list = []  # 集群模式节点列表，如 ["localhost:6379", "localhost:6380"]
    REDIS_POOL_SIZE: int = 10
    REDIS_DECODE_RESPONSES: bool = True
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_TTL: int = 30  # 服务实例心跳过期时间（秒）

    # CORS配置
    CORS_ORIGINS: list = ["http://localhost:9527", "http://127.0.0.1:9527", "http://localhost:9528", "http://127.0.0.1:9528", "http://localhost:9529", "http://127.0.0.1:9529"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    CORS_ALLOW_HEADERS: list = ["Authorization", "Content-Type", "X-Requested-With"]

    # JWT配置（如果需要）
   # JWT_SECRET_KEY: str = "4Wrx1pS4BxDBCuAdXokNqgrinR2E8JlGlma5pxC8V-k"
   # JWT_ALGORITHM: str = "HS256"
    #JWT_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    HMAC_SECRET_KEY: str = ""  # ✅ 生产环境必须通过环境变量或 .env 文件配置
    HMAC_ENABLED: bool = True  # 是否启用 HMAC 验证
    HMAC_TIMESTAMP_TOLERANCE: int = 300  # 时间戳容差（秒）
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 其他配置
    TIMEZONE: str = "Asia/Shanghai"

    # HTTPX配置
    HTTP_TIMEOUT: int = 10  # 单位秒
    REQUEST_TIMEOUT: int = 30  # 请求转发超时（秒）
    LOAD_BALANCER_STRATEGY: str = "weighted_round_robin"  # 负载均衡策略
    HTTPS_ENABLED: bool = False  # 是否启用HTTPS
    SSL_VERIFY: bool = False  # 是否验证证书
    SSL_CA_BUNDLE: Optional[str] = None  # SSL证书路径，HTTPS启用时使用
    SSL_CERT_PATH: Optional[str] = None  # SSL证书路径，HTTPS启用时使用
    SSL_KEY_PATH: Optional[str] = None  # SSL私钥路径，HTTPS启用时使用
    SSL_CERT_REQUIRED: bool = False  # 是否要求客户端提供证书
    SSL_PROTOCOL: str = ""  # SSL协议版本
    SSL_CIPHERS: Optional[str] = None  # SSL加密套件
    SSL_VERSION: str = ""  # SSL版本
    HTTP_MAX_KEEPALIVE: int = 10  # 最大保持连接数
    HTTP_MAX_CONNECTIONS: int = 100  # 最大连接数
    HTTP_HTTP2_ENABLED: bool = False  # 是否启用 HTTP/2
    HTTP_CONNECT_TIMEOUT: int = 5  # 连接超时时间
    HTTP_READ_TIMEOUT: int = 5  # 读取超时时间
    HTTP_WRITE_TIMEOUT: int = 5  # 写入超时时间
    HTTP_POOL_TIMEOUT: int = 5  # 连接池超时时间
    

    """Consul 配置"""
    CONSUL_HOST: str = "localhost"
    CONSUL_PORT: int =  8500
    CONSUL_ENABLED: bool = False #  是否启用 Consul 服务发现
    CONSUL_TOKEN: Optional[str] = None
    CONSUL_SCHEME: str = "http"
    CONSUL_VERIFY: bool = False # 是否验证 Consul 的 TLS 证书
    
    # Consul 集群模式
    CONSUL_CLUSTER_ENABLED: bool = False # 是否启用 Consul 集群模式
    CONSUL_CLUSTER_NODES: str = ""  # 集群节点列表，格式为 "host1:port1,host2:port2,host3:port3"
    CONSUL_DC: str = "dc1"  # Consul 数据中心名称

    # 限流配置
    RATE_LIMIT_ENABLED: bool = True  # 是否启用限流
    RATE_LIMIT_MAX_REQUESTS: int = 100  # 每时间窗口最大请求数
    RATE_LIMIT_WINDOW_SECONDS: int = 60  # 时间窗口大小（秒）
    
    # Gateway 系统级白名单配置（不需要 Token 验证的路径）
    SYSTEM_WHITELIST: str = "/api/services/,/healthz,/docs,/openapi.json,/redoc"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# 创建全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """
    获取配置实例

    Returns:
        Settings: 配置实例
    """
    return settings
