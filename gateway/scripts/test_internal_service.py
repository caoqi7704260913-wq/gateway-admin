"""
测试内部服务注册和请求流程

这个脚本模拟以下完整流程：
1. 内部服务（user-service）注册到 Gateway
2. Gateway 将服务信息同步到 Redis 和 Consul
3. 内部服务通过 Gateway 向 Admin 发起请求
4. 验证 HMAC 签名使用正确的密钥
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import httpx
import time
import hmac
import hashlib
from app.utils.redis_manager import get_redis_manager
from app.utils.consul_manager import get_consul_manager


async def test_internal_service_flow():
    """测试内部服务完整流程"""
    redis = get_redis_manager()
    consul = get_consul_manager()
    
    print("=" * 80)
    print("测试内部服务注册和请求流程")
    print("=" * 80)
    print()
    
    # ========================================
    # 步骤 1: 获取 HMAC Keys
    # ========================================
    print("[步骤 1] 获取 HMAC Keys...")
    gateway_key = await redis.get('config:hmac:gateway')
    admin_key = await redis.get('config:hmac:admin-service')
    
    if not gateway_key or not admin_key:
        print("❌ 无法获取 HMAC Keys")
        return
    
    print(f"✅ Gateway Key: {gateway_key[:8]}...")
    print(f"✅ Admin Key: {admin_key[:8]}...")
    print()
    
    async with httpx.AsyncClient() as client:
        # ========================================
        # 步骤 2: 模拟内部服务注册到 Gateway
        # ========================================
        print("-" * 80)
        print("[步骤 2] 模拟内部服务 (user-service) 注册到 Gateway")
        print("-" * 80)
        
        register_data = {
            "id": "user-service-001",
            "name": "user-service",
            "host": "localhost",
            "port": 8002,
            "weight": 1
        }
        
        # 生成注册请求的 HMAC 签名（使用 Gateway Key）
        ts_register = str(int(time.time()))
        nonce_register = os.urandom(16).hex()
        body_register = '{"id":"user-service-001","name":"user-service","host":"localhost","port":8002,"weight":1}'
        msg_register = f'{ts_register}{nonce_register}{body_register}'
        sig_register = hmac.new(gateway_key.encode(), msg_register.encode(), hashlib.sha256).hexdigest()
        
        try:
            resp_register = await client.post(
                'http://localhost:9000/api/services/register',
                content=body_register,
                headers={
                    'Content-Type': 'application/json',
                    'X-Signature': sig_register,
                    'X-Timestamp': ts_register,
                    'X-Nonce': nonce_register
                }
            )
            
            if resp_register.status_code == 200:
                print(f"✅ 服务注册成功")
                print(f"   Response: {resp_register.json()}")
            else:
                print(f"❌ 服务注册失败: {resp_register.status_code}")
                print(f"   Response: {resp_register.text}")
                return
        except Exception as e:
            print(f"❌ 注册请求异常: {e}")
            return
        
        print()
        
        # ========================================
        # 步骤 3: 验证服务已注册到 Redis 和 Consul
        # ========================================
        print("-" * 80)
        print("[步骤 3] 验证服务注册状态")
        print("-" * 80)
        
        # 检查 Redis
        redis_services = await redis.hgetall('services:user-service')
        if redis_services:
            print(f"✅ Redis 中已注册: user-service")
            print(f"   Service ID: {redis_services.get(b'id', b'N/A').decode()}")
            print(f"   Host: {redis_services.get(b'host', b'N/A').decode()}")
            print(f"   Port: {redis_services.get(b'port', b'N/A').decode()}")
        else:
            print(f"❌ Redis 中未找到: user-service")
        
        # 检查 Consul
        consul_services = consul.get_services()
        if 'user-service' in consul_services:
            print(f"✅ Consul 中已注册: user-service")
            svc = consul_services['user-service']
            print(f"   Service ID: {svc.get('ID', 'N/A')}")
            print(f"   Address: {svc.get('Address', 'N/A')}")
            print(f"   Port: {svc.get('Port', 'N/A')}")
        else:
            print(f"❌ Consul 中未找到: user-service")
        
        print()
        
        # ========================================
        # 步骤 4: 登录 Admin 获取 Token
        # ========================================
        print("-" * 80)
        print("[步骤 4] 登录 Admin 获取 Token")
        print("-" * 80)
        
        ts_login = str(int(time.time()))
        nonce_login = os.urandom(16).hex()
        body_login = '{"username":"admin","password":"123456"}'
        msg_login = f'{ts_login}{nonce_login}{body_login}'
        sig_login = hmac.new(gateway_key.encode(), msg_login.encode(), hashlib.sha256).hexdigest()
        
        try:
            resp_login = await client.post(
                'http://localhost:9000/api/auth/login',
                json={'username': 'admin', 'password': '123456'},
                headers={
                    'X-Signature': sig_login,
                    'X-Timestamp': ts_login,
                    'X-Nonce': nonce_login
                }
            )
            
            if resp_login.status_code != 200:
                print(f"❌ 登录失败: {resp_login.status_code}")
                print(f"   Response: {resp_login.text}")
                return
            
            token = resp_login.json()['token']
            print(f"✅ 登录成功")
            print(f"   Token: {token[:32]}...")
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return
        
        print()
        
        # ========================================
        # 步骤 5: 内部服务通过 Gateway 请求 Admin
        # ========================================
        print("-" * 80)
        print("[步骤 5] 内部服务通过 Gateway 请求 Admin (查询 CORS 配置)")
        print("-" * 80)
        
        ts_request = str(int(time.time()))
        nonce_request = os.urandom(16).hex()
        body_request = ''  # GET 请求没有 body
        msg_request = f'{ts_request}{nonce_request}{body_request}'
        sig_request = hmac.new(gateway_key.encode(), msg_request.encode(), hashlib.sha256).hexdigest()
        
        try:
            resp_request = await client.get(
                'http://localhost:9000/api/config/cors',
                headers={
                    'Authorization': f'Bearer {token}',
                    'X-Signature': sig_request,
                    'X-Timestamp': ts_request,
                    'X-Nonce': nonce_request,
                    'X-Service-Name': 'user-service'  # 标识请求来源
                }
            )
            
            print(f"Status: {resp_request.status_code}")
            if resp_request.status_code == 200:
                print(f"✅ 请求成功")
                print(f"   Response: {resp_request.json()}")
            else:
                print(f"❌ 请求失败: {resp_request.text}")
        except Exception as e:
            print(f"❌ 请求异常: {e}")
        
        print()
        
        # ========================================
        # 步骤 6: 清理 - 注销服务
        # ========================================
        print("-" * 80)
        print("[步骤 6] 清理 - 注销 user-service")
        print("-" * 80)
        
        deregister_data = {
            "id": "user-service-001"
        }
        
        ts_dereg = str(int(time.time()))
        nonce_dereg = os.urandom(16).hex()
        body_dereg = '{"id":"user-service-001"}'
        msg_dereg = f'{ts_dereg}{nonce_dereg}{body_dereg}'
        sig_dereg = hmac.new(gateway_key.encode(), msg_dereg.encode(), hashlib.sha256).hexdigest()
        
        try:
            resp_dereg = await client.post(
                'http://localhost:9000/api/services/deregister',
                content=body_dereg,
                headers={
                    'Content-Type': 'application/json',
                    'X-Signature': sig_dereg,
                    'X-Timestamp': ts_dereg,
                    'X-Nonce': nonce_dereg
                }
            )
            
            if resp_dereg.status_code == 200:
                print(f"✅ 服务注销成功")
                print(f"   Response: {resp_dereg.json()}")
            else:
                print(f"⚠️  服务注销失败: {resp_dereg.status_code}")
        except Exception as e:
            print(f"⚠️  注销异常: {e}")
        
        print()
        print("=" * 80)
        print("测试完成")
        print("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_internal_service_flow())
