"""清理所有 HMAC 密钥（Redis + Consul）"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.utils.redis_manager import get_redis_manager
from app.utils.consul_manager import get_consul_manager

async def cleanup_all_hmac_keys():
    """清理所有 HMAC 密钥"""
    redis = get_redis_manager()
    consul = get_consul_manager()
    
    services = ["gateway", "admin-service", "user-service"]
    
    print("开始清理所有 HMAC 密钥...\n")
    
    # 1. 清理 Redis 中的密钥
    print("1. 清理 Redis 中的密钥:")
    for service_name in services:
        key = f"config:hmac:{service_name}"
        try:
            await redis.delete(key)
            print(f"   ✅ 已删除: {key}")
        except Exception as e:
            print(f"   ❌ 删除失败 {key}: {e}")
    
    # 2. 清理 Consul 中的密钥
    print("\n2. 清理 Consul 中的密钥:")
    if consul.is_healthy():
        for service_name in services:
            consul_path = f"config/hmac/{service_name}"
            try:
                # 直接使用 consul 客户端删除
                consul.client.kv.delete(consul_path)
                print(f"   ✅ 已删除: {consul_path}")
            except Exception as e:
                print(f"   ⚠️  删除失败 {consul_path}: {e}")
    else:
        print("   ⚠️  Consul 不可用，跳过")
    
    print("\n✅ 清理完成！")
    print("\n提示：")
    print("- Admin Service 重启后会自动生成新的 HMAC Key")
    print("- User Service 需要手动配置或等待自动生成")
    print("- Gateway 可以运行 setup_independent_hmac.py 重新生成密钥")

if __name__ == "__main__":
    asyncio.run(cleanup_all_hmac_keys())

