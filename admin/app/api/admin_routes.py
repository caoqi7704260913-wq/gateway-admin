"""
管理员管理 API 路由
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.utils.database_pool import get_db_async
from app.api.routes import verify_token

router = APIRouter(prefix="/admins", tags=["管理员管理"])


# ============ Pydantic 模型 ============

class AdminCreate(BaseModel):
    """创建管理员请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[str] = Field(None, description="邮箱")
    role_id: Optional[int] = Field(None, description="角色ID")


class AdminUpdate(BaseModel):
    """更新管理员请求"""
    nickname: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = None
    role_id: Optional[int] = None
    status: Optional[int] = Field(None, ge=0, le=1, description="状态：0-禁用，1-启用")


class AdminResponse(BaseModel):
    """管理员响应"""
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[int] = None
    status: int
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AdminListResponse(BaseModel):
    """管理员列表响应"""
    total: int
    items: List[AdminResponse]


# ============ API 端点 ============

@router.get("/", response_model=AdminListResponse)
async def list_admins(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    username: Optional[str] = Query(None, description="用户名搜索"),
    status: Optional[int] = Query(None, ge=0, le=1, description="状态筛选"),
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """获取管理员列表（支持分页和搜索）"""
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from app.models.schemas import Admin
    
    # 构建查询，预加载角色关联
    query = select(Admin).options(selectinload(Admin.admin_roles))
    count_query = select(func.count(Admin.id))
    
    # 添加筛选条件
    if username:
        query = query.where(Admin.username.like(f"%{username}%"))
        count_query = count_query.where(Admin.username.like(f"%{username}%"))
    
    if status is not None:
        query = query.where(Admin.status == status)
        count_query = count_query.where(Admin.status == status)
    
    # 获取总数
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Admin.id.desc())
    
    result = await session.execute(query)
    admins = result.scalars().all()
    
    # 转换为响应模型
    items = []
    for admin in admins:
        # 获取角色 ID（取第一个角色）
        role_id = None
        if admin.admin_roles:
            role_id = admin.admin_roles[0].role_id
        
        items.append(
            AdminResponse(
                id=admin.id,
                username=admin.username,
                nickname=admin.nickname,
                email=admin.email,
                role_id=role_id,
                status=admin.status,
                created_at=admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if admin.created_at else "",
                updated_at=admin.updated_at.strftime("%Y-%m-%d %H:%M:%S") if admin.updated_at else None
            )
        )
    
    return AdminListResponse(total=total, items=items)


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """获取管理员详情"""
    from sqlalchemy import select
    from app.models.schemas import Admin
    
    result = await session.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        nickname=admin.nickname,
        email=admin.email,
        role_id=admin.role_id,
        status=admin.status,
        created_at=admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if admin.created_at else "",
        updated_at=admin.updated_at.strftime("%Y-%m-%d %H:%M:%S") if admin.updated_at else None
    )


@router.post("/", response_model=AdminResponse, status_code=201)
async def create_admin(
    admin_data: AdminCreate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """创建管理员"""
    from sqlalchemy import select
    from app.models.schemas import Admin
    from app.services.password_service import password_service
    from datetime import datetime
    
    # 检查用户名是否已存在
    result = await session.execute(
        select(Admin).where(Admin.username == admin_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 加密密码
    hashed_password = password_service.hash_password(admin_data.password)
    
    # 创建管理员
    new_admin = Admin(
        username=admin_data.username,
        password=hashed_password,
        nickname=admin_data.nickname,
        email=admin_data.email,
        role_id=admin_data.role_id,
        status=1,  # 默认启用
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    session.add(new_admin)
    await session.commit()
    await session.refresh(new_admin)
    
    return AdminResponse(
        id=new_admin.id,
        username=new_admin.username,
        nickname=new_admin.nickname,
        email=new_admin.email,
        role_id=new_admin.role_id,
        status=new_admin.status,
        created_at=new_admin.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        updated_at=new_admin.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    )


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    admin_data: AdminUpdate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """更新管理员"""
    from sqlalchemy import select, delete
    from sqlalchemy.orm import selectinload
    from app.models.schemas import Admin, AdminRole
    from datetime import datetime
    
    result = await session.execute(
        select(Admin).options(selectinload(Admin.admin_roles)).where(Admin.id == admin_id)
    )
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    
    # 更新字段
    if admin_data.nickname is not None:
        admin.nickname = admin_data.nickname
    if admin_data.email is not None:
        admin.email = admin_data.email
    if admin_data.status is not None:
        admin.status = admin_data.status
    
    # 更新角色关联
    if admin_data.role_id is not None:
        # 删除旧的角色关联
        await session.execute(
            delete(AdminRole).where(AdminRole.admin_id == admin_id)
        )
        # 添加新的角色关联
        new_admin_role = AdminRole(admin_id=admin_id, role_id=admin_data.role_id)
        session.add(new_admin_role)
    
    admin.updated_at = datetime.now()
    
    await session.commit()
    await session.refresh(admin)
    
    # 获取角色 ID
    role_id = None
    if admin.admin_roles:
        role_id = admin.admin_roles[0].role_id
    
    return AdminResponse(
        id=admin.id,
        username=admin.username,
        nickname=admin.nickname,
        email=admin.email,
        role_id=role_id,
        status=admin.status,
        created_at=admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if admin.created_at else "",
        updated_at=admin.updated_at.strftime("%Y-%m-%d %H:%M:%S") if admin.updated_at else None
    )


@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """删除管理员"""
    from sqlalchemy import select
    from app.models.schemas import Admin
    
    result = await session.execute(select(Admin).where(Admin.id == admin_id))
    admin = result.scalar_one_or_none()
    
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    
    # 不允许删除自己
    # TODO: 从 token 中获取当前用户ID进行比较
    
    await session.delete(admin)
    await session.commit()
    
    return {"message": "管理员已删除"}
