"""
直接测试脚本 - 绕过 API 直接操作 Redis
"""
import asyncio
import json
from app.utils.redis_manager import get_redis_manager
from app.models.service import ServiceBase

async def main():
    print("=" * 60)
    print("直接测试：注册服务到 Redis")
    print("=" * 60)

    redis = get_redis_manager()
    client = await redis.get_client()

    # 创建测试服务
    service = ServiceBase(
        name="user",
        host="127.0.0.1",
        ip="127.0.0.1",
        port=8081,
        url="http://127.0.0.1:8081",
        weight=1,
        metadata={},
        status="healthy"
    )

    print(f"\n服务信息: {service.model_dump()}")

    # 直接写入 Redis
    key = f"service:user:{service.id}"
    value = json.dumps(service.model_dump())
    await client.set(key, value, ex=30)

    print(f"已写入 Redis: {key}")

    # 读取验证
    result = await client.get(key)
    print(f"读取结果: {result}")

    # 获取所有 user 服务
    keys = await redis.keys("service:user:*")
    print(f"\n所有 user 服务 keys: {keys}")

    for k in keys:
        v = await redis.get(k)
        print(f"  {k}: {v}")

    print("\n" + "=" * 60)
    print("测试完成!")

asyncio.run(main())
