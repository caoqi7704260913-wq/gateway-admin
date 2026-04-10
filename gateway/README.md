# Gateway API

基于 FastAPI 的高性能 API 网关，提供服务注册发现、负载均衡、请求路由、安全认证等功能。

## 技术栈

- **框架**: FastAPI 0.135.3
- **ASGI 服务器**: Uvicorn 0.44.0
- **数据验证**: Pydantic 2.12.5
- **缓存/存储**: Redis 5.2.1
- **配置管理**: Pydantic Settings

## 功能模块

### 1. 服务注册与发现

内部服务启动时注册到 Gateway，Gateway 自动维护服务实例列表。

| 文件 | 说明 |
|------|------|
| `app/services/discovery.py` | 服务发现核心逻辑 |
| `app/api/routes.py` | 服务注册/注销 API |

**API 端点:**
```
POST   /api/services/register           # 注册服务
DELETE /api/services/{service_name}    # 注销服务
GET    /api/services/{service_name}    # 获取服务列表
GET    /api/services/{service_name}/{service_id}  # 获取指定服务
```

### 2. 健康检查

Gateway 定时检查已注册服务的健康状态，自动注销不健康的服务实例。

| 文件 | 说明 |
|------|------|
| `app/services/health_checker.py` | 健康检查器 |

**特性:**
- TCP 连接检查
- HTTP 健康检查
- 自动刷新 TTL
- 不健康时自动注销

### 3. 负载均衡

支持多种负载均衡策略，自动选择健康的服务实例。

| 文件 | 说明 |
|------|------|
| `app/services/load_balancer.py` | 负载均衡器 |

**策略:**
- `weighted_round_robin` - 加权轮询（默认）
- `round_robin` - 普通轮询
- `random` - 随机选择

### 4. 请求路由转发

将外部请求透明转发到后端服务，支持请求/响应修改。

| 文件 | 说明 |
|------|------|
| `app/services/router.py` | 请求路由器 |
| `app/utils/httpx_manager.py` | HTTP 客户端管理 |

### 5. HMAC 签名验证

防止请求被篡改，所有外部请求必须携带 HMAC 签名。

| 文件 | 说明 |
|------|------|
| `app/middleware/hmac_middleware.py` | HMAC 中间件 |
| `app/utils/hmac_validator.py` | HMAC 验证工具 |

**请求头:**
```
X-Signature: HMAC-SHA256签名
X-Timestamp: 时间戳（秒）
X-Nonce: 随机字符串
```

### 6. 动态 CORS

支持运行时更新 CORS 配置，无需重启服务。

| 文件 | 说明 |
|------|------|
| `app/middleware/dynamic_cors.py` | 动态 CORS 中间件 |
| `app/services/config_manager.py` | 配置管理器 |

**API 端点:**
```
GET    /api/config/cors              # 获取 CORS 配置
PUT    /api/config/cors              # 更新 CORS 配置
POST   /api/config/cors/origins     # 添加 CORS 源
DELETE /api/config/cors/origins      # 移除 CORS 源
```

### 7. 限流

基于滑动窗口算法的请求限流，保护后端服务。

| 文件 | 说明 |
|------|------|
| `app/middleware/rate_limiter.py` | 限流中间件 |

**配置:**
- 默认每分钟 100 次请求
- 按客户端 IP 限流
- 支持自定义策略

**响应头:**
```
X-RateLimit-Limit: 最大请求数
X-RateLimit-Remaining: 剩余请求数
X-RateLimit-Reset: 重置时间戳
```

### 8. HMAC 密钥管理

集中管理内部服务的 HMAC 密钥。

| 文件 | 说明 |
|------|------|
| `app/services/config_manager.py` | 配置管理器 |

**API 端点:**
```
POST   /api/config/hmac/key          # 创建密钥
GET    /api/config/hmac/key/{app_id} # 获取密钥
DELETE /api/config/hmac/key/{app_id} # 删除密钥
GET    /api/config/hmac/keys        # 列出所有应用
```

## 项目结构

```
gateway/
├── app/
│   ├── api/
│   │   └── routes.py              # API 路由
│   ├── middleware/
│   │   ├── hmac_middleware.py     # HMAC 验证
│   │   ├── dynamic_cors.py       # 动态 CORS
│   │   └── rate_limiter.py       # 限流
│   ├── models/
│   │   └── service.py            # 服务数据模型
│   ├── services/
│   │   ├── discovery.py          # 服务发现
│   │   ├── health_checker.py     # 健康检查
│   │   ├── load_balancer.py      # 负载均衡
│   │   ├── router.py             # 请求路由
│   │   └── config_manager.py     # 配置管理
│   └── utils/
│       ├── redis_manager.py      # Redis 管理器
│       └── httpx_manager.py      # HTTP 客户端
├── config/
│   ├── __init__.py
│   └── settings.py               # 配置管理
├── main.py                       # 应用入口
├── requirements.txt              # 依赖
└── .env                         # 环境变量
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

修改 `.env` 文件：

```env
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=123123

# 服务端口
PORT=8000

# CORS 允许的源
CORS_ORIGINS=["http://localhost:9527"]
```

### 3. 启动服务

```bash
python main.py
```

### 4. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 配置说明

### 应用配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 应用名称 | Gateway API |
| `APP_VERSION` | 版本号 | 1.0.0 |
| `DEBUG` | 调试模式 | True |

### 服务器配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST` | 监听地址 | 0.0.0.0 |
| `PORT` | 监听端口 | 8000 |

### Redis 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `REDIS_HOST` | Redis 地址 | localhost |
| `REDIS_PORT` | Redis 端口 | 6379 |
| `REDIS_PASSWORD` | 密码 | 123123 |
| `REDIS_TTL` | 服务心跳过期时间 | 30秒 |

### HMAC 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HMAC_SECRET_KEY` | 默认密钥 | - |
| `HMAC_ENABLED` | 是否启用 | True |
| `HMAC_TIMESTAMP_TOLERANCE` | 时间戳容差 | 300秒 |

### 限流配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `max_requests` | 最大请求数 | 100 |
| `window_seconds` | 时间窗口 | 60秒 |

## Redis 数据结构

```
# 服务注册
service:{name}:{id}           -> JSON 服务信息
service:healthy:{name}       -> 有序集合，健康服务

# HMAC 密钥
config:hmac:{app_id}         -> 密钥

# CORS 配置
config:cors                  -> JSON 配置

# 全局配置
config:global                -> JSON 配置
```

## 注意事项

1. `.env` 文件包含敏感信息，不要提交到版本控制
2. 生产环境请修改 `HMAC_SECRET_KEY`
3. Redis 连接信息根据实际环境配置
