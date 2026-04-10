"""
API 路由

提供网关管理接口：
- 服务注册/注销
- 健康检查
- 网关状态
- CORS 配置管理
- HMAC 密钥管理
- 熔断器状态
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator, field_serializer
from typing import Optional, List
from loguru import logger

from app.services.discovery import get_service_discovery
from app.services.config_manager import get_config_manager
from app.services.circuit_breaker import CircuitBreakerRegistry, CircuitBreakerStats
from app.models.service import ServiceBase
from app.api.validators import validator, ValidationError

router = APIRouter()


# ==================== 请求模型 ====================

class ServiceRegisterRequest(BaseModel):
    """服务注册请求"""
    name: str
    host: str
    port: int
    ip: Optional[str] = None
    url: Optional[str] = None
    weight: int = 1
    metadata: Optional[dict] = None


class CORSConfigRequest(BaseModel):
    """CORS 配置请求"""
    origins: List[str]
    credentials: bool = True
    methods: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    headers: List[str] = ["Authorization", "Content-Type", "X-Requested-With"]


class HMACKeyRequest(BaseModel):
    """HMAC 密钥请求"""
    app_id: str
    secret_key: Optional[str] = None


class HMACKeyResponse(BaseModel):
    """HMAC 密钥响应（脱敏）"""
    app_id: str
    secret_key: str

    @field_serializer('secret_key')
    def serialize_secret_key(self, key: str) -> str:
        if len(key) <= 8:
            return '*' * len(key)
        return f"{key[:4]}...{key[-4:]}"


# ==================== 服务注册与发现 ====================

@router.post("/api/services/register")
async def register_service(req: ServiceRegisterRequest):
    """
    注册服务实例

    服务启动时调用此接口注册到网关
    """
    try:
        # 参数验证
        name = validator.validate_service_name(req.name)
        host = validator.validate_host(req.host)
        port = validator.validate_port(req.port)
        weight = validator.validate_weight(req.weight)
        url = validator.validate_url(req.url)
        ip = validator.validate_host(req.ip) if req.ip else host
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    service = ServiceBase(
        name=name,
        host=host,
        ip=ip,
        port=port,
        url=url or f"http://{host}:{port}",
        weight=weight,
        metadata=req.metadata or {},
        status="healthy"
    )

    discovery = get_service_discovery()
    success = await discovery.register_service(service)

    if success:
        return {"message": "Service registered", "service_id": service.id}
    raise HTTPException(status_code=500, detail="Failed to register service")


@router.delete("/api/services/{service_name}")
async def deregister_service(service_name: str, service_id: Optional[str] = None):
    """
    注销服务实例

    服务关闭时调用此接口注销
    """
    try:
        service_name = validator.validate_service_name(service_name)
        if service_id:
            service_id = validator.validate_service_id(service_id)
    except HTTPException:
        raise

    discovery = get_service_discovery()

    if service_id:
        service = await discovery.get_service(service_name, service_id)
        if service:
            redis_key = f"service:{service_name}:{service_id}"
            await discovery.redis_manager.delete(redis_key)
            return {"message": "Service deregistered"}

    return {"message": "Service not found"}


@router.get("/api/services/{service_name}")
async def list_services(service_name: str):
    """
    获取服务实例列表
    """
    try:
        service_name = validator.validate_service_name(service_name)
    except HTTPException:
        raise

    discovery = get_service_discovery()
    services = await discovery.get_healthy_services(service_name)

    return {
        "service_name": service_name,
        "count": len(services),
        "services": [s.model_dump() for s in services]
    }


@router.get("/api/services/{service_name}/{service_id}")
async def get_service(service_name: str, service_id: str):
    """
    获取指定服务实例
    """
    try:
        service_name = validator.validate_service_name(service_name)
        service_id = validator.validate_service_id(service_id)
    except HTTPException:
        raise

    discovery = get_service_discovery()
    service = await discovery.get_service(service_name, service_id)

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return service.model_dump()


# ==================== 健康检查 ====================

@router.get("/health")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "healthy", "service": "gateway"}


@router.get("/")
async def root():
    """
    根路径
    """
    return {"service": "Gateway API", "version": "1.0.0"}


# ==================== CORS 配置管理 ====================

@router.get("/api/config/cors")
async def get_cors_config():
    """
    获取 CORS 配置
    """
    config = get_config_manager()
    cors_config = await config.get_cors_config()
    if cors_config:
        return cors_config
    return {"message": "CORS配置未初始化"}


@router.put("/api/config/cors")
async def update_cors_config(req: CORSConfigRequest):
    """
    更新 CORS 配置
    """
    try:
        origins = validator.validate_cors_origins(req.origins)
        methods = validator.validate_cors_methods(req.methods)
        headers = validator.validate_cors_headers(req.headers)
    except HTTPException:
        raise

    config = get_config_manager()
    await config.set_cors_config({
        "origins": origins,
        "credentials": req.credentials,
        "methods": methods,
        "headers": headers
    })
    return {"message": "CORS配置已更新"}


@router.post("/api/config/cors/origins")
async def add_cors_origin(origin: str):
    """
    添加 CORS 允许的源
    """
    try:
        origin = validator.validate_cors_origin(origin)
    except HTTPException:
        raise

    config = get_config_manager()
    await config.add_cors_origin(origin)
    return {"message": f"已添加: {origin}"}


@router.delete("/api/config/cors/origins")
async def remove_cors_origin(origin: str):
    """
    移除 CORS 允许的源
    """
    try:
        origin = validator.validate_cors_origin(origin)
    except HTTPException:
        raise

    config = get_config_manager()
    await config.remove_cors_origin(origin)
    return {"message": f"已移除: {origin}"}


# ==================== HMAC 密钥管理 ====================

@router.post("/api/config/hmac/key")
async def create_hmac_key(req: HMACKeyRequest):
    """
    创建或更新 HMAC 密钥

    内部服务注册后调用此接口获取密钥
    """
    try:
        app_id = validator.validate_app_id(req.app_id)
        secret_key = validator.validate_secret_key(req.secret_key)
    except HTTPException:
        raise

    config = get_config_manager()
    secret_key = await config.create_hmac_key(app_id, secret_key)
    return {"app_id": app_id, "secret_key": secret_key}


@router.get("/api/config/hmac/key/{app_id}")
async def get_hmac_key(app_id: str):
    """
    获取 HMAC 密钥
    """
    try:
        app_id = validator.validate_app_id(app_id)
    except HTTPException:
        raise

    config = get_config_manager()
    secret_key = await config.get_hmac_key(app_id)
    if secret_key:
        return HMACKeyResponse(app_id=app_id, secret_key=secret_key)
    raise HTTPException(status_code=404, detail="密钥不存在")


@router.delete("/api/config/hmac/key/{app_id}")
async def delete_hmac_key(app_id: str):
    """
    删除 HMAC 密钥
    """
    try:
        app_id = validator.validate_app_id(app_id)
    except HTTPException:
        raise

    config = get_config_manager()
    success = await config.delete_hmac_key(app_id)
    if success:
        return {"message": f"密钥已删除: {app_id}"}
    raise HTTPException(status_code=404, detail="密钥不存在")


@router.get("/api/config/hmac/keys")
async def list_hmac_keys():
    """
    获取所有 HMAC 密钥的 app_id 列表
    """
    config = get_config_manager()
    keys = await config.list_hmac_keys()
    return {"app_ids": keys, "count": len(keys)}


# ==================== 熔断器状态 ====================

@router.get("/api/circuit-breakers")
async def get_circuit_breakers():
    """
    获取所有熔断器状态
    """
    stats = CircuitBreakerRegistry.get_all_stats()
    return {"circuit_breakers": stats, "count": len(stats)}


@router.get("/api/circuit-breakers/{name}")
async def get_circuit_breaker(name: str):
    """
    获取指定熔断器状态
    """
    try:
        name = validator.validate_service_name(name, "name")
    except HTTPException:
        raise

    stats = CircuitBreakerRegistry.get_all_stats()
    if name in stats:
        return stats[name]
    raise HTTPException(status_code=404, detail="熔断器不存在")


@router.post("/api/circuit-breakers/{name}/reset")
async def reset_circuit_breaker(name: str):
    """
    重置指定熔断器
    """
    try:
        name = validator.validate_service_name(name, "name")
    except HTTPException:
        raise

    stats = CircuitBreakerRegistry.get_all_stats()
    if name in stats:
        breaker = CircuitBreakerRegistry.get(name)
        breaker._stats = CircuitBreakerStats()
        return {"message": f"熔断器 {name} 已重置"}
    raise HTTPException(status_code=404, detail="熔断器不存在")
