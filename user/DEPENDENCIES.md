# User 服务依赖说明

本文档详细说明 User 用户服务的所有依赖及其用途。

## 📦 核心依赖

### Web 框架
- **fastapi** (>=0.115.0) - 高性能异步 Web 框架
- **uvicorn[standard]** (>=0.30.0) - ASGI 服务器（含标准额外依赖）
- **starlette** (>=0.40.0) - ASGI 工具包，FastAPI 的基础

### 数据验证
- **pydantic** (>=2.12.0) - 数据验证和设置管理（v2）
- **pydantic-settings** (>=2.8.0) - 基于 Pydantic 的配置管理

### 配置管理
- **python-dotenv** (>=1.0.0) - 从 .env 文件加载环境变量

### 数据库
- **sqlmodel** (>=0.0.14) - SQL 数据库 ORM（基于 SQLAlchemy + Pydantic）
- **pymysql** (>=1.1.0) - MySQL 同步驱动
- **aiomysql** (>=0.2.0) - MySQL 异步驱动

### Redis
- **redis** (>=5.2.0) - Redis 客户端（支持异步）
  - Token 存储
  - HMAC Key 存储
  - CORS 配置缓存
  - 限流计数
  - 服务注册信息

### HTTP 客户端
- **httpx** (>=0.28.0) - 异步 HTTP 客户端
  - Gateway 服务注册（POST /api/services/register）
  - Gateway 服务注销（DELETE /api/services/unregister）
  - 健康检查端点探测

### 密码加密
- **passlib[bcrypt]** (>=1.7.4) - 密码哈希库
  - bcrypt 算法
  - 用户密码加密

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

安装测试依赖：
```bash
pip install pytest pytest-asyncio
```

---

## 📋 依赖分类

### 生产环境必需
```bash
pip install fastapi uvicorn[standard] starlette pydantic pydantic-settings \
            python-dotenv sqlmodel pymysql aiomysql redis httpx \
            passlib[bcrypt] loguru
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

### 开发环境额外
```bash
pip install pytest pytest-asyncio
```

---

## 🔍 依赖用途详解

### 1. 数据库 ORM
```python
# sqlmodel
from sqlmodel import SQLModel, Field, Session, create_engine

class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    username: str = Field(unique=True)
    password_hash: str
    
# 异步引擎
from aiomysql import create_pool
engine = create_async_engine("mysql+aiomysql://...")
```

### 2. Redis 缓存
```python
# redis (async)
from redis.asyncio import Redis

redis = Redis(host='localhost', port=6379, password='xxx')
await redis.set('config:hmac:user-service', 'secret_key')  # HMAC Key
await redis.get('config:cors')                                # CORS 配置
```

### 3. 密码加密
```python
# passlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed = pwd_context.hash("plain_password")  # 加密
verified = pwd_context.verify("password", hashed)  # 验证
```

### 4. HTTP 客户端
```python
# httpx - 用于与 Gateway 通信
from app.utils.http_client import http_client

# 服务注册
response = await http_client.post(
    "http://gateway:9000/api/services/register",
    json=service_data
)

# 服务注销
response = await http_client.delete(
    f"http://gateway:9000/api/services/unregister/{service_id}"
)
```

### 5. 配置管理
```python
# pydantic-settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_HOST: str = "localhost"
    SERVICE_NAME: str = "user-service"
    
settings = Settings()  # 自动从 .env 加载
```

---

## ⚠️ 版本兼容性

| 依赖 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| Python | 3.10 | 3.11+ | 需要 async/await 支持 |
| FastAPI | 0.115.0 | 最新 | 稳定的异步支持 |
| Pydantic | 2.12.0 | 最新 | v2 API（不兼容 v1） |
| SQLModel | 0.0.14 | 最新 | 基于 Pydantic v2 |
| Redis | 5.2.0 | 最新 | 需要 asyncio 支持 |
| aiomysql | 0.2.0 | 最新 | 异步 MySQL 驱动 |

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

### Q: bcrypt 导入错误？
确保安装了 passlib 的 bcrypt 额外依赖：
```bash
pip install passlib[bcrypt]
```

### Q: aiomysql 连接失败？
检查 MySQL 服务是否运行，以及连接字符串格式：
```python
DATABASE_URL = "mysql+aiomysql://user:pass@localhost:3306/dbname"
```

### Q: Redis 异步连接错误？
确保使用 `redis.asyncio` 而不是同步客户端：
```python
from redis.asyncio import Redis  # ✅ 正确
from redis import Redis          # ❌ 错误（同步）
```

### Q: SQLModel 表未创建？
确保在创建表之前导入了所有模型：
```python
from app.models.schemas import User, Profile  # 先导入
await db_manager.create_tables_async()  # 再创建表
```

---

## 📝 依赖树

```
user/
├── FastAPI (Web 框架)
│   ├── Starlette (ASGI)
│   └── Pydantic (验证)
├── Uvicorn (服务器)
├── SQLModel (ORM)
│   ├── SQLAlchemy
│   └── Pydantic
├── aiomysql (异步 MySQL)
├── pymysql (同步 MySQL)
├── Redis (缓存/配置)
├── HTTPX (HTTP 客户端)
├── passlib (密码加密)
│   └── bcrypt
├── python-dotenv (配置)
└── Loguru (日志)
```

---

## 🎯 最小化安装

如果只需要核心功能（不含测试）：

```bash
pip install fastapi uvicorn[standard] sqlmodel aiomysql redis httpx passlib[bcrypt] loguru python-dotenv
```

完整安装（含测试）：

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

---

## 📊 依赖对比

### 与 Admin 的差异

| 依赖 | User | Admin | 说明 |
|------|------|-------|------|
| SQLModel | ✅ | ✅ | 都需要数据库 |
| aiomysql | ✅ | ✅ | 都需要 MySQL |
| passlib | ✅ | ✅ | 都需要密码加密 |
| httpx | ✅ | ✅ | 都需要注册服务 |

### 共同依赖

- FastAPI, Uvicorn, Starlette
- Pydantic, pydantic-settings
- python-dotenv
- redis
- httpx
- loguru

---

**最后更新**: 2026-04-17  
**维护者**: User Team
