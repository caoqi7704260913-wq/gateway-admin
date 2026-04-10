"""
负载均衡模块

支持多种负载均衡策略：
- 轮询 (round_robin)
- 加权轮询 (weighted_round_robin)
- 随机 (random)
- 最少连接 (least_conn)
"""

import random
from typing import Optional
from loguru import logger
from app.models.service import ServiceBase


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, strategy: str = "round_robin"):
        """
        初始化负载均衡器
        
        Args:
            strategy: 负载均衡策略
        """
        self.strategy = strategy
        self._counters: dict[str, int] = {}  # 用于轮询计数
    
    async def select(self, services: list[ServiceBase]) -> Optional[ServiceBase]:
        """
        根据策略选择一个服务实例
        
        Args:
            services: 可用服务列表
        
        Returns:
            选中的服务实例，无可用服务时返回 None
        """
        if not services:
            return None
        
        if len(services) == 1:
            return services[0]
        
        if self.strategy == "round_robin":
            return self._round_robin(services)
        elif self.strategy == "weighted_round_robin":
            return self._weighted_round_robin(services)
        elif self.strategy == "random":
            return self._random(services)
        elif self.strategy == "least_conn":
            return self._least_conn(services)
        else:
            return self._round_robin(services)
    
    def _round_robin(self, services: list[ServiceBase]) -> ServiceBase:
        """轮询策略"""
        service_key = self._get_service_key(services)
        count = self._counters.get(service_key, 0)
        selected = services[count % len(services)]
        self._counters[service_key] = count + 1
        return selected
    
    def _weighted_round_robin(self, services: list[ServiceBase]) -> ServiceBase:
        """加权轮询策略"""
        # 构建加权列表
        weighted_list: list[ServiceBase] = []
        for s in services:
            weight = getattr(s, 'weight', 1) or 1
            weighted_list.extend([s] * weight)
        
        service_key = self._get_service_key(services)
        count = self._counters.get(service_key, 0)
        selected = weighted_list[count % len(weighted_list)]
        self._counters[service_key] = count + 1
        return selected
    
    def _random(self, services: list[ServiceBase]) -> ServiceBase:
        """随机策略"""
        return random.choice(services)
    
    def _least_conn(self, services: list[ServiceBase]) -> ServiceBase:
        """最少连接策略（暂用轮询替代）"""
        return self._round_robin(services)
    
    def _get_service_key(self, services: list[ServiceBase]) -> str:
        """生成服务列表的唯一键"""
        return ",".join(sorted([s.id for s in services]))
    
    def reset(self):
        """重置计数器"""
        self._counters.clear()


# 单例实例
_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer(strategy: Optional[str] = None) -> LoadBalancer:
    """获取负载均衡器单例"""
    global _load_balancer
    if _load_balancer is None:
        from config import settings
        final_strategy = strategy or settings.LOAD_BALANCER_STRATEGY
        _load_balancer = LoadBalancer(final_strategy)
    return _load_balancer
