"""
服务实例数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class WhitelistConfig(BaseModel):
    """白名单配置模型"""
    type: str = Field(..., description="白名单类型: ip, header, parameter")
    value: str = Field(..., description="白名单值")
    description: Optional[str] = Field(None, description="描述")


import uuid

def generate_service_id() -> str:
    """生成服务实例唯一标识"""
    return f"{uuid.getnode():012x}-{uuid.uuid4().hex[:8]}"


class ServiceBase(BaseModel):
    """服务实例基础数据模型"""
    id: str = Field(default_factory=generate_service_id, description="服务实例唯一标识")
    host: str = Field(..., description="服务实例所在主机")
    name: str = Field(..., description="服务名称")
    url: str = Field(..., description="服务地址")
    ip: str = Field(..., description="服务IP地址")
    port: int = Field(..., description="服务端口")
    weight: int = Field(default=1, description="权重")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    global_whitelist: List[WhitelistConfig] = Field(default_factory=list, description="全局白名单配置")
    status: str = Field(default="healthy", description="健康状态")
    last_heartbeat: Optional[datetime] = Field(default=None, description="最后心跳时间")


class ServiceCreate(ServiceBase):
    """创建服务实例请求模型"""
    pass


class ServiceUpdate(BaseModel):
    """更新服务实例请求模型"""
    name: Optional[str] = Field(None, description="服务名称")
    url: Optional[str] = Field(None, description="服务地址")
    weight: Optional[int] = Field(None, ge=0, description="权重")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    global_whitelist: Optional[List[WhitelistConfig]] = Field(None, description="全局白名单配置")
    status: Optional[str] = Field(None, description="健康状态")


class ServiceResponse(ServiceBase):
    """服务实例响应模型"""
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True