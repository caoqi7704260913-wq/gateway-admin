# 后台管理服务 (Admin Service)

基于 FastAPI 的后台管理服务，提供管理员、角色、权限、菜单等管理功能。

## 技术栈

- FastAPI - Web 框架
- SQLModel - ORM
- MySQL - 数据库
- Redis - Token 存储
- passlib - 密码哈希

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env` 并修改配置：

```env
DATABASE_URL=mysql+pymysql://admin:123123@localhost:3306/admin
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=123123
```

### 3. 初始化数据库

```bash
python init_db.py
```

默认管理员：`admin` / `123456`

### 4. 启动服务

```bash
python -m uvicorn app.main:app --reload --port 8001
```

或直接运行：

```bash
python app/main.py
```

## 服务功能

### 表结构

| 表名 | 说明 |
|:---|:---|
| admins | 管理员表 |
| roles | 角色表 |
| permissions | 权限表 |
| admin_roles | 管理员角色关联表 |
| role_permissions | 角色权限关联表 |
| menus | 菜单表 |
| tokens | Token 表 |

### API 接口

#### 认证

- `POST /api/v1/auth/login` - 登录
- `POST /api/v1/auth/logout` - 登出

#### CORS 配置

- `GET /api/v1/config/cors` - 获取 CORS 配置
- `POST /api/v1/config/cors` - 设置 CORS 配置

#### HMAC 配置

- `GET /api/v1/config/hmac` - 获取所有 HMAC Keys
- `POST /api/v1/config/hmac` - 设置 HMAC Key
- `DELETE /api/v1/config/hmac/{app_id}` - 删除 HMAC Key

### CORS 和 HMAC 配置存储

CORS 和 HMAC Key 配置存储在 Redis 中：

- `config:cors` - CORS 配置
- `config:hmac:{app_id}` - HMAC 密钥

### 服务注册

Admin 服务启动时自动注册到 Gateway，支持服务发现。

## 目录结构

```
admin/
├── app/
│   ├── __init__.py
│   ├── main.py           # 应用入口
│   ├── database.py       # 数据库初始化
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py     # API 路由
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py    # 数据模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── token_service.py
│   │   ├── config_service.py
│   │   ├── password_service.py
│   │   └── register_service.py
│   └── utils/
│       ├── __init__.py
│       └── redis_manager.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── tests/
│   └── unit/
├── docs/
│   └── 工程提示词.md
├── .env
├── .env.example
├── requirements.txt
├── init_db.py
└── README.md
```
