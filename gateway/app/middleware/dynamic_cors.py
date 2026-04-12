"""
动态 CORS 中间件

从 Redis 读取 CORS 配置，支持运行时热更新
"""

from typing import List, Optional, Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from loguru import logger

from app.services.config_manager import get_config_manager
from config import settings


# 类级别的 CORS 配置缓存（启动时加载）
_cors_cache: Dict[str, Any] = {
    "origins": settings.CORS_ORIGINS,
    "credentials": settings.CORS_ALLOW_CREDENTIALS,
    "methods": settings.CORS_ALLOW_METHODS,
    "headers": settings.CORS_ALLOW_HEADERS,
}


def update_cors_cache(config: Dict[str, Any]) -> None:
    """
    更新 CORS 缓存

    Args:
        config: CORS 配置字典
    """
    global _cors_cache
    _cors_cache = {
        "origins": config.get("origins", settings.CORS_ORIGINS),
        "credentials": config.get("credentials", settings.CORS_ALLOW_CREDENTIALS),
        "methods": config.get("methods", settings.CORS_ALLOW_METHODS),
        "headers": config.get("headers", settings.CORS_ALLOW_HEADERS),
    }
    logger.info(f"CORS缓存已更新: {len(_cors_cache['origins'])} 个源")


def get_cors_cache() -> Dict[str, Any]:
    """获取 CORS 缓存"""
    return _cors_cache


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    动态 CORS 中间件

    支持从 Redis 实时读取 CORS 配置，无需重启服务
    """

    def __init__(self, app):
        super().__init__(app)
        self.config_manager = get_config_manager()

    def _get_cache(self):
        """获取缓存的配置"""
        return _cors_cache

    def _is_origin_allowed(self, origin: str) -> bool:
        """检查 origin 是否允许"""
        if not origin:
            return False

        cache = self._get_cache()
        origins = cache["origins"]

        # 检查通配符
        if "*" in origins:
            return True

        # 精确匹配
        if origin in origins:
            return True

        # 前缀匹配（支持子域名）
        for allowed in origins:
            if allowed.startswith("http://") or allowed.startswith("https://"):
                if origin.startswith(allowed.rstrip("/")):
                    return True
                # 支持 *.domain.com 格式
                if allowed.startswith("*."):
                    domain = allowed[2:]
                    if origin.endswith(domain) or origin.endswith(domain.rstrip("/")):
                        return True

        return False

    def _get_allow_origin(self, request: Request) -> str:
        """获取允许的 origin"""
        cache = self._get_cache()
        origins = cache["origins"]
        credentials = cache["credentials"]

        origin = request.headers.get("origin")
        if not origin:
            return "*" if "*" in origins else ""

        if self._is_origin_allowed(origin):
            # 当启用凭证时，不能返回通配符，必须返回具体 origin
            if "*" in origins and not credentials:
                return "*"
            return origin

        # Origin 不被允许时，不设置 CORS 头（而不是返回 "null"）
        return ""

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        cache = self._get_cache()

        # 获取请求信息
        method = request.method
        origin = request.headers.get("origin")

        # 构建响应
        response = await call_next(request)

        # 处理 CORS 预检请求
        if method == "OPTIONS":
            allow_origin = self._get_allow_origin(request)

            if allow_origin:
                response.headers["Access-Control-Allow-Origin"] = allow_origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(cache["methods"])
                response.headers["Access-Control-Allow-Headers"] = ", ".join(cache["headers"])
                response.headers["Access-Control-Allow-Credentials"] = str(cache["credentials"]).lower()
                response.headers["Access-Control-Max-Age"] = "3600"
                response.status_code = 200
            return response

        # 添加 CORS 响应头
        allow_origin = self._get_allow_origin(request)
        if allow_origin:
            response.headers["Access-Control-Allow-Origin"] = allow_origin
            if cache["credentials"]:
                response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


def get_dynamic_cors_middleware() -> type[DynamicCORSMiddleware]:
    """获取动态 CORS 中间件类"""
    return DynamicCORSMiddleware
