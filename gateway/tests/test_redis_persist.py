"""测试 Redis 服务数据持久化"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')
import asyncio
import json

from app.services.discovery import get_service_discovery
from app.utils.redis_manager import get_redis_manager

async def test_redis_persist():
    print("=== Test Redis Service Data Persistence ===\n")
    
    discovery = get_service_discovery()
    redis_mgr = get_redis_manager()
    
    # 创建测试服务
    from app.models.service import ServiceBase
    test_service = ServiceBase(
        id="test-service-001",
        name="test-service",
        host="192.168.1.100",
        ip="192.168.1.100",
        port=8080,
        url="http://192.168.1.100:8080",
        weight=5,
        status="healthy"
    )
    
    # 注册
    print("[1] Register service...")
    await discovery.register_service(test_service)
    
    # 检查 Redis
    print("\n[2] Check Redis data...")
    keys = await redis_mgr.keys("service:*")
    print(f"Keys in Redis: {keys}")
    
    # 读取详细数据
    redis_key = f"service:{test_service.name}:{test_service.id}"
    value = await redis_mgr.get(redis_key)
    print(f"\nRedis key: {redis_key}")
    print(f"Redis value: {value}")
    
    # 解析 JSON
    if value:
        data = json.loads(value)
        print(f"\nParsed data:")
        print(f"  - id: {data.get('id')}")
        print(f"  - name: {data.get('name')}")
        print(f"  - host: {data.get('host')}")
        print(f"  - port: {data.get('port')}")
        print(f"  - weight: {data.get('weight')}")
        print(f"  - status: {data.get('status')}")
    
    # 清理
    print("\n[3] Cleanup...")
    await redis_mgr.delete(redis_key)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test_redis_persist())
