"""
数据库模型
"""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Admin(SQLModel, table=True):
    """管理员表"""
    __tablename__ = "admins"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    nickname: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    status: int = Field(default=1)  # 1: 正常, 0: 禁用
    last_login_time: Optional[datetime] = None
    last_login_ip: Optional[str] = Field(default=None, max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 关联
    admin_roles: List["AdminRole"] = Relationship(back_populates="admin")


class Permission(SQLModel, table=True):
    """权限表"""
    __tablename__ = "permissions"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=100, unique=True, index=True)
    name: str = Field(max_length=100)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关联
    role_permissions: List["RolePermission"] = Relationship(back_populates="permission")


class Role(SQLModel, table=True):
    """角色表"""
    __tablename__ = "roles"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=50)
    description: Optional[str] = None
    status: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 关联
    admin_roles: List["AdminRole"] = Relationship(back_populates="role")
    role_permissions: List["RolePermission"] = Relationship(back_populates="role")


class AdminRole(SQLModel, table=True):
    """管理员角色关联表"""
    __tablename__ = "admin_roles"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    admin_id: int = Field(foreign_key="admins.id", index=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关联
    admin: Optional["Admin"] = Relationship(back_populates="admin_roles")
    role: Optional["Role"] = Relationship(back_populates="admin_roles")


class RolePermission(SQLModel, table=True):
    """角色权限关联表"""
    __tablename__ = "role_permissions"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(foreign_key="roles.id", index=True)
    permission_id: int = Field(foreign_key="permissions.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关联
    role: Optional["Role"] = Relationship(back_populates="role_permissions")
    permission: Optional["Permission"] = Relationship(back_populates="role_permissions")


class Menu(SQLModel, table=True):
    """菜单表"""
    __tablename__ = "menus"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_id: Optional[int] = Field(default=0, index=True)
    name: str = Field(max_length=50)
    path: str = Field(max_length=255)
    component: Optional[str] = Field(default=None, max_length=255)
    icon: Optional[str] = Field(default=None, max_length=50)
    sort: int = Field(default=0)
    status: int = Field(default=1)
    permission_code: Optional[str] = Field(default=None, max_length=100)
    menu_type: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Token(SQLModel, table=True):
    """Token表"""
    __tablename__ = "tokens"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(max_length=64, unique=True, index=True)
    admin_id: int = Field(foreign_key="admins.id", index=True)
    device: Optional[str] = Field(default=None, max_length=50)
    ip: Optional[str] = Field(default=None, max_length=50)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
