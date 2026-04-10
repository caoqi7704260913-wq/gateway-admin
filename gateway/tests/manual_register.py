"""手动注册服务并检查 Redis"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')
import asyncio
import json

from app.services.discovery import get_service_discovery
from app.utils.redis_manager import get_redis_manager
from app.models.service import ServiceBase

async def main():
    discovery = get_service_discovery()
    redis_mgr = get_redis_manager()
    
    print('=== Manual Register & Check ===\n')
    
    # 创建服务
    service = ServiceBase(
        id="my-service-001",
        name="my-service",
        host="10.0.0.50",
        ip="10.0.0.50",
        port=7000,
        url="http://10.0.0.50:7000",
        weight=8,
        status="healthy"
    )
    
    # 注册到 Redis + Consul
    print('[1] Register service...')
    await discovery.register_service(service)
    print('Registered!')
    
    # 检查 Redis
    print('\n[2] Check Redis keys:')
    keys = await redis_mgr.keys('service:*')
    print(f'  Keys: {keys}')
    
    # 检查具体数据
    redis_key = f"service:{service.name}:{service.id}"
    print(f'\n[3] Get Redis key: {redis_key}')
    value = await redis_mgr.get(redis_key)
    print(f'  Value: {value}')
    
    if value:
        data = json.loads(value)
        print(f'\n[4] Parsed:')
        for k, v in data.items():
            print(f'    {k}: {v}')
    
    print('\n[5] Check Consul:')
    services = discovery.consul_manager.get_services()
    print(f'  Consul services: {len(services)}')
    for name, info in services.items():
        print(f'    - {name}: {info.get("Address")}:{info.get("Port")}')
    
    print('\n[DONE] Data is in Redis now!')

asyncio.run(main())
