"""
数据库初始化和迁移
"""
import asyncio
from app.utils.database_pool import db_manager


async def init_db():
    """初始化数据库连接池"""
    await db_manager.init()


async def create_db_and_tables():
    """创建数据库表（异步）"""
    # 必须先导入所有模型，这样 SQLModel.metadata 才会包含表定义
    from app.models.schemas import Admin, Role, Permission, Menu, AdminRole, RolePermission, Token
    
    await db_manager.create_tables_async()
    print("数据库表创建完成")


async def init_default_data():
    """初始化默认数据（异步）"""
    from app.models.schemas import Admin, Role, Permission, Menu
    from app.services.password_service import password_service
    from sqlalchemy import select
    
    async with db_manager.AsyncSessionLocal() as session:
        # 检查是否已有管理员
        result = await session.execute(select(Admin).where(Admin.username == "admin"))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = Admin(
                username="admin",
                password_hash=password_service.hash("123456"),
                nickname="管理员",
                email="admin@example.com",
                status=1
            )
            session.add(admin)
        
        # 检查是否已有角色
        result = await session.execute(select(Role).where(Role.code == "admin"))
        admin_role = result.scalar_one_or_none()
        if not admin_role:
            admin_role = Role(
                code="admin",
                name="超级管理员",
                description="拥有所有权限",
                status=1
            )
            session.add(admin_role)
        
        # 创建默认权限
        default_permissions = [
            ("user:view", "用户查看"),
            ("user:edit", "用户编辑"),
            ("role:view", "角色查看"),
            ("role:edit", "角色编辑"),
            ("config:cors", "CORS配置"),
            ("config:hmac", "HMAC配置"),
            ("menu:view", "菜单查看"),
            ("menu:edit", "菜单编辑"),
        ]
        
        for code, name in default_permissions:
            result = await session.execute(select(Permission).where(Permission.code == code))
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(code=code, name=name)
                session.add(perm)
        
        # 创建默认菜单
        default_menus = [
            {"id": 1, "name": "系统管理", "path": "/system", "icon": "Setting", "sort": 100},
            {"id": 2, "name": "用户管理", "path": "/system/users", "icon": "User", "sort": 101, "parent_id": 1},
            {"id": 3, "name": "角色管理", "path": "/system/roles", "icon": "Key", "sort": 102, "parent_id": 1},
            {"id": 4, "name": "菜单管理", "path": "/system/menus", "icon": "Menu", "sort": 103, "parent_id": 1},
            {"id": 5, "name": "配置中心", "path": "/config", "icon": "Tools", "sort": 200},
            {"id": 6, "name": "CORS配置", "path": "/config/cors", "icon": "Document", "sort": 201, "parent_id": 5},
            {"id": 7, "name": "HMAC配置", "path": "/config/hmac", "icon": "Lock", "sort": 202, "parent_id": 5},
        ]
        
        for menu_data in default_menus:
            menu = await session.get(Menu, menu_data["id"])
            if not menu:
                menu = Menu(**menu_data)
                session.add(menu)
        
        await session.commit()
        print("默认数据初始化完成")


if __name__ == "__main__":
    asyncio.run(init_db())
    create_db_and_tables()
    asyncio.run(init_default_data())
