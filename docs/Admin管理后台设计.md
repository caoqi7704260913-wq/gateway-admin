# Admin 管理后台

Gateway 的可视化管理系统。

## 技术选型

- **前端**: vue-element-admin (Vue 2 + Element UI)
- **后端**: Admin 服务作为内部服务注册到 Gateway

## 架构设计

```
浏览器(9528/9529) 
       ↓
    Gateway(8000) → Admin 服务(内部) → 调用其他内部服务
```

## 前端项目

### 获取 vue-element-admin

```bash
# 克隆项目
git clone https://github.com/PanJiaChen/vue-element-admin.git

# 进入目录
cd vue-element-admin

# 安装依赖
npm install

# 本地开发
npm run dev
```

### 修改 API 配置

文件: `vue-element-admin/src/utils/request.js`

```javascript
import service from './service'

// 创建 axios 实例
const service = axios.create({
  baseURL: process.env.VUE_APP_BASE_API || 'http://localhost:8000',
  timeout: 30000
})
```

文件: `vue-element-admin/src/api/gateway.js` (新建)

```javascript
import request from '@/utils/request'

export function getServices(serviceName) {
  return request({
    url: `/api/services/${serviceName}`,
    method: 'get'
  })
}

export function getCorsConfig() {
  return request({
    url: '/api/config/cors',
    method: 'get'
  })
}

export function updateCorsConfig(data) {
  return request({
    url: '/api/config/cors',
    method: 'put',
    data
  })
}

export function getCircuitBreakers() {
  return request({
    url: '/api/circuit-breakers',
    method: 'get'
  })
}

export function resetCircuitBreaker(name) {
  return request({
    url: `/api/circuit-breakers/${name}/reset`,
    method: 'post'
  })
}

export function getHmacKeys() {
  return request({
    url: '/api/config/hmac/keys',
    method: 'get'
  })
}

export function createHmacKey(appId) {
  return request({
    url: '/api/config/hmac/key',
    method: 'post',
    data: { app_id: appId }
  })
}

export function deleteHmacKey(appId) {
  return request({
    url: `/api/config/hmac/key/${appId}`,
    method: 'delete'
  })
}
```

## 功能模块

### 1. 服务管理

| 功能 | API | 说明 |
|------|-----|------|
| 服务列表 | GET /api/services/{name} | 查看已注册服务 |
| 服务详情 | GET /api/services/{name}/{id} | 查看指定服务 |
| 注销服务 | DELETE /api/services/{name} | 移除服务 |

### 2. CORS 配置

| 功能 | API | 说明 |
|------|-----|------|
| 查看配置 | GET /api/config/cors | 获取当前 CORS |
| 更新配置 | PUT /api/config/cors | 修改 CORS |
| 添加源 | POST /api/config/cors/origins | 添加允许的源 |
| 移除源 | DELETE /api/config/cors/origins | 移除源 |

### 3. HMAC 密钥

| 功能 | API | 说明 |
|------|-----|------|
| 创建密钥 | POST /api/config/hmac/key | 生成新密钥 |
| 查看密钥 | GET /api/config/hmac/key/{app_id} | 获取密钥 |
| 删除密钥 | DELETE /api/config/hmac/key/{app_id} | 删除密钥 |
| 密钥列表 | GET /api/config/hmac/keys | 所有应用 |

### 4. 熔断器

| 功能 | API | 说明 |
|------|-----|------|
| 熔断器列表 | GET /api/circuit-breakers | 查看所有熔断器 |
| 熔断器详情 | GET /api/circuit-breakers/{name} | 查看指定熔断器 |
| 重置熔断器 | POST /api/circuit-breakers/{name}/reset | 手动重置 |

## 页面布局建议

```
├── Dashboard (首页/概览)
├── 服务管理
│   ├── 服务列表
│   └── 服务详情
├── 配置管理
│   ├── CORS 配置
│   └── HMAC 密钥
├── 熔断器
│   └── 熔断器状态
└── 设置
    └── Gateway 配置
```

## 开发计划

### Phase 1: 前端搭建
- [ ] 克隆 vue-element-admin
- [ ] 修改 API 基础配置
- [ ] 创建 Gateway API 模块
- [ ] 登录页面（可选，简单验证）

### Phase 2: 页面开发
- [ ] 服务列表页面
- [ ] CORS 配置页面
- [ ] HMAC 密钥管理页面
- [ ] 熔断器状态页面

### Phase 3: 集成测试
- [ ] 前端请求 Gateway API
- [ ] HMAC 签名集成
- [ ] CORS 配置测试

## 注意事项

1. **CORS 配置**: 前端开发环境需添加到 CORS 允许列表
2. **HMAC 签名**: Admin 作为内部服务，也需要 HMAC 签名
3. **端口规划**: 
   - Gateway: 8000
   - 前端: 9528/9529
   - Admin 后端: 内部服务

## 相关文档

- [Gateway 功能模块说明](../gateway/docs/功能模块说明.md)
- [vue-element-admin 官方文档](https://panjiachen.github.io/vue-element-admin-site/)
