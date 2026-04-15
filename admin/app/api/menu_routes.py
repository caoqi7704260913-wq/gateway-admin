"""
菜单管理 API
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database_pool import get_db_async
from app.api.routes import verify_token
from app.models.schemas import Menu
from pydantic import BaseModel, Field

router = APIRouter(prefix="/menus", tags=["菜单管理"])


class MenuCreate(BaseModel):
    """创建菜单请求"""
    name: str = Field(..., max_length=50, description="菜单名称")
    path: str = Field(..., max_length=200, description="路由路径")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    component: Optional[str] = Field(None, max_length=200, description="组件路径")
    sort: int = Field(default=0, description="排序")
    status: int = Field(default=1, ge=0, le=1, description="状态：1显示 0隐藏")


class MenuUpdate(BaseModel):
    """更新菜单请求"""
    name: Optional[str] = Field(None, max_length=50, description="菜单名称")
    path: Optional[str] = Field(None, max_length=200, description="路由路径")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    component: Optional[str] = Field(None, max_length=200, description="组件路径")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")


class MenuResponse(BaseModel):
    """菜单响应"""
    id: int
    name: str
    path: str
    icon: Optional[str] = None
    component: Optional[str] = None
    sort: int
    status: int
    created_at: str

    class Config:
        from_attributes = True


class MenuListResponse(BaseModel):
    """菜单列表响应"""
    total: int
    items: List[MenuResponse]


@router.get("/", response_model=MenuListResponse)
async def list_menus(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    name: Optional[str] = Query(None, description="菜单名称搜索"),
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """获取菜单列表"""
    from sqlalchemy import select, func
    
    query = select(Menu)
    count_query = select(func.count(Menu.id))
    
    if name:
        query = query.where(Menu.name.like(f"%{name}%"))
        count_query = count_query.where(Menu.name.like(f"%{name}%"))
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Menu.sort, Menu.id)
    
    result = await session.execute(query)
    menus = result.scalars().all()
    
    items = [
        MenuResponse(
            id=m.id,
            name=m.name,
            path=m.path,
            icon=m.icon,
            component=m.component,
            sort=m.sort,
            status=m.status,
            created_at=m.created_at.strftime("%Y-%m-%d %H:%M:%S") if m.created_at else ""
        )
        for m in menus
    ]
    
    return MenuListResponse(total=total, items=items)


@router.post("/", response_model=MenuResponse, status_code=201)
async def create_menu(
    menu_data: MenuCreate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """创建菜单"""
    menu = Menu(**menu_data.dict())
    session.add(menu)
    await session.commit()
    await session.refresh(menu)
    
    return MenuResponse(
        id=menu.id,
        name=menu.name,
        path=menu.path,
        icon=menu.icon,
        component=menu.component,
        sort=menu.sort,
        status=menu.status,
        created_at=menu.created_at.strftime("%Y-%m-%d %H:%M:%S") if menu.created_at else ""
    )


@router.put("/{menu_id}", response_model=MenuResponse)
async def update_menu(
    menu_id: int,
    menu_data: MenuUpdate,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """更新菜单"""
    from sqlalchemy import select
    
    result = await session.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    
    for field, value in menu_data.dict(exclude_unset=True).items():
        setattr(menu, field, value)
    
    await session.commit()
    await session.refresh(menu)
    
    return MenuResponse(
        id=menu.id,
        name=menu.name,
        path=menu.path,
        icon=menu.icon,
        component=menu.component,
        sort=menu.sort,
        status=menu.status,
        created_at=menu.created_at.strftime("%Y-%m-%d %H:%M:%S") if menu.created_at else ""
    )


@router.delete("/{menu_id}")
async def delete_menu(
    menu_id: int,
    _: dict = Depends(verify_token),
    session: AsyncSession = Depends(get_db_async)
):
    """删除菜单"""
    from sqlalchemy import select
    
    result = await session.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalar_one_or_none()
    
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    
    await session.delete(menu)
    await session.commit()
    
    return {"message": "菜单删除成功"}
