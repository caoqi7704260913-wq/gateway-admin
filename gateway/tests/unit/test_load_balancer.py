"""
负载均衡器测试
"""

import pytest
from app.services.load_balancer import LoadBalancer, get_load_balancer
from app.models import ServiceBase


class TestLoadBalancer:
    """负载均衡器测试"""

    @pytest.fixture
    def sample_services(self):
        """创建示例服务列表"""
        return [
            ServiceBase(
                id="1",
                host="192.168.1.1",
                name="service-1",
                url="http://192.168.1.1:8080",
                ip="192.168.1.1",
                port=8080,
                weight=1
            ),
            ServiceBase(
                id="2",
                host="192.168.1.2",
                name="service-2",
                url="http://192.168.1.2:8080",
                ip="192.168.1.2",
                port=8080,
                weight=1
            ),
            ServiceBase(
                id="3",
                host="192.168.1.3",
                name="service-3",
                url="http://192.168.1.3:8080",
                ip="192.168.1.3",
                port=8080,
                weight=1
            ),
        ]

    @pytest.fixture
    def weighted_services(self):
        """创建加权服务列表"""
        return [
            ServiceBase(
                id="1",
                host="192.168.1.1",
                name="service-1",
                url="http://192.168.1.1:8080",
                ip="192.168.1.1",
                port=8080,
                weight=3
            ),
            ServiceBase(
                id="2",
                host="192.168.1.2",
                name="service-2",
                url="http://192.168.1.2:8080",
                ip="192.168.1.2",
                port=8080,
                weight=1
            ),
        ]

    @pytest.mark.asyncio
    async def test_round_robin(self, sample_services):
        """轮询策略测试"""
        lb = LoadBalancer(strategy="round_robin")
        
        selected = [await lb.select(sample_services) for _ in range(6)]
        ids = [s.id for s in selected]
        
        # 轮询应该是 1, 2, 3, 1, 2, 3
        assert ids[:3] == ["1", "2", "3"]
        assert ids[3] == "1"

    @pytest.mark.asyncio
    async def test_weighted_round_robin(self, weighted_services):
        """加权轮询策略测试"""
        lb = LoadBalancer(strategy="weighted_round_robin")
        
        selected = [await lb.select(weighted_services) for _ in range(4)]
        ids = [s.id for s in selected]
        
        # 权重3:1，前4次应该 1,1,1,2
        assert ids.count("1") == 3
        assert ids.count("2") == 1

    @pytest.mark.asyncio
    async def test_random_strategy(self, sample_services):
        """随机策略测试"""
        lb = LoadBalancer(strategy="random")
        
        selected = await lb.select(sample_services)
        assert selected.id in ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_empty_instances(self):
        """空实例列表测试"""
        lb = LoadBalancer(strategy="round_robin")
        selected = await lb.select([])
        assert selected is None

    @pytest.mark.asyncio
    async def test_single_instance(self, sample_services):
        """单实例测试"""
        lb = LoadBalancer(strategy="round_robin")
        
        single_service = [sample_services[0]]
        selected = await lb.select(single_service)
        
        assert selected.id == "1"

    @pytest.mark.asyncio
    async def test_invalid_strategy_defaults_to_round_robin(self, sample_services):
        """无效策略测试 - 应该降级到轮询"""
        lb = LoadBalancer(strategy="invalid_strategy")
        selected = await lb.select(sample_services)
        assert selected is not None

    @pytest.mark.asyncio
    async def test_reset_counters(self, sample_services):
        """重置计数器测试"""
        lb = LoadBalancer(strategy="round_robin")
        
        # 选择几次
        await lb.select(sample_services)
        await lb.select(sample_services)
        
        # 重置
        lb.reset()
        
        # 再次选择应该从头开始
        selected = await lb.select(sample_services)
        assert selected.id == "1"

    def test_get_load_balancer_singleton(self):
        """单例模式测试"""
        lb1 = get_load_balancer()
        lb2 = get_load_balancer()
        assert lb1 is lb2
