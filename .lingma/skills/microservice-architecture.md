# 微服务架构开发规范

## 📋 概述

本 Skill 定义了基于 FastAPI 的微服务架构系统的核心开发规范，包括 API Gateway 模式、HMAC 签名验证、服务发现等关键设计决策。所有新功能的开发都必须遵循这些规范。

---

## 🏗️ 架构核心原则

### 1. API Gateway 模式

**原则**：所有外部请求必须通过 Gateway 转发，后端服务不直接暴露给外网。

**实现要求**：
- ✅ Gateway 作为唯一入口（端口 9000）
- ✅ 后端服务（Admin/User）只监听内网端口
- ✅ Gateway 负责统一认证、限流、路由转发

**禁止**：
- ❌ 后端服务直接暴露公网 IP
- ❌ 客户端绕过 Gateway 直接调用后端服务

---

### 2. HMAC 签名验证机制

#### 2.1 双层验证架构

**外部请求流程**：
```
Client (Gateway 密钥签名) 
  → Gateway (验证客户端签名) 
  → Gateway (使用目标服务密钥重新签名) 
  → Backend Service (验证 Gateway 签名)
```

**关键规则**：
1. **前端只使用 Gateway 的 HMAC Key**
   - 前端配置：`HMAC_KEY = {gateway_key}`
   - 所有请求（包括登录）都需要签名

2. **Gateway 转发时使用目标服务的密钥签名**
   ```python
   # Gateway 转发逻辑
   hmac_key = await redis.get(f"config:hmac:{target_service_name}")
   signature = generate_hmac(message, hmac_key)
   headers["X-Signature"] = signature
   headers["X-Forwarded-By"] = "gateway"
   ```

3. **后端服务使用自己的密钥验证**
   ```python
   # Admin Service 验证逻辑
   current_service_name = settings.SERVICE_NAME  # "admin-service"
   hmac_key = await redis.get(f"config:hmac:{current_service_name}")
   is_valid = verify_hmac(signature, message, hmac_key)
   ```

#### 2.2 密钥管理

**存储策略**：
- **主存储**：Redis (`config:hmac:{service_name}`)
- **降级存储**：Consul KV (`config/hmac/{service_name}`)
- **双写策略**：写入时同时写入 Redis 和 Consul

**密钥分配**：
| 服务 | 密钥用途 | 谁持有 |
|------|---------|--------|
| Gateway | 验证客户端签名 | 前端、Gateway |
| Admin Service | 验证 Gateway 签名 | Gateway、Admin |
| User Service | 验证 Gateway 签名 | Gateway、User |

**重要原则**：
- ✅ **对称加密**：发送方和接收方使用同一个密钥
- ✅ **密钥隔离**：每个服务有独立的密钥
- ✅ **前端只用 Gateway 密钥**：前端不需要知道后端服务的密钥

#### 2.3 签名算法

**签名字符串格式**：
```
{HTTP_METHOD}\n{PATH}\n{TIMESTAMP}\n{BODY}
```

**生成示例**：
```python
import hmac
import hashlib
import time

def generate_signature(method: str, path: str, body: str, secret_key: str):
    timestamp = str(int(time.time()))
    message = f"{method}\n{path}\n{timestamp}\n{body}"
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature, timestamp
```

**验证要求**：
- ✅ 时间戳容忍度：300 秒（5分钟）
- ✅ 使用 `hmac.compare_digest()` 进行恒定时间比较
- ✅ Body 必须包含在签名中

---

### 3. API 路由规范

**原则**：统一的路由命名规则，Gateway 不做路径转换。

**路由格式**：
```
/{service-name}/api/{version}/{resource}
```

**示例**：
- Admin 服务：`/admin/api/auth/login`
- User 服务：`/user/api/users/profile`
- Order 服务：`/order/api/orders/list`

**Gateway 转发规则**：
1. 提取第一段作为服务名（如 `/admin/...` → `admin-service`）
2. 去掉服务名前缀，剩余路径直接转发
3. **不做任何路径转换或重写**

**前端调用**：
```typescript
// ✅ 正确：完整的服务路由
axios.get('/admin/api/auth/login')
axios.get('/user/api/users/profile')

// ❌ 错误：省略服务名
axios.get('/api/auth/login')
```

**后端服务配置**：
```python
# Admin Service main.py
app.include_router(api_router, prefix="/api")
# 实际路由：/api/auth/login
# Gateway 转发：/admin/api/auth/login → /api/auth/login ✅
```

**优势**：
- ✅ 统一规范，易于理解
- ✅ Gateway 无硬编码逻辑
- ✅ 支持多版本 API（v1, v2...）
- ✅ 服务间调用路径清晰

