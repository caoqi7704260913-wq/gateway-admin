"""
pytest 配置文件
"""

import os
import pytest

# 修复环境变量 - 覆盖 DEBUG 设置
os.environ['DEBUG'] = 'True'

# 导入配置前设置环境变量
from config import settings
