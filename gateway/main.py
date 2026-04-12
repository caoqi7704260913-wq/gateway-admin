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
import asyncio  #  添加 asyncio 导入
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
from app.utils.redis_manager import get_redis_manager, close  #  导入 close 函数
from app.utils.consul_manager import get_consul_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 验证关键配置
    if settings.HMAC_ENABLED and not settings.HMAC_SECRET_KEY:
        raise RuntimeError(
            "HMAC 已启用但未配置 HMAC_SECRET_KEY！\n"
            "请通过以下方式之一配置：\n"
            "1. 环境变量: export HMAC_SECRET_KEY='your-secret-key'\n"
            "2. .env 文件: HMAC_SECRET_KEY=your-secret-key"
        )
    
    # 启动时
    redis = get_redis_manager()
    from app.utils.redis_manager import get_client  #  导入模块级函数
    get_client()  #  调用模块级同步函数

    # 初始化 HTTP 客户端
    from app.utils.httpx_manager import HTTPClientManager
    HTTPClientManager.get_client()

    # 加载配置到内存（CORS、HMAC 密钥）
    config_manager = get_config_manager()
    await config_manager.load_configs()

    consul = get_consul_manager()
    if settings.CONSUL_ENABLED and consul.is_healthy():
        logger.info(f"Consul 已连接: {settings.CONSUL_HOST}:{settings.CONSUL_PORT}")

    # 启动健康检查服务（从 Redis 读取已注册的服务）
    from app.services.health_checker import HealthChecker
    health_checkers = []
    
    try:
        # 获取所有已注册的服务
        redis = get_redis_manager()
        service_keys = await redis.keys("service:*:*")
        
        # 提取唯一的服务名称
        service_names = set()
        for key in service_keys:
            parts = key.split(":")
            if len(parts) >= 2:
                service_names.add(parts[1])
        
        # 为每个服务启动健康检查
        for service_name in service_names:
            # 获取该服务的第一个实例信息（用于获取 host/port）
            pattern = f"service:{service_name}:*"
            instances = await redis.keys(pattern)
            if instances:
                import json
                first_instance_data = await redis.get(instances[0])
                if first_instance_data:
                    instance = json.loads(first_instance_data)
                    checker = HealthChecker(
                        name=service_name,
                        host=instance.get('host', 'localhost'),
                        port=instance.get('port', 80),
                        interval=10  # 每10秒检查一次
                    )
                    task = asyncio.create_task(checker.start_health_check())
                    health_checkers.append((checker, task))
                    logger.info(f" 已启动服务 [{service_name}] 的健康检查")
        
        if not health_checkers:
            logger.info("ℹ 暂无已注册的服务，健康检查未启动")
    except Exception as e:
        logger.warning(f"启动健康检查服务失败: {e}")

    logger.info(f"Gateway 启动成功: http{'s' if settings.HTTPS_ENABLED else ''}://{settings.HOST}:{settings.PORT}")

    yield

    # 关闭时
    # 停止健康检查服务
    for checker, task in health_checkers:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    await HTTPClientManager.close()
    await close()  #  使用模块级 close 函数
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
    #  根据配置决定是否启用 HTTPS
    ssl_certfile = None
    ssl_keyfile = None
    
    if settings.HTTPS_ENABLED:
        if not settings.SSL_CERT_PATH or not settings.SSL_KEY_PATH:
            logger.warning("HTTPS 已启用但未配置 SSL 证书路径，将使用 HTTP")
            logger.warning("   请在 .env 文件中配置 SSL_CERT_PATH 和 SSL_KEY_PATH")
        else:
            ssl_certfile = settings.SSL_CERT_PATH
            ssl_keyfile = settings.SSL_KEY_PATH
            logger.info(f"HTTPS 已启用 - 证书: {settings.SSL_CERT_PATH}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        ssl_certfile=ssl_certfile,  # 显式传递 SSL 参数
        ssl_keyfile=ssl_keyfile
    )
