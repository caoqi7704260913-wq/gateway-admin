"""
测试内部服务直接请求 Admin（不经过 Gateway）

这个脚本模拟以下场景：
1. user-service 直接向 admin-service 发起请求
2. 使用 user-service 的 HMAC Key 签名
3. 携带 X-Service-Name Header 标识来源
4. Admin 验证服务注册状态和 HMAC 签名
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
import time
import hmac
import hashlib
from app.utils.redis_manager import get_redis_manager


async def test_internal_service_direct_request():
    """测试内部服务直接请求 Admin"""
    redis = get_redis_manager()
    
    print("=" * 80)
    print("测试内部服务直接请求 Admin（不经过 Gateway）")
    print("=" * 80)
    print()
    
    # ========================================
    # 步骤 1: 设置 HMAC Keys 并注册服务
    # ========================================
    print("[步骤 1] 设置 HMAC Keys 并注册 user-service...")
    
    # 为 user-service 设置一个测试密钥
    user_service_key = "test-user-service-key-12345"
    await redis.set('config:hmac:user-service', user_service_key)
    
    # 在 Redis 中注册 user-service
    service_key = 'service:user-service:test-instance'
    await redis.hset(service_key, 'id', 'test-instance')
    await redis.hset(service_key, 'name', 'user-service')
    await redis.hset(service_key, 'host', '127.0.0.1')
    await redis.hset(service_key, 'port', '8002')
    await redis.hset(service_key, 'ip', '127.0.0.1')
    
    # 获取 Admin 的密钥（用于对比）
    admin_key = await redis.get('config:hmac:admin-service')
    
    print(f"✅ User-Service Key: {user_service_key[:8]}...")
    print(f"✅ Admin Key: {admin_key[:8] if admin_key else 'None'}...")
    print(f"✅ User-Service 已注册到 Redis")
    print()
    
    async with httpx.AsyncClient() as client:
        # ========================================
        # 步骤 2: 内部服务直接请求 Admin
        # ========================================
        print("-" * 80)
        print("[步骤 2] user-service 直接请求 Admin (查询健康状态)")
        print("-" * 80)
        
        # 构建签名（使用 user-service 的密钥）
        ts = str(int(time.time()))
        nonce = os.urandom(16).hex()
        method = "GET"
        path = "/api/v1/health"  # Admin 的健康检查端点
        
        # 签名字符串格式：{method}:{path}:{timestamp}
        message = f"{method}:{path}:{ts}"
        signature = hmac.new(
            user_service_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        print(f"签名信息:")
        print(f"  Method: {method}")
        print(f"  Path: {path}")
        print(f"  Timestamp: {ts}")
        print(f"  Message: {message}")
        print(f"  Signature: {signature[:16]}...")
        print(f"  Key Used: user-service ({user_service_key[:8]}...)")
        print()
        
        try:
            # 直接请求 Admin，不经过 Gateway
            resp = await client.get(
                'http://localhost:8001/api/v1/health',  # 直接访问 Admin
                headers={
                    'X-Service-Name': 'user-service',  # 标识来源
                    'X-Signature': signature,
                    'X-Timestamp': ts,
                    'X-Nonce': nonce
                }
            )
            
            print(f"响应状态: {resp.status_code}")
            if resp.status_code == 200:
                print(f"✅ 请求成功！")
                print(f"   Response: {resp.json()}")
            else:
                print(f"❌ 请求失败")
                print(f"   Response: {resp.text}")
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # ========================================
        # 步骤 3: 测试错误的密钥（应该被拒绝）
        # ========================================
        print("-" * 80)
        print("[步骤 3] 测试使用错误的密钥（应该被拒绝）")
        print("-" * 80)
        
        wrong_key = "wrong-key-12345"
        ts2 = str(int(time.time()))
        message2 = f"GET:/api/v1/health:{ts2}"
        wrong_signature = hmac.new(
            wrong_key.encode(),
            message2.encode(),
            hashlib.sha256
        ).hexdigest()
        
        try:
            resp2 = await client.get(
                'http://localhost:8001/api/v1/health',
                headers={
                    'X-Service-Name': 'user-service',
                    'X-Signature': wrong_signature,
                    'X-Timestamp': ts2,
                    'X-Nonce': os.urandom(16).hex()
                }
            )
            
            print(f"响应状态: {resp2.status_code}")
            if resp2.status_code == 403:
                print(f"✅ 正确拒绝！使用了错误的密钥")
                print(f"   Response: {resp2.json()}")
            else:
                print(f"⚠️  意外响应: {resp2.status_code}")
                print(f"   Response: {resp2.text}")
                
        except Exception as e:
            print(f"❌ 请求异常: {e}")
        
        print()
        
        # ========================================
        # 清理
        # ========================================
        print("-" * 80)
        print("[清理] 删除测试数据")
        print("-" * 80)
        await redis.delete('config:hmac:user-service')
        await redis.delete('service:user-service:test-instance')
        print("✅ 测试密钥和服务注册已删除")
        print()
        
        print("=" * 80)
        print("测试完成")
        print("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_internal_service_direct_request())
