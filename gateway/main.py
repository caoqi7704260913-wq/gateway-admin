"""
Gateway 主入口

整合所有组件：
- HMAC 中间件
- 限流中间件
- 动态 CORS 中间件
- API 路由
- 请求转发
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from loguru import logger
import uvicorn

from config import settings
from app.middleware.hmac_middleware import HMACMiddleware
from app.middleware.rate_limiter import RateLimiter
from app.middleware.dynamic_cors import DynamicCORSMiddleware
from app.api import routes as api_routes
from app.services.router import get_router
from app.services.config_manager import get_config_manager
from app.utils.redis_manager import get_redis_manager
from app.utils.consul_manager import get_consul_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    redis = get_redis_manager()
    await redis.get_client()  # 初始化 Redis 连接

    # 加载配置到内存（CORS、HMAC 密钥）
    config_manager = get_config_manager()
    await config_manager.load_configs()

    consul = get_consul_manager()
    if settings.CONSUL_ENABLED and consul.is_healthy():
        logger.info(f"Consul 已连接: {settings.CONSUL_HOST}:{settings.CONSUL_PORT}")

    logger.info(f"Gateway 启动成功: http://{settings.HOST}:{settings.PORT}")

    yield

    # 关闭时
    await redis.close()
    if settings.CONSUL_ENABLED:
        await consul.close()
    logger.info("Gateway 已停止")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# CORS 中间件（动态从 Redis 读取配置）
app.add_middleware(DynamicCORSMiddleware)

# HMAC 验证中间件
app.add_middleware(HMACMiddleware)

# 限流中间件（从 settings 读取配置）
app.add_middleware(RateLimiter, rate_key="api")

# API 路由
app.include_router(api_routes.router)


# 代理路由 - 捕获所有路径转发到后端
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str):
    """
    请求转发路由
    
    将请求转发到对应的后端服务
    """
    router = get_router()
    return await router.route(request)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
