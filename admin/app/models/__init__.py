"""
数据模型包
"""
from app.models.schemas import Admin, Permission, Role, AdminRole, RolePermission, Menu, Token

__all__ = ["Admin", "Permission", "Role", "AdminRole", "RolePermission", "Menu", "Token"]
