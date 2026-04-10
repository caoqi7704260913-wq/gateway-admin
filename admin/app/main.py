"""
后台管理服务 - FastAPI 应用入口
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from loguru import logger
from app.api.routes import router as api_router
from app.services.register_service import register_service
from app.services.config_service import config_service
from app.utils.redis_manager import redis_manager
from app.utils.http_client import http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("Admin service starting...")
    
    # 初始化 HTTP 客户端
    await http_client.init()
    
    # 初始化 Redis
    await redis_manager.init()
    
    # 注册到 Gateway
    await register_service.register()
    
    # 启动心跳任务
    heartbeat_task = asyncio.create_task(register_service.heartbeat())
    
    # 应用默认 CORS 配置
    await config_service.set_cors_config(config_service.DEFAULT_CORS)
    
    logger.info("Admin service started on port 8001")
    
    yield
    
    # 关闭时
    logger.info("Admin service shutting down...")
    heartbeat_task.cancel()
    await register_service.unregister()
    await redis_manager.close()
    await http_client.close()
    logger.info("Admin service stopped")


app = FastAPI(
    title="后台管理服务",
    description="管理后台 API 服务",
    version="1.0.0",
    lifespan=lifespan
)


# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "后台管理服务", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "admin"}


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
