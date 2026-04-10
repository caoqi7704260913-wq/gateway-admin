"""
HMAC 签名验证器

提供 HMAC 签名生成和验证功能，支持防重放攻击
"""

import hmac
import hashlib
import time
import secrets
from typing import Optional, Tuple
from loguru import logger
from config import settings


class HMACValidator:
    """HMAC 签名验证器"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        timestamp_tolerance: int = 300  # 5分钟时间戳容差
    ):
        """
        初始化验证器
        
        Args:
            secret_key: HMAC 密钥，默认使用配置中的密钥
            timestamp_tolerance: 时间戳容差（秒），默认5分钟
        """
        self.secret_key = secret_key or settings.HMAC_SECRET_KEY
        self.timestamp_tolerance = timestamp_tolerance
        # 用于存储已使用的 nonce（生产环境建议用 Redis）
        self._used_nonces: set = set()

    def generate_signature(
        self,
        body: str,
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> Tuple[str, int, str]:
        """
        生成 HMAC 签名（供客户端使用）
        
        Args:
            body: 请求体（字符串）
            timestamp: 时间戳，默认当前时间
            nonce: 随机字符串，默认自动生成
            
        Returns:
            (signature, timestamp, nonce) 元组
        """
        timestamp = timestamp or int(time.time())
        nonce = nonce or secrets.token_hex(16)
        
        # 签名内容：timestamp + nonce + body
        message = f"{timestamp}{nonce}{body}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp, nonce

    def verify_signature(
        self,
        signature: str,
        body: str,
        timestamp: int,
        nonce: str,
        client_key: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        验证 HMAC 签名
        
        Args:
            signature: 请求中的签名
            body: 请求体
            timestamp: 时间戳
            nonce: 随机字符串
            client_key: 客户端密钥（多租户场景）
            
        Returns:
            (是否验证通过, 错误信息)
        """
        # 1. 检查时间戳（防重放）
        current_time = int(time.time())
        if abs(current_time - timestamp) > self.timestamp_tolerance:
            return False, f"Timestamp expired (tolerance: {self.timestamp_tolerance}s)"

        # 2. 检查 nonce（防重放）
        if nonce in self._used_nonces:
            return False, "Nonce already used (replay attack)"
        
        # 3. 验证签名
        key = client_key or self.secret_key
        message = f"{timestamp}{nonce}{body}"
        expected_signature = hmac.new(
            key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return False, "Signature mismatch"

        # 4. 记录 nonce（防重放）
        self._used_nonces.add(nonce)
        # 清理过期的 nonce，防止内存膨胀
        self._cleanup_nonces()
        
        return True, "OK"

    def _cleanup_nonces(self, max_size: int = 10000):
        """清理过期的 nonce，防止内存膨胀"""
        if len(self._used_nonces) > max_size:
            # 保留最近的一半
            self._used_nonces = set(list(self._used_nonces)[-max_size // 2:])
            logger.debug(f"Cleaned up nonces, current size: {len(self._used_nonces)}")

    def clear_used_nonces(self):
        """清空已使用的 nonce（测试用）"""
        self._used_nonces.clear()


# 单例实例
_validator: Optional[HMACValidator] = None


def get_hmac_validator() -> HMACValidator:
    """获取 HMAC 验证器单例"""
    global _validator
    if _validator is None:
        _validator = HMACValidator()
    return _validator
