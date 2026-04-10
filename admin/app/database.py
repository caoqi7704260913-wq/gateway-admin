"""
数据库初始化和迁移
"""
from app.database_pool import db_manager


def create_db_and_tables():
    """创建数据库表"""
    db_manager.create_tables()
    print("数据库表创建完成")


def init_default_data():
    """初始化默认数据"""
    from app.models.schemas import Admin, Role, Permission, Menu
    from app.services.password_service import password_service
    from sqlmodel import select
    
    with db_manager.get_session() as session:
        # 检查是否已有管理员
        admin = session.exec(select(Admin).where(Admin.username == "admin")).first()
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
        admin_role = session.exec(select(Role).where(Role.code == "admin")).first()
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
            perm = session.exec(select(Permission).where(Permission.code == code)).first()
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
            menu = session.get(Menu, menu_data["id"])
            if not menu:
                menu = Menu(**menu_data)
                session.add(menu)
        
        session.commit()
        print("默认数据初始化完成")


if __name__ == "__main__":
    create_db_and_tables()
    init_default_data()
