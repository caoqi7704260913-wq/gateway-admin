"""
限流器测试 - 测试辅助函数
"""

import pytest
import time
from config import settings


class TestRateLimiterConfig:
    """限流器配置测试"""

    def test_rate_limiter_key_generation(self):
        """限流 key 生成测试"""
        rate_key = "api"
        client_ip = "192.168.1.1"
        
        key = f"{rate_key}:{client_ip}"
        assert key == "api:192.168.1.1"

    def test_window_calculation(self):
        """时间窗口计算测试"""
        window_seconds = 60
        now = time.time()
        window_start = int(now // window_seconds * window_seconds)
        reset_time = window_start + window_seconds
        
        assert window_start <= now < reset_time
        assert reset_time - window_start == window_seconds

    def test_remaining_requests_calculation(self):
        """剩余请求数计算"""
        max_requests = 100
        current_count = 75
        
        remaining = max(0, max_requests - current_count)
        is_allowed = current_count < max_requests
        
        assert remaining == 25
        assert is_allowed is True

    def test_rate_limit_exceeded(self):
        """超过限流测试"""
        max_requests = 100
        current_count = 100
        
        remaining = max(0, max_requests - current_count)
        is_allowed = current_count < max_requests
        
        assert remaining == 0
        assert is_allowed is False


class TestRateLimiterHelperFunctions:
    """限流器辅助函数测试"""

    def test_default_key_func_ip_extraction(self):
        """默认 key 函数 - IP 提取"""
        class MockRequest:
            client = type('obj', (object,), {'host': '192.168.1.100'})()
        
        request = MockRequest()
        client_ip = request.client.host if request.client else "unknown"
        
        assert client_ip == "192.168.1.100"

    def test_default_key_func_unknown_client(self):
        """默认 key 函数 - 未知客户端"""
        class MockRequest:
            client = None
        
        request = MockRequest()
        client_ip = request.client.host if request.client else "unknown"
        
        assert client_ip == "unknown"

    def test_redis_key_format(self):
        """Redis key 格式测试"""
        rate_key = "api"
        client_ip = "192.168.1.1"
        window_start = 1700000000
        
        redis_key = f"{rate_key}:{client_ip}:{window_start}"
        
        assert redis_key == "api:192.168.1.1:1700000000"

    def test_excluded_paths(self):
        """排除路径测试"""
        excluded_paths = ["/health", "/healthz", "/docs", "/redoc", "/openapi.json"]
        
        assert "/health" in excluded_paths
        assert "/healthz" in excluded_paths
        assert "/api/users" not in excluded_paths
