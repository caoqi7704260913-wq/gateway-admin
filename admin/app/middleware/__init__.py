"""
中间件包

包含各种 HTTP 中间件：
- rate_limiter: 限流中间件
- service_auth: 服务来源认证中间件（验证请求来自 Gateway 或已注册服务）
- audit_log: 操作审计中间件

注意：Admin Service 不直接验证 JWT，由 Gateway 通过 HMAC 验证后转发
"""

from app.middleware.rate_limiter import RateLimiterMiddleware, get_rate_limiter
from app.middleware.service_auth import ServiceSourceAuthMiddleware
from app.middleware.audit_log import AuditLogMiddleware

__all__ = [
    "RateLimiterMiddleware", 
    "get_rate_limiter",
    "ServiceSourceAuthMiddleware",
    "AuditLogMiddleware",
]
