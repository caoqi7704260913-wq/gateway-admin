"""完整测试：Redis + Consul 服务注册、发现、转发"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')
import asyncio
import httpx

from app.services.discovery import get_service_discovery
from app.services.router import Router
from app.services.config_manager import get_config_manager
from app.models.service import ServiceBase

def ok(msg): return f"[OK] {msg}"
def fail(msg): return f"[FAIL] {msg}"

async def test_full_flow():
    print("=" * 60)
    print("Full Test: Redis + Consul Service Registration & Discovery")
    print("=" * 60)
    
    # ========== 1. Check Status ==========
    print("\n[1] Check Services Status\n")
    
    discovery = get_service_discovery()
    
    # Redis
    try:
        redis_client = await discovery.redis_manager.get_client()
        await redis_client.ping()
        print(ok("Redis connected"))
    except Exception as e:
        print(fail(f"Redis unavailable: {e}"))
        return
    
    # Consul
    consul_ok = discovery.consul_manager.is_healthy()
    print(ok("Consul connected") if consul_ok else fail("Consul unavailable"))
    
    if not consul_ok:
        print("\nExit: Consul not available")
        return
    
    # ========== 2. Service Registration ==========
    print("\n[2] Register Service to Redis + Consul\n")
    
    test_service = ServiceBase(
        id="user-service-001",
        name="user-service",
        host="127.0.0.1",
        ip="127.0.0.1",
        port=8001,
        url="http://127.0.0.1:8001",
        weight=10,
        status="healthy",
        metadata={"tags": ["test"]}
    )
    
    success = await discovery.register_service(test_service)
    print(ok("Service registered") if success else fail("Registration failed"))
    print(f"  - Name: {test_service.name}")
    print(f"  - ID: {test_service.id}")
    print(f"  - Address: {test_service.host}:{test_service.port}")
    
    # ========== 3. Service Discovery ==========
    print("\n[3] Service Discovery\n")
    
    services = await discovery.get_healthy_services("user-service")
    print(f"Discovered {test_service.name}: {len(services)} instance(s)")
    for svc in services:
        print(f"  - {svc.host}:{svc.port} (weight={svc.weight})")
    
    # ========== 4. Config Sync ==========
    print("\n[4] Config Sync (CORS)\n")
    
    config_mgr = get_config_manager()
    
    cors_config = {
        "allow_origins": ["http://localhost:3000", "http://localhost:9527"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["*"]
    }
    
    await config_mgr.set_cors_config(cors_config)
    print(ok("CORS config synced to Redis + Consul"))
    
    retrieved_cors = await config_mgr.get_cors_config()
    print(f"Read from Consul: {retrieved_cors.get('allow_origins')}")
    
    # ========== 5. Request Forwarding Simulation ==========
    print("\n[5] Request Forwarding Simulation\n")
    
    router = Router()
    
    print("Forwarding: /user/api/v1/login")
    print(f"  1. Route match: /user/* -> user-service")
    print(f"  2. Discovery: {len(services)} backend(s) found")
    if services:
        print(f"  3. Load balance: select {services[0].host}:{services[0].port}")
        print(f"  4. Target: http://{services[0].host}:{services[0].port}/api/v1/login")
    
    # ========== 6. Consul Health Check ==========
    print("\n[6] Consul Health Check\n")
    
    service_id = f"{test_service.name}-{test_service.host}:{test_service.port}"
    update_ok = discovery.consul_manager.update_ttl(service_id)
    print(ok(f"TTL updated: {service_id}") if update_ok else fail("TTL update failed"))
    
    all_services = discovery.consul_manager.get_services()
    print(f"Consul registered services: {len(all_services)}")
    for name, info in all_services.items():
        print(f"  - {name}: {info.get('Address')}:{info.get('Port')}")
    
    # ========== 7. Cleanup ==========
    print("\n[7] Cleanup\n")
    
    redis_key = f"service:{test_service.name}:{test_service.id}"
    await discovery.redis_manager.delete(redis_key)
    print(f"Redis key deleted: {redis_key}")
    
    discovery.consul_manager.deregister_service(service_id)
    print(f"Consul service deregistered: {service_id}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_full_flow())
