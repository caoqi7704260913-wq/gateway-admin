# Gateway 依赖说明

本文档详细说明 Gateway 服务的所有依赖及其用途。

## 📦 核心依赖

### Web 框架
- **fastapi** (>=0.115.0) - 高性能异步 Web 框架
- **uvicorn** (>=0.30.0) - ASGI 服务器，用于运行 FastAPI
- **starlette** (>=0.40.0) - ASGI 工具包，FastAPI 的基础

### 数据验证
- **pydantic** (>=2.12.0) - 数据验证和设置管理
- **pydantic-settings** (>=2.8.0) - 基于 Pydantic 的配置管理

### 配置管理
- **python-dotenv** (>=1.0.0) - 从 .env 文件加载环境变量

### 数据存储
- **redis** (>=5.2.0) - Redis 客户端（支持异步）
  - 服务注册与发现
  - 配置缓存
  - 限流计数
  - 熔断器状态

### HTTP 客户端
- **httpx** (>=0.28.0) - 异步 HTTP 客户端
  - 服务健康检查
  - 反向代理请求转发
  - 支持 HTTP/2

### 服务发现
- **python-consul** (>=1.1.0) - Consul 客户端
  - 服务注册
  - 健康检查 TTL 更新
  - KV 存储（配置同步）

### 日志
- **loguru** (>=0.7.0) - 现代化日志库
  - 彩色输出
  - 自动轮转
  - 结构化日志

---

## 🧪 测试依赖（可选）

这些依赖仅用于开发和测试环境：

- **pytest** (>=7.4.0) - Python 测试框架
- **pytest-asyncio** (>=0.21.0) - 异步测试支持
- **requests** (>=2.31.0) - HTTP 客户端（用于集成测试）

安装测试依赖：
```bash
pip install pytest pytest-asyncio requests
```

---

## 📋 依赖分类

### 生产环境必需
```bash
pip install fastapi uvicorn starlette pydantic pydantic-settings \
            python-dotenv redis httpx python-consul loguru
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

### 开发环境额外
```bash
pip install pytest pytest-asyncio requests
```

---

## 🔍 依赖用途详解

### 1. 服务注册与发现
```python
# python-consul
from consul import Consul

consul = Consul(host='localhost', port=8500)
consul.agent.service.register(...)  # 注册服务
consul.agent.check.ttl_pass(...)     # 更新健康检查
```

### 2. Redis 缓存
```python
# redis (async)
from redis.asyncio import Redis

redis = Redis(host='localhost', port=6379, password='xxx')
await redis.set('key', 'value', ex=30)  # 服务实例（30秒TTL）
await redis.get('config:cors')           # 配置缓存
```

### 3. HTTP 代理
```python
# httpx
import httpx

client = httpx.AsyncClient()
response = await client.get('http://backend-service/api')  # 转发请求
```

### 4. 配置管理
```python
# pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    CONSUL_PORT: int = 8500
    
settings = Settings()  # 自动从 .env 加载
```

---

## ⚠️ 版本兼容性

| 依赖 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| Python | 3.10 | 3.11+ | 需要 async/await 支持 |
| FastAPI | 0.115.0 | 最新 | 稳定的异步支持 |
| Redis | 5.2.0 | 最新 | 需要 asyncio 支持 |
| Pydantic | 2.12.0 | 最新 | v2 API |
| python-consul | 1.1.0 | 最新 | 稳定版本 |

---

## 🔄 更新依赖

定期检查并更新依赖：

```bash
# 查看可更新的包
pip list --outdated

# 更新所有依赖
pip install --upgrade -r requirements.txt

# 更新单个依赖
pip install --upgrade fastapi
```

---

## 🐛 常见问题

### Q: 导入 consul 失败？
```bash
pip install python-consul
```

### Q: Redis 异步连接错误？
确保使用 `redis.asyncio` 而不是同步客户端：
```python
from redis.asyncio import Redis  # ✅ 正确
from redis import Redis          # ❌ 错误（同步）
```

### Q: httpx 超时？
检查网络连接和目标服务是否可达：
```python
client = httpx.AsyncClient(timeout=10.0)  # 设置超时时间
```

---

## 📝 依赖树

```
gateway/
├── FastAPI (Web 框架)
│   ├── Starlette (ASGI)
│   └── Pydantic (验证)
├── Uvicorn (服务器)
├── Redis (缓存/注册)
├── HTTPX (HTTP 客户端)
├── python-consul (服务发现)
├── python-dotenv (配置)
└── Loguru (日志)
```

---

## 🎯 最小化安装

如果只需要核心功能（不含测试）：

```bash
pip install fastapi uvicorn redis httpx python-consul loguru python-dotenv
```

完整安装（含测试）：

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio requests
```

---

**最后更新**: 2026-04-13  
**维护者**: Gateway Team
