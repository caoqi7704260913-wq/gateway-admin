"""验证 Redis 数据"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')
import asyncio
import json

from app.utils.redis_manager import get_redis_manager

async def verify_redis():
    redis_mgr = get_redis_manager()
    
    # 注册测试服务
    service_key = "service:user-service:user-service-001"
    service_data = {
        "id": "user-service-001",
        "name": "user-service",
        "host": "127.0.0.1",
        "ip": "127.0.0.1",
        "port": 8001,
        "url": "http://127.0.0.1:8001",
        "weight": 10,
        "status": "healthy"
    }
    
    await redis_mgr.set(service_key, json.dumps(service_data), ex=60)
    print(f"[Redis] Write: {service_key}")
    
    # 读取验证
    value = await redis_mgr.get(service_key)
    print(f"[Redis] Read: {value}")
    
    # 列出所有 service: 开头的 key
    keys = await redis_mgr.keys("service:*")
    print(f"[Redis] All service keys: {keys}")
    
    # 删除
    await redis_mgr.delete(service_key)
    print("[Redis] Deleted")

if __name__ == "__main__":
    asyncio.run(verify_redis())
