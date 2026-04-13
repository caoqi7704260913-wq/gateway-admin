"""
配置管理包

提供应用配置管理，支持环境变量和 .env 文件
"""
from config.settings import settings, BASE_DIR

__all__ = ["settings", "BASE_DIR"]
