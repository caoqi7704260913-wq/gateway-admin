"""
服务模块
"""

# 路由器
from .router import Router, get_router

# 负载均衡
from .load_balancer import LoadBalancer, get_load_balancer

# 健康检查
from .health_checker import HealthChecker

# 服务发现
from .discovery import ServiceDiscovery, get_service_discovery

# 配置管理
from .config_manager import ConfigManager, get_config_manager

# 熔断器
from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitOpenError,
    CircuitBreakerRegistry,
    get_circuit_breaker,
)

__all__ = [
    # 路由器
    "Router",
    "get_router",
    # 负载均衡
    "LoadBalancer",
    "get_load_balancer",
    # 健康检查
    "HealthChecker",
    # 服务发现
    "ServiceDiscovery",
    "get_service_discovery",
    # 配置管理
    "ConfigManager",
    "get_config_manager",
    # 熔断器
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitOpenError",
    "CircuitBreakerRegistry",
    "get_circuit_breaker",
]
