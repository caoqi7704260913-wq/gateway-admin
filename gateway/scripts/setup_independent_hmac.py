"""为每个服务生成独立的 HMAC 密钥"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import secrets
from app.utils.redis_manager import get_redis_manager
from app.utils.consul_manager import get_consul_manager

async def setup_independent_hmac_keys():
    """为每个服务生成独立的 HMAC 密钥"""
    redis = get_redis_manager()
    consul = get_consul_manager()
    
    services = {
        "gateway": "Gateway 服务（前端使用）",
        "admin-service": "Admin 管理服务",
        "user-service": "User 用户服务",
    }
    
    print("=" * 70)
    print("为每个服务生成独立的 HMAC 密钥")
    print("=" * 70)
    
    keys = {}
    for service_name, description in services.items():
        # 生成独立密钥
        key = secrets.token_urlsafe(32)
        keys[service_name] = key
        
        # 存储到 Redis
        await redis.set(f"config:hmac:{service_name}", key)
        
        # 存储到 Consul
        if consul.is_healthy():
            consul_path = f"config/hmac/{service_name}"
            consul.client.kv.put(consul_path, key)
        
        print(f"\n{description}")
        print(f"  Service: {service_name}")
        print(f"  Key: {key}")
    
    print("\n" + "=" * 70)
    print("Frontend Configuration (use gateway key only):")
    print("=" * 70)
    print(f"HMAC_KEY={keys['gateway']}")
    print("\n" + "=" * 70)
    print("✅ 所有密钥已生成并存储到 Redis + Consul")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(setup_independent_hmac_keys())
