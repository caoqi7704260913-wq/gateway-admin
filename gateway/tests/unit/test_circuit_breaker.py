"""
熔断器测试
"""

import pytest
import asyncio
from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    CircuitOpenError,
)


class TestCircuitBreaker:
    """熔断器测试"""

    def test_initial_state(self):
        """初始状态测试"""
        cb = CircuitBreaker(name="test", config=CircuitBreakerConfig(failure_threshold=3))
        assert cb.state == CircuitState.CLOSED

    def test_is_closed(self):
        """关闭状态测试"""
        cb = CircuitBreaker(name="test")
        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self):
        """记录失败增加计数"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=5)
        )
        
        await cb.record_failure()
        assert cb._stats.failure_count == 1
        assert cb._stats.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_state_transitions_to_open(self):
        """状态转换到打开"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2)
        )
        
        await cb.record_failure()
        await cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert cb.is_open is True

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """成功重置失败计数"""
        cb = CircuitBreaker(name="test", config=CircuitBreakerConfig(failure_threshold=5))
        
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()
        
        assert cb._stats.failure_count == 0
        assert cb._stats.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self):
        """关闭状态可以执行"""
        cb = CircuitBreaker(name="test")
        result = await cb.can_execute()
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_execute_when_open(self):
        """打开状态不能执行"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1)
        )
        
        await cb.record_failure()
        assert cb.is_open is True
        
        result = await cb.can_execute()
        assert result is False

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        """超时后进入半开状态"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(
                failure_threshold=1,
                timeout=0.1
            )
        )
        
        await cb.record_failure()
        assert cb.is_open is True
        
        # 等待超时
        await asyncio.sleep(0.15)
        
        await cb._check_timeout()
        assert cb.is_half_open is True

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """执行成功记录"""
        cb = CircuitBreaker(name="test")
        
        async def dummy_func():
            return "success"
        
        result = await cb.execute(dummy_func)
        assert result == "success"
        assert cb._stats.success_count == 1

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        """执行失败记录"""
        cb = CircuitBreaker(name="test", config=CircuitBreakerConfig(failure_threshold=5))
        
        async def failing_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            await cb.execute(failing_func)
        
        assert cb._stats.failure_count == 1

    @pytest.mark.asyncio
    async def test_execute_blocked_when_open(self):
        """打开状态阻止执行"""
        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1)
        )
        
        await cb.record_failure()
        
        with pytest.raises(CircuitOpenError):
            await cb.execute(lambda: None)


class TestCircuitBreakerConfig:
    """熔断器配置测试"""

    def test_default_config(self):
        """默认配置"""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 30

    def test_custom_config(self):
        """自定义配置"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=3,
            timeout=60
        )
        assert config.failure_threshold == 10
        assert config.success_threshold == 3
        assert config.timeout == 60
