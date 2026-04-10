"""检查 Redis 中的服务数据"""
import sys
sys.path.insert(0, 'd:/python_project/gateway')
import asyncio

from app.utils.redis_manager import get_redis_manager
from app.services.discovery import get_service_discovery

async def check():
    rm = get_redis_manager()
    discovery = get_service_discovery()
    
    print('=== Check Redis Service Data ===\n')
    
    # 列出所有 service:* 开头的 key
    keys = await rm.keys('service:*')
    print(f'[Redis] All service keys: {keys}')
    
    # 检查每个 key 的数据
    for key in keys:
        value = await rm.get(key)
        print(f'\n{key}:')
        print(f'  {value}')
    
    # 测试从 discovery 发现服务
    print('\n=== Test Discovery ===')
    
    service_names = ['user-service', 'test-service', 'admin-service']
    for name in service_names:
        services = await discovery.get_healthy_services(name)
        print(f'Discovered {name}: {len(services)} instances')
        for s in services:
            print(f'  - {s.host}:{s.port} (weight={s.weight})')

asyncio.run(check())
