"""
熔断器

保护后端服务，当失败率过高时快速失败，防止级联故障
"""

import time
import asyncio
import inspect
from enum import Enum
from typing import Callable, Optional, Any
from dataclasses import dataclass, field
from loguru import logger

from app.utils.redis_manager import get_redis_manager


class CircuitState(Enum):
    """熔断状态"""
    CLOSED = "closed"      # 关闭，正常请求
    OPEN = "open"          # 开启，快速失败
    HALF_OPEN = "half_open"  # 半开，允许一个请求


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5        # 失败次数阈值
    success_threshold: int = 2         # 半开后成功次数阈值
    timeout: int = 30                  # 熔断超时（秒）
    half_open_max_calls: int = 1       # 半开状态允许的请求数


@dataclass
class CircuitBreakerStats:
    """熔断器统计"""
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    half_open_calls: int = 0
    opened_at: Optional[float] = None


class CircuitBreaker:
    """
    熔断器

    状态转换:
    CLOSED → OPEN: 失败次数达到阈值
    OPEN → HALF_OPEN: 超时后
    HALF_OPEN → CLOSED: 成功次数达到阈值
    HALF_OPEN → OPEN: 再次失败
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        use_redis: bool = False
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.use_redis = use_redis
        self.redis = get_redis_manager() if use_redis else None
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    def _get_redis_key(self, field: str) -> str:
        """获取 Redis key"""
        return f"circuit_breaker:{self.name}:{field}"

    async def _load_from_redis(self):
        """从 Redis 加载状态"""
        if not self.use_redis or not self.redis:
            return

        try:
            state = await self.redis.hget(self._get_redis_key("state"), "state")
            if state:
                self._stats.state = CircuitState(state)

            failure_count = await self.redis.hget(self._get_redis_key("stats"), "failure_count")
            if failure_count:
                self._stats.failure_count = int(failure_count)

            opened_at = await self.redis.hget(self._get_redis_key("stats"), "opened_at")
            if opened_at:
                self._stats.opened_at = float(opened_at)

        except Exception as e:
            logger.warning(f"熔断器 {self.name} 从 Redis 加载状态失败: {e}")

    async def _save_to_redis(self):
        """保存状态到 Redis"""
        if not self.use_redis or not self.redis:
            return

        try:
            await self.redis.hset(
                self._get_redis_key("state"),
                "state",
                self._stats.state.value
            )
            await self.redis.hset(
                self._get_redis_key("stats"),
                "failure_count",
                str(self._stats.failure_count)
            )
            if self._stats.opened_at:
                await self.redis.hset(
                    self._get_redis_key("stats"),
                    "opened_at",
                    str(self._stats.opened_at)
                )
        except Exception as e:
            logger.warning(f"熔断器 {self.name} 保存状态到 Redis 失败: {e}")

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._stats.state

    @property
    def is_closed(self) -> bool:
        """是否关闭"""
        return self._stats.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """是否开启"""
        return self._stats.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """是否半开"""
        return self._stats.state == CircuitState.HALF_OPEN

    async def _check_timeout(self):
        """检查是否超时，自动转换状态"""
        if self._stats.state == CircuitState.OPEN:
            if self._stats.opened_at:
                elapsed = time.time() - self._stats.opened_at
                if elapsed >= self.config.timeout:
                    await self._transition_to_half_open()

    async def _transition_to_open(self):
        """转换到开启状态"""
        async with self._lock:
            if self._stats.state != CircuitState.OPEN:
                self._stats.state = CircuitState.OPEN
                self._stats.opened_at = time.time()
                self._stats.consecutive_failures = 0
                logger.warning(f"熔断器 {self.name} 已开启")
                await self._save_to_redis()

    async def _transition_to_half_open(self):
        """转换到半开状态"""
        async with self._lock:
            if self._stats.state == CircuitState.OPEN:
                self._stats.state = CircuitState.HALF_OPEN
                self._stats.half_open_calls = 0
                self._stats.consecutive_successes = 0
                logger.info(f"熔断器 {self.name} 进入半开状态")
                await self._save_to_redis()

    async def _transition_to_closed(self):
        """转换到关闭状态"""
        async with self._lock:
            if self._stats.state != CircuitState.CLOSED:
                self._stats.state = CircuitState.CLOSED
                self._stats.failure_count = 0
                self._stats.consecutive_failures = 0
                self._stats.consecutive_successes = 0
                self._stats.opened_at = None
                logger.info(f"熔断器 {self.name} 已关闭")
                await self._save_to_redis()

    async def record_success(self):
        """记录成功"""
        async with self._lock:
            self._stats.success_count += 1
            self._stats.total_calls += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()

            if self._stats.state == CircuitState.HALF_OPEN:
                self._stats.half_open_calls -= 1
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to_closed()

            await self._save_to_redis()

    async def record_failure(self):
        """记录失败"""
        async with self._lock:
            self._stats.failure_count += 1
            self._stats.total_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.last_failure_time = time.time()

            if self._stats.state == CircuitState.HALF_OPEN:
                await self._transition_to_open()
            elif self._stats.consecutive_failures >= self.config.failure_threshold:
                await self._transition_to_open()

            await self._save_to_redis()

    async def can_execute(self) -> bool:
        """是否可以执行请求"""
        await self._check_timeout()

        if self._stats.state == CircuitState.CLOSED:
            return True

        if self._stats.state == CircuitState.HALF_OPEN:
            return self._stats.half_open_calls < self.config.half_open_max_calls

        return False

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带熔断保护的函数

        Args:
            func: 要执行的异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitOpenError: 熔断开启时抛出
        """
        if not await self.can_execute():
            raise CircuitOpenError(f"Circuit breaker {self.name} is open")

        if self._stats.state == CircuitState.HALF_OPEN:
            self._stats.half_open_calls += 1

        try:
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure()
            raise


class CircuitOpenError(Exception):
    """熔断开启异常"""
    pass


class CircuitBreakerRegistry:
    """熔断器注册表"""

    _breakers: dict[str, CircuitBreaker] = {}

    @classmethod
    def get(cls, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        获取熔断器实例

        Args:
            name: 熔断器名称
            config: 配置

        Returns:
            熔断器实例
        """
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]

    @classmethod
    def get_all_stats(cls) -> dict[str, dict]:
        """获取所有熔断器状态"""
        return {
            name: {
                "state": breaker.state.value,
                "failure_count": breaker._stats.failure_count,
                "success_count": breaker._stats.success_count,
                "total_calls": breaker._stats.total_calls,
                "consecutive_failures": breaker._stats.consecutive_failures,
                "last_failure_time": breaker._stats.last_failure_time,
                "last_success_time": breaker._stats.last_success_time,
            }
            for name, breaker in cls._breakers.items()
        }

    @classmethod
    def reset_all(cls):
        """重置所有熔断器"""
        for breaker in cls._breakers.values():
            breaker._stats = CircuitBreakerStats()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: int = 30
) -> CircuitBreaker:
    """
    获取熔断器

    Args:
        name: 熔断器名称
        failure_threshold: 失败次数阈值
        success_threshold: 半开后成功次数阈值
        timeout: 熔断超时（秒）

    Returns:
        熔断器实例
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout
    )
    return CircuitBreakerRegistry.get(name, config)
