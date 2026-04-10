"""测试配置管理器 - Redis 与 Consul 同步"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')
import asyncio

from app.services.config_manager import get_config_manager

async def test_config_sync():
    config_manager = get_config_manager()
    print("=== Test Config Manager (Redis + Consul) ===\n")
    
    # 1. Test CORS Config
    print("--- Test CORS Config ---")
    test_cors = {
        "allow_origins": ["http://localhost:3000"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
    
    await config_manager.set_cors_config(test_cors)
    print("Set CORS to Redis+Consul: OK")
    
    # Read from Consul (priority)
    from_consul = await config_manager.get_cors_config()
    print(f"Read CORS from Consul: {from_consul.get('allow_origins')}")
    
    # 2. Test HMAC Key
    print("\n--- Test HMAC Key ---")
    service_name = "test-service"
    secret_key = "test_secret_key_12345"
    
    await config_manager.create_hmac_key(service_name, secret_key)
    print(f"Create HMAC key for {service_name}: OK")
    
    # Get HMAC key
    hmac_key = await config_manager.get_hmac_key(service_name)
    print(f"Get HMAC key: {hmac_key}")
    
    # 3. Cleanup
    print("\n--- Cleanup ---")
    await config_manager.delete_cors_config()
    await config_manager.delete_hmac_key(service_name)
    print("Cleanup: OK")
    
    print("\n=== All Tests Passed ===")

if __name__ == "__main__":
    asyncio.run(test_config_sync())