---

### 4. 服务发现与注册

#### 4.1 3级缓存策略

**查询优先级**：
1. **本地缓存**（最快，TTL: 60秒）
2. **Redis**（主要来源，`service:{name}:{instance_id}`）
3. **Consul**（降级方案，Redis 故障时使用）

**实现要求**：
```python
async def get_service_instances(service_name: str):
    # 1. 检查本地缓存
    if service_name in local_cache and not cache_expired:
        return local_cache[service_name]
    
    # 2. 查询 Redis
    try:
        instances = await redis.get_service_instances(service_name)
        if instances:
            local_cache[service_name] = instances
            return instances
    except Exception as e:
        logger.warning(f"Redis query failed: {e}")
    
    # 3. 降级到 Consul
    try:
        instances = consul.get_service_instances(service_name)
        if instances:
            local_cache[service_name] = instances
            return instances
    except Exception as e:
        logger.error(f"Consul query failed: {e}")
    
    raise ServiceUnavailableError(service_name)
```

#### 4.2 服务注册

**注册流程**：
1. 生成固定服务 ID（MD5: name+ip+port）
2. 注册到 Gateway API（`/api/services/register`）
3. Gateway 清理旧实例
4. 存储到 Redis（TTL: 30秒）
5. 启动 HealthChecker（每10秒刷新 TTL）

**健康检查**：
- Gateway 主动探测后端服务的 `/healthz` 端点
- 每 10 秒刷新一次 Redis TTL
- TTL 过期自动剔除不健康实例

---

### 5. 零信任安全策略

**原则**：所有内部服务调用都必须验证来源

**验证逻辑**：
```python
# Admin Service 中间件
forwarded_by = request.headers.get("X-Forwarded-By")

if forwarded_by == "gateway":
    # Gateway 转发的请求：验证 HMAC 签名
    current_service_name = settings.SERVICE_NAME
    if verify_hmac_signature(request, current_service_name):
        return True  # ✅ 签名验证通过
    else:
        return False  # ❌ 签名无效

# 其他服务直接调用
service_name = request.headers.get("X-Service-Name")
if service_name and service_name in registered_services:
    if verify_hmac_signature(request, service_name):
        return True  # ✅ 已注册服务且签名有效

return False  # ❌ 拒绝访问
```

**registered_services 来源**：
1. 优先从 Redis 读取 `service:*:*` 键
2. 降级从 Consul 读取服务列表
3. 本地缓存 60 秒 TTL

---

### 6. 多层防护体系

**Admin 服务安全防护（6层）**：

1. **Gateway HMAC 验证** - 验证客户端请求签名
2. **内部通信 HMAC 验证** ⭐ - Gateway 使用目标服务密钥重新签名
3. **来源验证** - ServiceSourceAuthMiddleware 验证 X-Forwarded-By
4. **操作审计** - AuditLogMiddleware 记录敏感操作
5. **限流保护** - RateLimiterMiddleware 防止滥用
6. **网络隔离** - Admin 不暴露外网

---

## 🔧 开发规范

### 0. 禁止硬编码原则（最高优先级）

**核心原则**：所有配置、路径、密钥、服务名等必须通过配置文件或环境变量管理，严禁在代码中硬编码。

**禁止硬编码的内容**：
- ❌ 服务名称、IP 地址、端口号
- ❌ HMAC 密钥、密码、Token
- ❌ API 路径、路由规则
- ❌ 数据库连接字符串
- ❌ Redis/Consul 配置
- ❌ CORS 源列表
- ❌ 超时时间、重试次数等业务参数

**正确做法**：
```python
# ✅ 从配置文件读取
from config import settings
service_name = settings.SERVICE_NAME
hmac_key = await redis.get(f"config:hmac:{service_name}")

# ❌ 硬编码
service_name = "admin-service"
hmac_key = "hardcoded-key-12345"
```

**例外情况**：
- 单元测试中的 Mock 数据
- 示例代码中的占位符（需明确标注）

**违规后果**：
- 降低代码可维护性
- 增加安全风险（密钥泄露）
- 阻碍多环境部署（开发/测试/生产）

---

### 1. 新增后端服务

**必须实现的组件**：

1. **服务注册**
   ```python
   from app.services.register_service import ServiceRegister
   
   register = ServiceRegister(
       service_name="my-service",
       host="localhost",
       port=8003,
       health_endpoint="/healthz"
   )
   await register.register()
   ```

2. **健康检查端点**
   ```python
   @app.get("/healthz")
   async def health_check():
       return {"status": "healthy"}
   ```

3. **HMAC 密钥配置**
   - 启动时检查 Redis 中是否有 `config:hmac:{service_name}`
   - 如果没有，自动生成并存储

