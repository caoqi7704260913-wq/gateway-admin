# Admin 测试目录结构

## 📁 目录组织

```
tests/
├── __init__.py
├── unit/                    # 单元测试
│   └── __init__.py
└── test_admin_registration.py  # Admin 注册流程测试
```

---

## 🧪 测试文件说明

### test_admin_registration.py

**用途**: 测试 Admin 服务的完整注册流程

**测试内容**:
1. Redis 连接测试
2. CORS 配置管理
3. HMAC Key 管理
4. Gateway 注册流程

**运行方式**:
```bash
cd d:\python_project\admin
python tests/test_admin_registration.py
```

**预期输出**:
```
✅ 通过 - Redis 连接
✅ 通过 - CORS 配置
✅ 通过 - HMAC Key 管理
❌ 失败 - Gateway 注册 (Gateway 未运行)

总计: 3/4 测试通过
```

---

## 🚀 运行测试

### 运行所有测试

```bash
cd d:\python_project\admin
pytest tests/ -v
```

### 运行特定测试

```bash
# 运行注册流程测试
python tests/test_admin_registration.py

# 使用 pytest
pytest tests/test_admin_registration.py -v
```

### 运行单元测试

```bash
pytest tests/unit/ -v
```

---

## ⚠️ 注意事项

### 1. 测试文件位置

**✅ 正确**: 所有测试文件在 `tests/` 目录下

**❌ 错误**: 测试文件在项目根目录

### 2. 不使用已废弃的函数

**❌ 避免**:
```python
@app.on_event("startup")
async def startup():
    pass
```

**✅ 使用**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    yield
    # 关闭逻辑
```

### 3. 依赖服务

运行测试前确保以下服务正在运行：
- Redis (端口 6379)
- Gateway (端口 9000)
- Consul (端口 8500, 可选)

---

## 📝 添加新测试

### 单元测试示例

在 `tests/unit/` 下创建新的测试文件：

```python
# tests/unit/test_config_service.py
import pytest
from app.services.config_service import config_service


@pytest.mark.asyncio
async def test_get_cors_config():
    """测试获取 CORS 配置"""
    config = await config_service.get_cors_config()
    assert config is not None
    assert "origins" in config


@pytest.mark.asyncio
async def test_set_hmac_key():
    """测试设置 HMAC Key"""
    result = await config_service.set_hmac_key("test-app", "secret-key")
    assert result is True
    
    key = await config_service.get_hmac_key("test-app")
    assert key == "secret-key"
```

### 集成测试示例

在 `tests/` 下创建集成测试：

```python
# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint(client):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
```

---

## 🔧 Pytest 配置

如果需要，可以创建 `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
```

---

## 📊 测试覆盖率

查看测试覆盖率：

```bash
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

查看 HTML 报告：
```bash
# Windows
start htmlcov\index.html

# Linux/Mac
open htmlcov/index.html
```

---

## 💡 最佳实践

### 1. 命名规范

- 测试文件: `test_<module>.py`
- 测试类: `Test<Class>`
- 测试函数: `test_<functionality>`

### 2. 使用 Fixtures

```python
@pytest.fixture
async def redis_client():
    """Redis 客户端 fixture"""
    from app.utils.redis_manager import redis_manager
    await redis_manager.init()
    yield redis_manager
    await redis_manager.close()
```

### 3. 异步测试

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### 4. 清理资源

```python
@pytest.fixture
async def temp_config():
    """临时配置 fixture"""
    # 设置
    await config_service.set_cors_config(test_config)
    yield
    # 清理
    await config_service.delete_cors_config()
```

---

## 🔍 常见问题

### Q: 测试找不到模块？

**解决**: 确保在项目根目录运行测试，或设置 PYTHONPATH：

```bash
# Windows
set PYTHONPATH=%PYTHONPATH%;d:\python_project\admin

# Linux/Mac
export PYTHONPATH=$PYTHONPATH:/path/to/admin
```

### Q: 异步测试不工作？

**解决**: 安装 pytest-asyncio：

```bash
pip install pytest-asyncio
```

并在 `pytest.ini` 中配置：
```ini
[pytest]
asyncio_mode = auto
```

### Q: 如何跳过需要外部服务的测试？

```python
import pytest

@pytest.mark.skipif(
    not os.getenv("GATEWAY_URL"),
    reason="需要 Gateway 服务"
)
def test_gateway_registration():
    pass
```

---

## 📚 相关文档

- [Admin 注册流程说明](../docs/注册流程说明.md)
- [完成总结](../docs/完成总结.md)
- [Pytest 文档](https://docs.pytest.org/)

---

**保持测试文件在 tests 目录，使用最新的 API！** ✅
