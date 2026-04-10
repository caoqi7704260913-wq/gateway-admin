# -*- coding: utf-8 -*-
import os
import sys

# 清除可能的环境变量
os.environ.pop('DEBUG', None)

# 设置项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接创建 settings 测试
from pydantic_settings import BaseSettings, SettingsConfigDict

class TestSettings(BaseSettings):
    APP_NAME: str = "test"
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

try:
    settings = TestSettings()
    print(f"DEBUG value: {settings.DEBUG} (type: {type(settings.DEBUG)})")
except Exception as e:
    print(f"Error: {e}")
    
    # 检查实际读取的值
    import dotenv
    dotenv.load_dotenv(".env")
    print(f"DEBUG from env: {os.getenv('DEBUG')}")
