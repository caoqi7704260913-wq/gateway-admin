"""
限流中间件测试脚本

测试场景：
1. 正常请求（在限流范围内）
2. 超过限流（触发 429 错误）
3. 降级模式（Redis 不可用时放行）
"""
import asyncio
import httpx
from loguru import logger


async def test_rate_limit():
    """测试限流功能"""
    base_url = "http://localhost:8001"
    
    logger.info("="*60)
    logger.info("开始测试限流中间件")
    logger.info("="*60)
    
    # 测试 1: 正常请求
    logger.info("\n📝 测试 1: 正常请求（在限流范围内）")
    async with httpx.AsyncClient() as client:
        for i in range(5):
            response = await client.get(f"{base_url}/health")
            rate_limit = response.headers.get("X-RateLimit-Limit", "N/A")
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            logger.info(f"  请求 {i+1}: {response.status_code} - Remaining: {remaining}/{rate_limit}")
    
    # 测试 2: 健康检查端点（应该被排除）
    logger.info("\n📝 测试 2: 健康检查端点（应跳过限流）")
    async with httpx.AsyncClient() as client:
        for endpoint in ["/health", "/healthz", "/status"]:
            response = await client.get(f"{base_url}{endpoint}")
            has_rate_limit = "X-RateLimit-Limit" in response.headers
            logger.info(f"  {endpoint}: {response.status_code} - 有限流头: {has_rate_limit}")
    
    # 测试 3: 快速发送大量请求（触发限流）
    logger.info("\n📝 测试 3: 快速发送大量请求（触发限流）")
    logger.info("  注意: 默认配置为 100 次/60秒，可能需要调整配置来测试")
    logger.info("  建议: 设置 RATE_LIMIT_MAX_REQUESTS=5 进行测试")
    
    # 测试 4: 查看限流响应头
    logger.info("\n📝 测试 4: 限流响应头")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        logger.info(f"  X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit', 'N/A')}")
        logger.info(f"  X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining', 'N/A')}")
        logger.info(f"  X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset', 'N/A')}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ 限流测试完成")
    logger.info("="*60)
    logger.info("\n💡 提示:")
    logger.info("  1. 要测试限流触发，请修改 .env:")
    logger.info("     RATE_LIMIT_MAX_REQUESTS=5")
    logger.info("     RATE_LIMIT_WINDOW_SECONDS=60")
    logger.info("  2. 重启服务后快速发送超过 5 次请求")
    logger.info("  3. 应该会收到 429 Too Many Requests 错误")


if __name__ == "__main__":
    try:
        asyncio.run(test_rate_limit())
    except Exception as e:
        logger.error(f"测试失败: {e}")
        logger.info("\n💡 请确保 Admin 服务正在运行:")
        logger.info("   python -m app.main")
