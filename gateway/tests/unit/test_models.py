"""
数据模型测试
"""

import pytest
from app.models import (
    WhitelistConfig,
    ServiceBase,
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    generate_service_id,
)


class TestWhitelistConfig:
    """白名单配置测试"""

    def test_create_whitelist(self):
        whitelist = WhitelistConfig(
            type="ip",
            value="192.168.1.1",
            description="测试IP"
        )
        assert whitelist.type == "ip"
        assert whitelist.value == "192.168.1.1"
        assert whitelist.description == "测试IP"

    def test_whitelist_optional_description(self):
        whitelist = WhitelistConfig(type="header", value="X-Custom-Header")
        assert whitelist.description is None


class TestServiceModels:
    """服务模型测试"""

    def test_generate_service_id(self):
        service_id = generate_service_id()
        assert service_id is not None
        assert len(service_id) > 0

    def test_service_base_defaults(self):
        service = ServiceBase(
            host="192.168.1.100",
            name="test-service",
            url="http://192.168.1.100:8080",
            ip="192.168.1.100",
            port=8080
        )
        assert service.weight == 1
        assert service.status == "healthy"
        assert service.metadata == {}
        assert service.global_whitelist == []
        assert service.last_heartbeat is None

    def test_service_create(self):
        service = ServiceCreate(
            host="192.168.1.100",
            name="user-service",
            url="http://192.168.1.100:8080",
            ip="192.168.1.100",
            port=8080,
            weight=2,
            metadata={"version": "v1"}
        )
        assert service.name == "user-service"
        assert service.weight == 2
        assert service.metadata["version"] == "v1"

    def test_service_update(self):
        update = ServiceUpdate(
            weight=3,
            status="unhealthy"
        )
        assert update.weight == 3
        assert update.status == "unhealthy"
        assert update.name is None

    def test_service_response(self):
        service = ServiceResponse(
            host="192.168.1.100",
            name="test-service",
            url="http://192.168.1.100:8080",
            ip="192.168.1.100",
            port=8080,
            created_at=None,
            updated_at=None
        )
        assert service.name == "test-service"
        assert hasattr(service, 'created_at')
