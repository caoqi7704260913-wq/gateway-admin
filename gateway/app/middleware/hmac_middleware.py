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
    
    # 服务注册与发现（内部服务直连，不走 HTTP）
    #"/api/services/register",   # 服务注册
    #"/api/services/",           # 服务列表和详情
    #"/api/services/heartbeat",  # 心跳检测
    #"/api/services/deregister", # 服务注销
    
    # 内部服务间通信（需要 HMAC 验证，如需关闭请取消注释）
    # "/api/internal/",         # 内部服务间通信
    # "/api/config/cors",        # CORS 配置
    # "/api/config/reload",      # 配置热更新
]


class HMACMiddleware(BaseHTTPMiddleware):
    """HMAC 签名验证中间件"""

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        
        # 0. CORS 预检请求（OPTIONS）直接放行
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # 1. 检查是否需要验证（本地白名单 + 服务注册白名单）
        if self._is_excluded(request.url.path):
            return await call_next(request)
        
        # 2. 检查服务注册的白名单
        if await self._check_service_whitelist(request.url.path):
            return await call_next(request)

        # 3. HMAC 未启用时跳过验证
        if not settings.HMAC_ENABLED:
            return await call_next(request)

        # 4. 获取签名参数
        signature = request.headers.get("X-Signature")
        timestamp_str = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")

        # 5. 检查必要参数
        if not all([signature, timestamp_str, nonce]):
            return self._error_response(
                401,
                "Missing HMAC headers (X-Signature, X-Timestamp, X-Nonce required)"
            )

        # 6. 解析时间戳
        timestamp: int
        try:
            timestamp = int(timestamp_str)  # type: ignore[arg-type]
        except ValueError:
            return self._error_response(401, "Invalid timestamp format")

        # 7. 获取请求体
        body = await request.body()
        body_str = body.decode() if body else ""

        # 8. 验证签名（此时已确认 signature 和 nonce 不为 None）
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

        # 9. 签名验证通过，继续处理请求
        logger.debug(f"HMAC verified for {request.url.path}")
        return await call_next(request)

    def _is_excluded(self, path: str) -> bool:
        """检查路径是否需要排除"""
        for excluded in DEFAULT_EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True
        return False
    
    async def _check_service_whitelist(self, path: str) -> bool:
        """检查路径是否在服务注册的白名单中"""
        try:
            from app.utils.redis_manager import get_redis_manager
            redis = get_redis_manager()
            
            # 提取实际路径（去掉服务名前缀）
            # 例如: /admin-service/api/captcha/generate -> /api/captcha/generate
            parts = path.strip('/').split('/', 1)
            actual_path = '/' + parts[1] if len(parts) > 1 else path
            logger.debug(f"Original path: {path}, Actual path: {actual_path}")
            
            # 获取所有服务
            service_keys = await redis.keys("service:*:*")
            for key in service_keys:
                service_data = await redis.get(key)
                if service_data:
                    import json
                    service = json.loads(service_data)
                    whitelist = service.get('metadata', {}).get('global_whitelist', [])
                    
                    # 检查路径是否匹配白名单
                    for pattern in whitelist:
                        if self._match_path(actual_path, pattern):
                            logger.debug(f"Path {actual_path} matched whitelist pattern {pattern}")
                            return True
        except Exception as e:
            logger.error(f"Check service whitelist failed: {e}")
        
        return False
    
    def _match_path(self, path: str, pattern: str) -> bool:
        """简单路径匹配（支持 * 通配符）"""
        if pattern.endswith("/*"):
            prefix = pattern[:-2]
            return path.startswith(prefix)
        return path == pattern

    def _error_response(self, status_code: int, message: str) -> JSONResponse:
        """返回错误响应"""
        return JSONResponse(
            status_code=status_code,
            content={"error": message, "timestamp": int(time.time())}
        )
