"""清理所有 Redis 数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.utils.redis_manager import get_redis_manager

async def flush_all():
    """清空所有 Redis 数据"""
    redis = get_redis_manager()
    
    print("=" * 70)
    print("清理 Redis 中的所有数据")
    print("=" * 70)
    
    try:
        # 获取所有键
        all_keys = await redis.keys("*")
        print(f"\n找到 {len(all_keys)} 个键")
        
        if all_keys:
            # 删除所有键
            for key in all_keys:
                await redis.delete(key)
                print(f"  ✅ 已删除: {key}")
        
        print("\n✅ Redis 已清空！")
        
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(flush_all())