4. **服务认证中间件**
   ```python
   from app.middleware.service_auth import ServiceSourceAuthMiddleware
   
   app.add_middleware(ServiceSourceAuthMiddleware)
   ```

---

### 2. 前端集成规范

**HMAC 签名配置**：
```typescript
// frontend/src/api/request.ts
const HMAC_CONFIG = {
  key: '{gateway_hmac_key}', // 只使用 Gateway 密钥
  tolerance: 300,
}

function generateHmacSignature(method: string, path: string, body: any) {
  const timestamp = Math.floor(Date.now() / 1000).toString()
  const bodyStr = body ? JSON.stringify(body) : ''
  const message = `${method}\n${path}\n${timestamp}\n${bodyStr}`
  
  const signature = CryptoJS.HmacSHA256(message, HMAC_CONFIG.key)
    .toString(CryptoJS.enc.Hex)
  
  return { signature, timestamp }
}

// Axios 拦截器
apiClient.interceptors.request.use(config => {
  const { signature, timestamp } = generateHmacSignature(
    config.method!.toUpperCase(),
    config.url!,
    config.data
  )
  
  config.headers['X-Signature'] = signature
  config.headers['X-Timestamp'] = timestamp
  
  return config
})
```

**重要提示**：
- ✅ 所有请求（包括登录/注册）都需要 HMAC 签名
- ✅ 只使用 Gateway 的 HMAC Key
- ❌ 不要在代码中硬编码密钥，使用环境变量

---

### 3. 密钥管理操作

**生成独立密钥**：
```bash
cd gateway
python setup_independent_hmac.py
```

**清理所有密钥**：
```bash
cd gateway
python cleanup_hmac_keys.py
```

**获取 Gateway 密钥（供前端使用）**：
```bash
cd gateway
python get_hmac_key.py
```

---

## ⚠️ 常见错误与避免方法

### 错误 1：Gateway 使用错误的密钥签名

**错误做法**：
```python
# ❌ Gateway 使用自己的密钥签名
hmac_key = await redis.get("config:hmac:gateway")
```

**正确做法**：
```python
# ✅ Gateway 使用目标服务的密钥签名
hmac_key = await redis.get(f"config:hmac:{target_service_name}")
```

---

### 错误 2：后端服务使用硬编码的服务名验证

**错误做法**：
```python
# ❌ Admin 硬编码使用 "gateway" 验证
self._verify_hmac_signature(request, "gateway")
```

**正确做法**：
```python
# ✅ Admin 使用配置的服务名验证
current_service_name = settings.SERVICE_NAME  # "admin-service"
self._verify_hmac_signature(request, current_service_name)
```

---

### 错误 3：前端使用后端服务的密钥

**错误做法**：
```typescript
// ❌ 前端使用 Admin 服务的密钥
const HMAC_KEY = 'admin-service-key'
```

**正确做法**：
```typescript
// ✅ 前端只使用 Gateway 的密钥
const HMAC_KEY = 'gateway-key'
```

---

### 错误 4：忘记添加 X-Forwarded-By 头

**错误做法**：
```python
# ❌ Gateway 转发时未添加来源标识
headers["X-Signature"] = signature
```

**正确做法**：
```python
# ✅ Gateway 必须添加来源标识
headers["X-Forwarded-By"] = "gateway"
headers["X-Signature"] = signature
```

---

## 📊 监控与告警

### 关键指标

**需要监控的指标**：
- HMAC 验证失败次数（可能表示攻击）
- 时间戳过期请求数量（可能表示时钟不同步）
- 密钥读取失败次数（Redis/Consul 故障）
- 服务注册/注销频率
- 健康检查成功率

### 告警阈值

- HMAC 验证失败率 > 5% → **立即告警**
- 密钥读取失败 > 3次/分钟 → **警告**
- 服务健康检查失败率 > 10% → **警告**
- Redis/Consul 连接失败 → **立即告警**

---

## 📚 参考文档

- [架构设计文档](../docs/架构设计文档.md)
- [HMAC 密钥管理策略](../docs/HMAC密钥降级策略.md)
- [内部服务 HMAC 签名验证](../docs/内部服务HMAC签名验证.md)
- [Request_Response 对比指南](../docs/Request_Response对比指南.md)

---

## 🔄 版本历史

- **v1.0** (2026-04-13) - 初始版本，定义核心架构规范
  - 双层 HMAC 验证机制
  - Redis + Consul 双写策略
  - 3级缓存服务发现
  - 零信任安全策略

---

**使用说明**：在进行任何微服务相关的开发时，AI 助手必须严格遵循本 Skill 定义的规范，确保架构的一致性和安全性。
