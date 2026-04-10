"""测试 Consul KV 读写功能"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')

import consul
from config import settings

def test_consul_kv():
    client = consul.Consul(
        host=settings.CONSUL_HOST,
        port=settings.CONSUL_PORT,
        token=settings.CONSUL_TOKEN,
        scheme=settings.CONSUL_SCHEME,
        verify=settings.CONSUL_VERIFY
    )
    
    print("=== Test Consul KV ===")
    print(f"Connect: {settings.CONSUL_HOST}:{settings.CONSUL_PORT}")
    
    # Check health
    try:
        health = client.agent.self()
        print(f"Consul Status: OK")
        print(f"  - Version: {health.get('Config', {}).get('Version', 'N/A')}")
        print(f"  - NodeName: {health.get('Config', {}).get('NodeName', 'N/A')}")
    except Exception as e:
        print(f"Consul health check failed: {e}")
        return
    
    # Test write
    test_key = "gateway/test_key"
    test_value = "test_value_123"
    
    print(f"\n--- Write Test ---")
    result = client.kv.put(test_key, test_value)
    print(f"Write {test_key}={test_value}: {'OK' if result else 'FAIL'}")
    
    # Read
    print(f"\n--- Read Test ---")
    _, data = client.kv.get(test_key)
    if data:
        value = data['Value'].decode('utf-8')
        print(f"Read {test_key}: {value}")
    else:
        print(f"Read {test_key}: NOT FOUND")
    
    # List keys
    print(f"\n--- List Keys Test ---")
    _, keys = client.kv.get("", recurse=True)
    if keys:
        for k in keys:
            print(f"  - {k['Key']}")
    else:
        print("  No keys")
    
    # Delete
    print(f"\n--- Delete Test ---")
    client.kv.delete(test_key)
    _, data = client.kv.get(test_key)
    print(f"Delete {test_key}: {'OK' if data is None else 'FAIL'}")

if __name__ == "__main__":
    test_consul_kv()
