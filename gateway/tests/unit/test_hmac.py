"""
HMAC 验证测试
"""

import pytest
import time
import hashlib
import hmac as hmac_lib
from config import settings


class TestHMACHelperFunctions:
    """HMAC 辅助函数测试"""

    def test_settings_hmac_enabled(self):
        """HMAC 启用配置"""
        assert settings.HMAC_ENABLED is True

    def test_settings_hmac_secret_exists(self):
        """HMAC 密钥配置"""
        assert settings.HMAC_SECRET_KEY is not None
        assert len(settings.HMAC_SECRET_KEY) > 0

    def test_settings_timestamp_tolerance(self):
        """时间戳容差配置"""
        assert settings.HMAC_TIMESTAMP_TOLERANCE == 300


class TestHMACSignatureGeneration:
    """HMAC 签名生成测试"""

    def generate_signature(self, secret: str, message: str, timestamp: str) -> str:
        """生成 HMAC 签名"""
        sign_str = f"{timestamp}:{message}"
        return hmac_lib.new(
            secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()

    def test_signature_generation(self):
        """签名生成测试"""
        secret = "test-secret"
        timestamp = "1234567890"
        message = "test-message"
        
        signature = self.generate_signature(secret, message, timestamp)
        
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex digest

    def test_signature_consistency(self):
        """签名一致性测试"""
        secret = "test-secret"
        timestamp = "1234567890"
        message = "test-message"
        
        sig1 = self.generate_signature(secret, message, timestamp)
        sig2 = self.generate_signature(secret, message, timestamp)
        
        assert sig1 == sig2

    def test_signature_different_secret(self):
        """不同密钥生成不同签名"""
        timestamp = "1234567890"
        message = "test-message"
        
        sig1 = self.generate_signature("secret1", message, timestamp)
        sig2 = self.generate_signature("secret2", message, timestamp)
        
        assert sig1 != sig2

    def test_signature_different_message(self):
        """不同消息生成不同签名"""
        secret = "test-secret"
        timestamp = "1234567890"
        
        sig1 = self.generate_signature(secret, "message1", timestamp)
        sig2 = self.generate_signature(secret, "message2", timestamp)
        
        assert sig1 != sig2

    def test_signature_different_timestamp(self):
        """不同时间戳生成不同签名"""
        secret = "test-secret"
        message = "test-message"
        
        sig1 = self.generate_signature(secret, message, "1234567890")
        sig2 = self.generate_signature(secret, message, "1234567891")
        
        assert sig1 != sig2


class TestHMACVerification:
    """HMAC 验证测试"""

    def verify_signature(self, secret: str, timestamp: str, message: str, signature: str) -> bool:
        """验证签名"""
        sign_str = f"{timestamp}:{message}"
        expected = hmac_lib.new(
            secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac_lib.compare_digest(signature, expected)

    def test_valid_signature(self):
        """有效签名验证"""
        secret = "test-secret"
        timestamp = "1234567890"
        message = "test-message"
        
        # 生成签名
        sign_str = f"{timestamp}:{message}"
        signature = hmac_lib.new(
            secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # 验证
        result = self.verify_signature(secret, timestamp, message, signature)
        assert result is True

    def test_invalid_signature(self):
        """无效签名验证"""
        secret = "test-secret"
        timestamp = "1234567890"
        message = "test-message"
        
        result = self.verify_signature(secret, timestamp, message, "invalid-signature")
        assert result is False

    def test_tampered_message(self):
        """篡改消息检测"""
        secret = "test-secret"
        timestamp = "1234567890"
        original_message = "original-message"
        
        # 生成原始签名
        sign_str = f"{timestamp}:{original_message}"
        signature = hmac_lib.new(
            secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # 用篡改的消息验证
        tampered_message = "tampered-message"
        result = self.verify_signature(secret, timestamp, tampered_message, signature)
        assert result is False

    def test_expired_timestamp(self):
        """过期时间戳检测"""
        secret = "test-secret"
        old_timestamp = str(int(time.time()) - 600)  # 10分钟前
        message = "test-message"
        tolerance = 300  # 5分钟容差
        
        # 生成签名
        sign_str = f"{old_timestamp}:{message}"
        signature = hmac_lib.new(
            secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # 检查是否过期
        current_time = int(time.time())
        is_expired = abs(current_time - int(old_timestamp)) > tolerance
        
        assert is_expired is True
