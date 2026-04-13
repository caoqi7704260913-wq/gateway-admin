# -*- coding: utf-8 -*-
"""
数据库初始化脚本
运行: python init_db.py
"""
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import create_db_and_tables, init_default_data, init_db

async def main():
    print("="*60)
    print("开始初始化 Admin 数据库")
    print("="*60)
    
    # 1. 初始化数据库连接池
    print("\n[1/3] 初始化数据库连接池...")
    await init_db()
    print("✅ 数据库连接池已初始化")
    
    # 2. 创建表结构
    print("\n[2/3] 创建数据库表...")
    await create_db_and_tables()
    print("✅ 数据库表已创建")
    
    # 3. 初始化默认数据
    print("\n[3/3] 初始化默认数据...")
    await init_default_data()
    print("✅ 默认数据已初始化")
    
    print("\n" + "="*60)
    print("数据库初始化完成!")
    print("="*60)
    print("\n默认管理员账号:")
    print("  用户名: admin")
    print("  密码: 123456")
    print("\n提示:")
    print("  - 启动服务后可以通过 /api/v1/auth/login 登录")
    print("  - 生产环境请修改默认密码")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
