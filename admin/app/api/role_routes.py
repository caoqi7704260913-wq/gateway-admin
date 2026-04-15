"""
角色管理 API
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database_pool import get_db_async
from app.api.routes import verify_token
from app.models.schemas import Role, RolePermission
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter(prefix="/roles", tags=["角色管理"])


class RoleCreate(BaseModel):
    """创建角色请求"""
    code: str = Field(..., max_length=50, description="角色代码")
    name: str = Field(..., max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="描述")
    status: int = Field(default=1, ge=0, le=1, description="状态：1启用 0禁用")
    permission_ids: Optional[List[int]] = Field(default=[], description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色请求"""
    name: Optional[str] = Field(None, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    code: str
    name: str
    description: Optional[str] = None
    status: int
    created_at: str
    updated_at: Optional[str] = None
    permission_ids: List[int] = []

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """角色列表响应"""
    total: int
    items: List[RoleResponse]


@router.get("/", response_model=RoleListResponse)
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    name: Optional[str] = Query(None, description="角色名称搜索"),
    status: Optional[int] = Query(None, ge=0, le=1, description="状态筛选"),
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """获取角色列表（支持分页和搜索）"""
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    
    # 构建查询，预加载权限关联
    query = select(Role).options(selectinload(Role.role_permissions))
    count_query = select(func.count(Role.id))
    
    # 添加筛选条件
    if name:
        query = query.where(Role.name.like(f"%{name}%"))
        count_query = count_query.where(Role.name.like(f"%{name}%"))
    
    if status is not None:
        query = query.where(Role.status == status)
        count_query = count_query.where(Role.status == status)
    
    # 获取总数
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Role.id.desc())
    
    result = await session.execute(query)
    roles = result.scalars().all()
    
    # 转换为响应模型
    items = []
    for role in roles:
        # 获取权限 ID 列表
        permission_ids = [rp.permission_id for rp in role.role_permissions]
        
        items.append(
            RoleResponse(
                id=role.id,
                code=role.code,
                name=role.name,
                description=role.description,
                status=role.status,
                created_at=role.created_at.strftime("%Y-%m-%d %H:%M:%S") if role.created_at else "",
                updated_at=role.updated_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(role, 'updated_at') and role.updated_at else None,
                permission_ids=permission_ids
            )
        )
    
    return RoleListResponse(total=total, items=items)


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(
    role_data: RoleCreate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """创建角色"""
    from sqlalchemy import select
    
    # 检查角色代码是否已存在
    result = await session.execute(select(Role).where(Role.code == role_data.code))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="角色代码已存在")
    
    # 创建角色
    role = Role(
        code=role_data.code,
        name=role_data.name,
        description=role_data.description,
        status=role_data.status
    )
    session.add(role)
    await session.flush()
    
    # 关联权限
    if role_data.permission_ids:
        for permission_id in role_data.permission_ids:
            role_permission = RolePermission(role_id=role.id, permission_id=permission_id)
            session.add(role_permission)
    
    await session.commit()
    await session.refresh(role)
    
    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        status=role.status,
        created_at=role.created_at.strftime("%Y-%m-%d %H:%M:%S") if role.created_at else "",
        updated_at=None,
        permission_ids=role_data.permission_ids or []
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """更新角色"""
    from sqlalchemy import select, delete
    from sqlalchemy.orm import selectinload
    
    result = await session.execute(
        select(Role).options(selectinload(Role.role_permissions)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 更新字段
    if role_data.name is not None:
        role.name = role_data.name
    if role_data.description is not None:
        role.description = role_data.description
    if role_data.status is not None:
        role.status = role_data.status
    
    # 更新权限关联
    if role_data.permission_ids is not None:
        # 删除旧的权限关联
        await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        # 添加新的权限关联
        for permission_id in role_data.permission_ids:
            role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
            session.add(role_permission)
    
    if hasattr(role, 'updated_at'):
        role.updated_at = datetime.now()
    
    await session.commit()
    await session.refresh(role)
    
    # 获取权限 ID 列表
    permission_ids = [rp.permission_id for rp in role.role_permissions]
    
    return RoleResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        status=role.status,
        created_at=role.created_at.strftime("%Y-%m-%d %H:%M:%S") if role.created_at else "",
        updated_at=role.updated_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(role, 'updated_at') and role.updated_at else None,
        permission_ids=permission_ids
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """删除角色"""
    from sqlalchemy import select, delete
    
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 删除角色关联的权限
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    
    # 删除角色
    await session.delete(role)
    await session.commit()
    
    return {"message": "角色删除成功"}
