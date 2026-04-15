"""
权限管理 API
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database_pool import get_db_async
from app.api.routes import verify_token
from app.models.schemas import Permission
from pydantic import BaseModel, Field

router = APIRouter(prefix="/permissions", tags=["权限管理"])


class PermissionCreate(BaseModel):
    """创建权限请求"""
    code: str = Field(..., max_length=100, description="权限代码")
    name: str = Field(..., max_length=100, description="权限名称")
    description: Optional[str] = Field(None, description="描述")


class PermissionUpdate(BaseModel):
    """更新权限请求"""
    name: Optional[str] = Field(None, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, description="描述")


class PermissionResponse(BaseModel):
    """权限响应"""
    id: int
    code: str
    name: str
    description: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    """权限列表响应"""
    total: int
    items: List[PermissionResponse]


@router.get("/", response_model=PermissionListResponse)
async def list_permissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    name: Optional[str] = Query(None, description="权限名称搜索"),
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """获取权限列表"""
    from sqlalchemy import select, func
    
    query = select(Permission)
    count_query = select(func.count(Permission.id))
    
    if name:
        query = query.where(Permission.name.like(f"%{name}%"))
        count_query = count_query.where(Permission.name.like(f"%{name}%"))
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Permission.id)
    
    result = await session.execute(query)
    permissions = result.scalars().all()
    
    items = [
        PermissionResponse(
            id=p.id,
            code=p.code,
            name=p.name,
            description=p.description,
            created_at=p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        )
        for p in permissions
    ]
    
    return PermissionListResponse(total=total, items=items)


@router.post("/", response_model=PermissionResponse, status_code=201)
async def create_permission(
    permission_data: PermissionCreate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """创建权限"""
    from sqlalchemy import select
    
    result = await session.execute(select(Permission).where(Permission.code == permission_data.code))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="权限代码已存在")
    
    permission = Permission(
        code=permission_data.code,
        name=permission_data.name,
        description=permission_data.description
    )
    session.add(permission)
    await session.commit()
    await session.refresh(permission)
    
    return PermissionResponse(
        id=permission.id,
        code=permission.code,
        name=permission.name,
        description=permission.description,
        created_at=permission.created_at.strftime("%Y-%m-%d %H:%M:%S") if permission.created_at else ""
    )


@router.put("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """更新权限"""
    from sqlalchemy import select
    
    result = await session.execute(select(Permission).where(Permission.id == permission_id))
    permission = result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    if permission_data.name is not None:
        permission.name = permission_data.name
    if permission_data.description is not None:
        permission.description = permission_data.description
    
    await session.commit()
    await session.refresh(permission)
    
    return PermissionResponse(
        id=permission.id,
        code=permission.code,
        name=permission.name,
        description=permission.description,
        created_at=permission.created_at.strftime("%Y-%m-%d %H:%M:%S") if permission.created_at else ""
    )


@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: int,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """删除权限"""
    from sqlalchemy import select
    
    result = await session.execute(select(Permission).where(Permission.id == permission_id))
    permission = result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    await session.delete(permission)
    await session.commit()
    
    return {"message": "权限删除成功"}
