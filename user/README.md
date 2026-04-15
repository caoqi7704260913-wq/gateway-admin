# User Service

用户服务 - 基于 FastAPI 的微服务

## 🚀 快速开始

### 1. 激活虚拟环境

```bash
# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 4. 启动服务

```bash
python -m app.main
```

服务将在 `http://localhost:8002` 启动

---

## 📁 项目结构

```
user/
├── app/
│   ├── api/          # API 路由
│   ├── models/       # 数据模型
│   ├── services/     # 业务逻辑
│   ├── utils/        # 工具函数
│   └── main.py       # 应用入口
├── config/           # 配置文件
├── tests/            # 测试文件
├── .env              # 环境变量
├── requirements.txt  # 依赖列表
└── README.md         # 说明文档
```

---

## 🔧 技术栈

- **Web 框架**: FastAPI
- **数据库**: MySQL (SQLModel + aiomysql)
- **缓存**: Redis
- **服务发现**: Gateway 注册
- **日志**: Loguru

---

## 📝 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

---

## 🧪 运行测试

```bash
pytest tests/ -v
```

---

**最后更新**: 2026-04-13
