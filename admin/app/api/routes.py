"""
API 路由
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from app.services.auth_service import auth_service
from app.services.token_service import token_service
from app.services.config_service import config_service

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """获取客户端IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_token(authorization: Optional[str] = Header(None)) -> str:
    """从请求头获取 Token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证Token")
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


async def verify_token(token: str = Depends(get_token)) -> dict:
    """验证 Token"""
    data = await token_service.verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    # 将原始 token 存入返回数据
    data["_token"] = token
    return data


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    user: Optional[dict] = None


class CorsConfigRequest(BaseModel):
    allow_origins: list
    allow_credentials: bool = True
    allow_methods: list
    allow_headers: list


class HmacKeyRequest(BaseModel):
    app_id: str
    secret_key: str


# ============ 认证相关 ============

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """登录"""
    ip = get_client_ip(req)
    success, result, user_info = auth_service.login(request.username, request.password, ip=ip)
    if not success:
        raise HTTPException(status_code=401, detail=result)
    return LoginResponse(
        token=result,
        user=user_info
    )


@router.post("/auth/logout")
async def logout(token: dict = Depends(verify_token)):
    """登出"""
    await token_service.delete_token(token.get("_token", ""))
    return {"message": "登出成功"}


# ============ CORS 配置 ============

@router.get("/config/cors")
async def get_cors_config(_: dict = Depends(verify_token)):
    """获取 CORS 配置（需认证）"""
    config = await config_service.get_cors_config()
    return config


@router.post("/config/cors")
async def set_cors_config(config: CorsConfigRequest, _: dict = Depends(verify_token)):
    """设置 CORS 配置"""
    await config_service.set_cors_config(config.model_dump())
    return {"message": "CORS 配置已更新"}


# ============ HMAC Key 管理 ============

@router.get("/config/hmac")
async def get_hmac_keys(_: dict = Depends(verify_token)):
    """获取所有 HMAC Keys（已脱敏）"""
    raw_keys = await config_service.get_all_hmac_keys()
    # 脱敏处理
    keys = {
        app_id: f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        for app_id, key in raw_keys.items()
    }
    return {"keys": keys}


@router.post("/config/hmac")
async def set_hmac_key(req: HmacKeyRequest, _: dict = Depends(verify_token)):
    """设置 HMAC Key"""
    await config_service.set_hmac_key(req.app_id, req.secret_key)
    return {"message": f"HMAC Key for {req.app_id} 已设置"}


@router.delete("/config/hmac/{app_id}")
async def delete_hmac_key(app_id: str, _: dict = Depends(verify_token)):
    """删除 HMAC Key"""
    await config_service.delete_hmac_key(app_id)
    return {"message": f"HMAC Key for {app_id} 已删除"}


# ============ 健康检查 ============

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "admin"}
