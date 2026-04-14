"""
HMAC 签名验证中间件

用于验证请求的 HMAC 签名，防止请求被篡改
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from loguru import logger

from app.utils.hmac_validator import get_hmac_validator
from config import settings


# 默认排除路径（可在配置中修改）
DEFAULT_EXCLUDED_PATHS = [
    # 健康检查与监控
    "/health",
    "/healthz",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    
    # 服务注册与发现（内部服务直连 Consul，不走 HTTP）
    "/api/services/register",   # 服务注册
    "/api/services/",           # 服务列表和详情
    "/api/services/heartbeat",  # 心跳检测
    "/api/services/deregister", # 服务注销
    
    # 内部服务间通信（需要 HMAC 验证，如需关闭请取消注释）
    # "/api/internal/",         # 内部服务间通信
    # "/api/config/cors",        # CORS 配置
    # "/api/config/reload",      # 配置热更新
]


class HMACMiddleware(BaseHTTPMiddleware):
    """HMAC 签名验证中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        
        # 1. 检查是否需要验证
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # 2. HMAC 未启用时跳过验证
        if not settings.HMAC_ENABLED:
            return await call_next(request)

        # 3. 获取签名参数
        signature = request.headers.get("X-Signature")
        timestamp_str = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")

        # 4. 检查必要参数
        if not all([signature, timestamp_str, nonce]):
            return self._error_response(
                401,
                "Missing HMAC headers (X-Signature, X-Timestamp, X-Nonce required)"
            )

        # 5. 解析时间戳
        timestamp: int
        try:
            timestamp = int(timestamp_str)  # type: ignore[arg-type]
        except ValueError:
            return self._error_response(401, "Invalid timestamp format")

        # 6. 获取请求体
        body = await request.body()
        body_str = body.decode() if body else ""

        # 7. 验证签名（此时已确认 signature 和 nonce 不为 None）
        validator = get_hmac_validator()
        is_valid, error_msg = await validator.verify_signature(  # 改为异步调用
            signature=signature,  # type: ignore[arg-type]
            body=body_str,
            timestamp=timestamp,
            nonce=nonce  # type: ignore[arg-type]
        )

        if not is_valid:
            logger.warning(
                f"HMAC verification failed for {request.url.path}: {error_msg}"
            )
            return self._error_response(401, f"HMAC verification failed: {error_msg}")

        # 8. 签名验证通过，继续处理请求
        logger.debug(f"HMAC verified for {request.url.path}")
        return await call_next(request)

    def _is_excluded(self, path: str) -> bool:
        """检查路径是否需要排除"""
        for excluded in DEFAULT_EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True
        return False

    def _error_response(self, status_code: int, message: str) -> JSONResponse:
        """返回错误响应"""
        return JSONResponse(
            status_code=status_code,
            content={"error": message, "timestamp": int(time.time())}
        )
