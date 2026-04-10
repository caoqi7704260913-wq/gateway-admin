# -*- coding: utf-8 -*-
"""
数据库初始化脚本
运行: python init_db.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import create_db_and_tables, init_default_data

if __name__ == "__main__":
    print("开始创建数据库表...")
    create_db_and_tables()
    print("\n开始初始化默认数据...")
    init_default_data()
    print("\n数据库初始化完成!")
    print("默认管理员: admin / 123456")
