"""
限流中间件

基于滑动窗口算法的 Redis 限流实现
支持降级策略：Redis 不可用时自动放行
"""

import time
from typing import Callable, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from loguru import logger

from app.utils.redis_manager import redis_manager
from app.utils.fallback_manager import fallback_manager
from config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    限流中间件
    
    使用滑动窗口算法，基于 Redis 存储计数
    支持降级：Redis 不可用时自动放行请求
    """

    def __init__(
        self,
        app,
        rate_key: str = "rate_limit",
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        """
        初始化限流中间件
        
        Args:
            app: FastAPI 应用
            rate_key: Redis 限流 key 前缀
            max_requests: 时间窗口内最大请求数，默认从配置读取
            window_seconds: 时间窗口大小（秒），默认从配置读取
            key_func: 自定义限流 key 生成函数，默认按 IP
        """
        super().__init__(app)
        self.rate_key = rate_key
        # 从配置读取限流参数
        self.max_requests = max_requests if max_requests is not None else settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds if window_seconds is not None else settings.RATE_LIMIT_WINDOW_SECONDS
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.key_func = key_func or self._default_key_func

    def _default_key_func(self, request: Request) -> str:
        """默认按客户端 IP 生成限流 key"""
        client_ip = request.client.host if request.client else "unknown"
        return f"{client_ip}"

    async def _check_rate_limit(self, key: str) -> tuple[bool, int, int]:
        """
        检查是否超过限流（使用 Redis ZSET 实现真正的滑动窗口）
        
        降级策略：
        - Redis 不可用时自动放行
        - 记录降级状态
        
        Args:
            key: 限流 key
            
        Returns:
            (is_allowed, remaining, reset_time)
            is_allowed: 是否允许请求
            remaining: 剩余请求次数
            reset_time: 重置时间戳
        """
        now = time.time()
        window_start = now - self.window_seconds
        reset_time = int(now + self.window_seconds)

        redis_key = f"{self.rate_key}:{key}"

        try:
            # 检查 Redis 是否可用
            if not redis_manager.client:
                logger.warning("Redis not available, rate limit bypassed")
                fallback_manager.set_fallback("redis", True)
                return True, self.max_requests, reset_time
            
            # 使用 ZSET 实现滑动窗口
            
            # 1. 删除窗口外的旧数据
            await redis_manager.client.zremrangebyscore(redis_key, 0, window_start)
            
            # 2. 获取当前窗口内的请求数
            current_count = await redis_manager.client.zcard(redis_key)
            
            remaining = max(0, self.max_requests - current_count)
            is_allowed = current_count < self.max_requests

            if is_allowed:
                # 添加当前请求到 ZSET，score 为时间戳，member 为唯一标识
                member = f"{now}:{hash(key)}"
                await redis_manager.client.zadd(redis_key, {member: now})
                # 设置过期时间（比窗口稍长，确保清理）
                await redis_manager.client.expire(redis_key, int(self.window_seconds * 2))
                remaining -= 1

            return is_allowed, remaining, reset_time

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # 限流服务异常时默认放行（降级）
            fallback_manager.set_fallback("redis", True)
            return True, self.max_requests, reset_time

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 限流未启用时跳过
        if not self.enabled:
            return await call_next(request)

        # 跳过限流的路径
        excluded_paths = ["/health", "/healthz", "/status", "/docs", "/redoc", "/openapi.json"]
        if request.url.path in excluded_paths:
            return await call_next(request)

        # 生成限流 key
        key = self.key_func(request)
        full_key = f"{self.rate_key}:{key}"

        # 检查限流
        is_allowed, remaining, reset_time = await self._check_rate_limit(full_key)

        if not is_allowed:
            reset_seconds = reset_time - int(time.time())
            logger.warning(f"Rate limit exceeded for {key}: {remaining}/{self.max_requests}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too Many Requests",
                    "message": f"请求过于频繁，请 {reset_seconds} 秒后重试",
                    "retry_after": reset_seconds
                },
                headers={"Retry-After": str(reset_seconds)}
            )

        # 执行请求
        response = await call_next(request)

        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


def get_rate_limiter(
    rate_key: str = "default",
    max_requests: Optional[int] = None,
    window_seconds: Optional[int] = None
) -> type[RateLimiterMiddleware]:
    """
    获取限流中间件类
    
    Args:
        rate_key: 限流策略标识
        max_requests: 最大请求数，默认从配置读取
        window_seconds: 时间窗口，默认从配置读取
    
    Returns:
        RateLimiterMiddleware 中间件类
    """
    return type(
        "RateLimitedApp",
        (RateLimiterMiddleware,),
        {
            "__init__": lambda self, app: RateLimiterMiddleware.__init__(
                self, app, rate_key, max_requests, window_seconds
            )
        }
    )
