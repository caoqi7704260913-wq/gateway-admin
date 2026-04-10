"""
配置测试
"""

import pytest
from config import settings


class TestSettings:
    """配置测试"""

    def test_app_name(self):
        assert settings.APP_NAME == "Gateway API"

    def test_app_version(self):
        assert settings.APP_VERSION == "1.0.0"

    def test_host(self):
        assert settings.HOST == "0.0.0.0"

    def test_port(self):
        assert settings.PORT == 8000

    def test_redis_config(self):
        assert settings.REDIS_HOST == "localhost"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0

    def test_cors_origins(self):
        assert "http://localhost:9527" in settings.CORS_ORIGINS

    def test_hmac_secret(self):
        assert settings.HMAC_SECRET_KEY is not None
        assert len(settings.HMAC_SECRET_KEY) > 0
