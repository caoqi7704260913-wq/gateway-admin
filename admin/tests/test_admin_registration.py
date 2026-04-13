"""
Admin 服务注册流程测试

测试完整的注册流程：
1. 从 Redis 获取 HMAC Key
2. 从 Redis 获取 CORS 配置
3. 生成 HMAC 签名
4. 注册到 Gateway
5. 心跳保活
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.config_service import config_service
from app.utils.redis_manager import redis_manager


async def test_redis_connection():
    """测试 Redis 连接"""
    print("\n" + "="*60)
    print("测试 1: Redis 连接")
    print("="*60)
    
    try:
        await redis_manager.init()
        result = await redis_manager.client.ping()
        if result:
            print("Redis 连接成功")
            return True
        else:
            print("Redis ping 失败")
            return False
    except Exception as e:
        print(f"Redis 连接失败: {e}")
        return False


async def test_cors_config():
    """测试 CORS 配置"""
    print("\n" + "="*60)
    print("测试 2: CORS 配置管理")
    print("="*60)
    
    try:
        # 1. 初始化默认配置
        print("\n2.1 初始化默认 CORS 配置...")
        result = await config_service.init_default_cors()
        if result:
            print("初始化成功")
        else:
            print("初始化失败")
            return False
        
        # 2. 获取配置
        print("\n2.2 获取 CORS 配置...")
        config = await config_service.get_cors_config()
        if config:
            print("获取成功")
            print(f"   Origins: {config.get('origins', [])}")
            print(f"   Methods: {config.get('methods', [])}")
            print(f"   Credentials: {config.get('credentials')}")
        else:
            print("获取失败")
            return False
        
        # 3. 更新配置
        print("\n2.3 更新 CORS 配置...")
        new_config = {
            "origins": ["http://localhost:9527", "http://example.com"],
            "credentials": True,
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "headers": ["Authorization", "Content-Type"]
        }
        result = await config_service.set_cors_config(new_config)
        if result:
            print("更新成功")
        else:
            print("更新失败")
            return False
        
        # 4. 验证更新
        print("\n2.4 验证更新...")
        updated = await config_service.get_cors_config()
        if updated and updated.get('origins') == new_config['origins']:
            print("验证成功")
        else:
            print("验证失败")
            return False
        
        # 5. 添加 Origin
        print("\n2.5 添加 Origin...")
        result = await config_service.add_cors_origin("http://test.com")
        if result:
            print("添加成功")
            config = await config_service.get_cors_config()
            print(f"   当前 Origins: {config.get('origins', [])}")
        
        # 6. 移除 Origin
        print("\n2.6 移除 Origin...")
        result = await config_service.remove_cors_origin("http://test.com")
        if result:
            print("移除成功")
            config = await config_service.get_cors_config()
            print(f"   当前 Origins: {config.get('origins', [])}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hmac_key_management():
    """测试 HMAC Key 管理"""
    print("\n" + "="*60)
    print("测试 3: HMAC Key 管理")
    print("="*60)
    
    try:
        app_id = "test-admin-service"
        
        # 1. 设置 HMAC Key
        print("\n3.1 设置 HMAC Key...")
        secret_key = "test-secret-key-for-admin-12345678"
        result = await config_service.set_hmac_key(app_id, secret_key)
        if result:
            print(f"设置成功: {app_id}")
        else:
            print("设置失败")
            return False
        
        # 2. 获取 HMAC Key
        print("\n3.2 获取 HMAC Key...")
        retrieved_key = await config_service.get_hmac_key(app_id)
        if retrieved_key == secret_key:
            print("获取成功")
            print(f"   Key: {retrieved_key[:20]}...")
        else:
            print("获取失败或不匹配")
            return False
        
        # 3. 获取所有 Keys
        print("\n3.3 获取所有 HMAC Keys...")
        all_keys = await config_service.get_all_hmac_keys()
        print(f"获取成功，共 {len(all_keys)} 个密钥")
        for aid, key in list(all_keys.items())[:5]:
            print(f"   - {aid}: {key[:20]}...")
        
        # 4. 删除 HMAC Key
        print("\n3.4 删除 HMAC Key...")
        result = await config_service.delete_hmac_key(app_id)
        if result:
            print("删除成功")
        else:
            print("删除失败")
            return False
        
        # 5. 验证删除
        print("\n3.5 验证删除...")
        deleted_key = await config_service.get_hmac_key(app_id)
        if deleted_key is None:
            print("验证成功（Key 已删除）")
        else:
            print("验证失败（Key 仍然存在）")
            return False
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_gateway_registration():
    """测试 Gateway 注册"""
    print("\n" + "="*60)
    print("测试 4: Gateway 注册流程")
    print("="*60)
    
    try:
        from app.services.register_service import register_service
        from app.utils.http_client import http_client
        
        # 0. 初始化 HTTP 客户端
        print("\n4.0 初始化 HTTP 客户端...")
        await http_client.init()
        print("HTTP 客户端已初始化")
        
        # 1. 准备 HMAC Key
        print("\n4.1 准备 HMAC Key...")
        app_id = register_service._app_id
        secret_key = "admin-service-secret-key-12345678"
        await config_service.set_hmac_key(app_id, secret_key)
        print(f"HMAC Key 已设置: {app_id}")
        
        # 2. 注册到 Gateway
        print("\n4.2 注册到 Gateway...")
        result = await register_service.register()
        if result:
            print("注册成功")
            print(f"   Service ID: {register_service.service_info.get('id')}")
            print(f"   URL: {register_service.service_info.get('url')}")
        else:
            print("注册失败（Gateway 可能未运行）")
            print("   提示: 请先启动 Gateway 服务")
            await http_client.close()
            return False
        
        # 3. 等待一下
        print("\n4.3 等待 3 秒...")
        await asyncio.sleep(3)
        
        # 4. 注销
        print("\n4.4 注销服务...")
        result = await register_service.unregister()
        if result:
            print("注销成功")
        else:
            print("注销失败")
        
        # 清理
        await http_client.close()
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# Admin 服务注册流程测试")
    print("#"*60)
    
    results = []
    
    # 运行测试
    results.append(("Redis 连接", await test_redis_connection()))
    results.append(("CORS 配置", await test_cors_config()))
    results.append(("HMAC Key 管理", await test_hmac_key_management()))
    results.append(("Gateway 注册", await test_gateway_registration()))
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "通过" if result else "失败"
        print(f"{status} - {name}")
    
    print("\n" + "-"*60)
    print(f"总计: {passed}/{total} 测试通过")
    print(f"成功率: {passed/total*100:.1f}%")
    print("-"*60)
    
    if passed == total:
        print("\n所有测试通过！Admin 注册流程完整！")
    elif passed >= total * 0.8:
        print(f"\n大部分测试通过 ({passed}/{total})")
    else:
        print(f"\n部分测试失败，请检查配置")
    
    # 清理
    await redis_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
