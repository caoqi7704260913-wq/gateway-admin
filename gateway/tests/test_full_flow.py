"""
完整流程测试脚本

测试场景：模拟前端登录请求后转发到内部服务
"""
import asyncio
import json
import time
import httpx
from loguru import logger

GATEWAY_URL = "http://localhost:9000"
APP_ID = "test-app"


def json_serializer(obj):
    """自定义 JSON 序列化器，处理 datetime"""
    from datetime import datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def test_flow():
    """执行完整测试流程"""
    logger.info("=" * 60)
    logger.info("开始测试：前端登录请求 -> 网关 -> 后端服务")
    logger.info("=" * 60)

    # ========== 直接写入 Redis 注册服务 ==========
    logger.info("\n[0] 直接注册服务到 Redis...")
    from app.utils.redis_manager import get_redis_manager
    from app.models.service import ServiceBase

    redis = get_redis_manager()
    client = await redis.get_client()

    service = ServiceBase(
        name="user",
        host="127.0.0.1",
        ip="127.0.0.1",
        port=8081,
        url="http://127.0.0.1:8081",
        weight=1,
        metadata={},
        status="healthy"
    )

    key = f"service:user:{service.id}"
    data = service.model_dump()
    data['last_heartbeat'] = None  # 避免 datetime 序列化问题
    await client.set(key, json.dumps(data, default=json_serializer), ex=30)
    logger.info(f"服务已注册: user (ID: {service.id})")

    async with httpx.AsyncClient(timeout=30.0) as http:
        # ========== 1. 健康检查 ==========
        logger.info("\n[1] 健康检查...")
        resp = await http.get(f"{GATEWAY_URL}/health")
        logger.info(f"网关状态: {resp.json()}")

        # ========== 2. 启动模拟后端服务 ==========
        logger.info("\n[2] 启动模拟后端服务...")

        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        class MockHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                logger.info(f"后端收到: {self.path} -> {body}")

                response = {
                    "code": 200,
                    "message": "登录成功",
                    "data": {"token": "mock_token_12345", "user_id": 10001}
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            def log_message(self, format, *args):
                pass

        mock_server = HTTPServer(('127.0.0.1', 8081), MockHandler)
        mock_thread = threading.Thread(target=mock_server.serve_forever)
        mock_thread.daemon = True
        mock_thread.start()
        logger.info("模拟后端服务已启动: http://127.0.0.1:8081")

        # ========== 3. 创建 HMAC 密钥 ==========
        logger.info("\n[3] 创建 HMAC 密钥...")
        resp = await http.post(f"{GATEWAY_URL}/api/config/hmac/key", json={"app_id": APP_ID})
        result = resp.json()
        secret_key = result.get("secret_key")
        if secret_key:
            logger.info(f"HMAC密钥: {secret_key[:8]}...{secret_key[-4:]}")
        else:
            logger.error(f"HMAC密钥创建失败: {result}")
            return

        # ========== 4. 模拟登录请求 ==========
        logger.info("\n[4] 模拟前端登录请求...")

        login_data = {"username": "admin", "password": "123123"}
        body_str = json.dumps(login_data)

        headers = {
            "Content-Type": "application/json",
            "X-App-Id": APP_ID,
            "X-Timestamp": str(int(time.time())),
            "X-Nonce": "test_nonce",
            "X-Signature": "dummy_for_test"
        }

        login_url = f"{GATEWAY_URL}/user/api/v1/login"
        logger.info(f"请求: POST {login_url}")

        resp = await http.post(login_url, headers=headers, content=body_str)
        logger.info(f"\n响应状态: {resp.status_code}")
        logger.info(f"响应体: {resp.text}")

        # ========== 5. 验证结果 ==========
        logger.info("\n[5] 验证结果...")

        if resp.status_code == 200:
            try:
                data = resp.json()
                if data.get("code") == 200:
                    logger.success("✓ 登录成功！请求已正确转发到后端服务")
                    logger.info(f"   用户信息: {data.get('data')}")
                else:
                    logger.warning(f"⚠ 后端返回异常: {data}")
            except:
                logger.warning(f"⚠ 响应非JSON: {resp.text}")
        else:
            logger.error(f"✗ 请求失败: HTTP {resp.status_code} - {resp.text}")

        # ========== 6. 查看服务列表 ==========
        logger.info("\n[6] 查看已注册服务...")
        resp = await http.get(f"{GATEWAY_URL}/api/services/user")
        logger.info(f"user服务: {resp.json()}")

        # ========== 7. 测试 CORS 配置 ==========
        logger.info("\n[7] 测试 CORS 配置...")
        resp = await http.get(f"{GATEWAY_URL}/api/config/cors")
        logger.info(f"CORS配置: {resp.json()}")

        # ========== 8. 查看熔断器状态 ==========
        logger.info("\n[8] 查看熔断器状态...")
        resp = await http.get(f"{GATEWAY_URL}/api/circuit-breakers")
        logger.info(f"熔断器: {resp.json()}")

        mock_server.shutdown()

    logger.info("\n" + "=" * 60)
    logger.info("测试完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_flow())
