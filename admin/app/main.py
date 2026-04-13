"""
后台管理服务 - FastAPI 应用入口
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from config import settings
from app.api.routes import router as api_router
from app.services.register_service import register_service
from app.services.config_service import config_service
from app.utils.redis_manager import redis_manager
from app.utils.http_client import http_client
from app.utils.database_pool import db_manager
from app.utils.fallback_manager import fallback_manager
from app.middleware.rate_limiter import RateLimiterMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("="*60)
    logger.info("Admin service starting...")
    logger.info("="*60)
    
    # 1. 初始化 HTTP 客户端
    await http_client.init()
    logger.info("HTTP client initialized")
    
    # 2. 初始化 Redis
    await redis_manager.init()
    logger.info("Redis connected")
    
    # 3. 初始化数据库连接池
    await db_manager.init()
    logger.info("Database connection pool initialized")
    
    # 3.1 创建数据库表（如果不存在）
    try:
        # 导入所有模型
        from app.models.schemas import Admin, Role, Permission, Menu
        await db_manager.create_tables_async()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Failed to create database tables: {e}")
    
    # 4. 从 Redis 获取并应用默认 CORS 配置
    cors_initialized = await config_service.init_default_cors()
    if cors_initialized:
        logger.info("CORS config initialized from Redis")
    else:
        logger.warning("Failed to initialize CORS config, using defaults")
    
    # 4.1 初始化默认数据（可选，通过环境变量控制）
    if settings.INIT_DEFAULT_DATA:
        try:
            from app.database import init_default_data
            await init_default_data()
            logger.info("Default data initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize default data: {e}")
    
    # 5. 注册到 Gateway（包含从 Redis 获取 HMAC Key 和 CORS 配置）
    registered = await register_service.register()
    if registered:
        logger.info("Registered to Gateway")
        logger.info("Note: Gateway will actively check health via /healthz endpoint")
    else:
        logger.warning("Failed to register to Gateway, will retry")
    
    logger.info("="*60)
    logger.info(f"Admin service started on port {settings.PORT}")
    logger.info("="*60)
    
    yield
    
    # 关闭时
    logger.info("="*60)
    logger.info("Admin service shutting down...")
    logger.info("="*60)
    
    await register_service.unregister()
    logger.info("Unregistered from Gateway")
    
    await redis_manager.close()
    logger.info("Redis connection closed")
    
    # 关闭数据库连接池
    await db_manager.async_close()
    logger.info("Database connection pool closed")
    
    await http_client.close()
    logger.info("HTTP client closed")
    
    logger.info("Admin service stopped")


app = FastAPI(
    title="后台管理服务",
    description="管理后台 API 服务",
    version="1.0.0",
    lifespan=lifespan
)

# 注册限流中间件（在所有路由之前）
app.add_middleware(RateLimiterMiddleware)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求的日志"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - "
        f"{process_time:.3f}s"
    )
    
    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/")
async def root():
    return {"message": "后台管理服务", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "admin"}


@app.get("/healthz")
async def healthz():
    """
    健康检查端点
    
    Gateway 会定期调用此端点进行主动健康检查
    """
    return {"status": "healthy", "service": "admin"}


@app.get("/status")
async def status():
    """
    服务状态端点（包含降级信息）
    """
    return {
        "status": "healthy",
        "service": "admin",
        "fallback": fallback_manager.get_status()
    }


if __name__ == "__main__":
    import uvicorn
    from config import settings
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_debug,
        ssl_certfile=settings.SSL_CERT_FILE if settings.SSL_ENABLED else None,
        ssl_keyfile=settings.SSL_KEY_FILE if settings.SSL_ENABLED else None
    )
