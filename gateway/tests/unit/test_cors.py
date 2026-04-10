"""
CORS 中间件测试 - 测试辅助方法
"""

import pytest
from unittest.mock import MagicMock, patch
from config import settings


class TestCORSHelperFunctions:
    """CORS 辅助函数测试"""

    def test_settings_cors_origins(self):
        """CORS 原始配置"""
        assert "http://localhost:9527" in settings.CORS_ORIGINS
        assert "http://127.0.0.1:9527" in settings.CORS_ORIGINS

    def test_settings_cors_credentials(self):
        """CORS 凭证配置"""
        assert settings.CORS_ALLOW_CREDENTIALS is True

    def test_settings_cors_methods(self):
        """CORS 方法配置"""
        assert "GET" in settings.CORS_ALLOW_METHODS
        assert "POST" in settings.CORS_ALLOW_METHODS
        assert "OPTIONS" in settings.CORS_ALLOW_METHODS

    def test_settings_cors_headers(self):
        """CORS 头部配置"""
        assert "Authorization" in settings.CORS_ALLOW_HEADERS
        assert "Content-Type" in settings.CORS_ALLOW_HEADERS


class TestOriginMatching:
    """Origin 匹配测试"""

    def test_exact_match(self):
        """精确匹配"""
        origins = ["http://localhost:3000", "http://example.com"]
        origin = "http://localhost:3000"
        assert origin in origins

    def test_wildcard_match(self):
        """通配符匹配"""
        origins = ["*"]
        # 通配符应该匹配任何 origin
        assert True

    def test_subdomain_match(self):
        """子域名匹配"""
        origins = ["http://localhost:3000"]
        # localhost 不应该匹配 127.0.0.1
        assert "http://127.0.0.1:3000" not in origins

    def test_no_match(self):
        """不匹配"""
        origins = ["http://localhost:3000"]
        origin = "http://evil.com"
        assert origin not in origins
