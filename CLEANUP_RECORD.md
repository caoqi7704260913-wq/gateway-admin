# 服务清理记录

## 📅 清理时间
2026-04-13

---

## ✅ 清理完成项目

### 1. 服务停止

| 服务 | 端口 | PID | 状态 |
|------|------|-----|------|
| Gateway | 9000 | 16432 | ✅ 已停止 |
| Consul | 8500 | 9696 | ✅ 已停止 |

---

### 2. Redis 数据清理

**命令**:
```bash
D:\BtSoft\redis\redis-cli.exe -a 123123 FLUSHDB
```

**结果**:
- ✅ 数据库已清空
- ✅ Key 数量: 0

**清理的数据包括**:
- `config:cors` - CORS 配置
- `config:hmac:*` - HMAC 密钥
- `rate_limit:*` - 限流数据
- `hmac:nonce:*` - Nonce 防重放数据
- 所有其他测试数据

---

### 3. Consul 数据清理

**操作**:
```powershell
Remove-Item "d:\python_project\consul\data\*" -Recurse -Force
```

**清理的内容**:
- ✅ 服务注册信息
- ✅ KV 存储数据
- ✅ Raft 日志
- ✅ Serf 集群数据
- ✅ 健康检查状态

**目录状态**: 已清空

---

### 4. Gateway 本地缓存清理

**操作**:
```powershell
Remove-Item "d:\python_project\gateway\data\*" -Force
```

**清理的文件**:
- ✅ `config_cache.json` - 配置降级缓存
- ✅ `services_cache.json` - 服务发现降级缓存（如果存在）

**目录状态**: 已清空

---

### 5. Admin 数据检查

**状态**: ℹ️ Admin 项目没有 data 目录，无需清理

---

## 📊 清理总结

```
========== 清理结果总结 ==========

1. Gateway 服务:
   ✅ 已停止

2. Consul 服务:
   ✅ 已停止

3. Redis 数据:
   ✅ 已清空 (0 keys)

4. Consul 数据目录:
   ✅ 已清空

5. Gateway 缓存目录:
   ✅ 已清空

==================================
```

---

## 🔄 重新启动步骤

如果需要重新启动服务，请按以下顺序：

### 1. 启动 Redis
```bash
# Redis 应该已经在运行
redis-server --requirepass 123123
```

### 2. 启动 Consul
```bash
cd d:\python_project\consul
.\consul.exe agent -dev -data-dir="d:\python_project\consul\data"
```

### 3. 启动 Gateway
```bash
cd d:\python_project\gateway
python main.py
```

### 4. 启动 Admin（可选）
```bash
cd d:\python_project\admin
python -m app.main
```

---

## ⚠️ 注意事项

### 1. 数据不可恢复
- ❌ Redis 数据已永久删除
- ❌ Consul 数据已永久删除
- ❌ 本地缓存已永久删除

如需保留数据，请在清理前备份。

### 2. 服务依赖顺序
启动时必须按照以下顺序：
1. Redis
2. Consul
3. Gateway
4. Admin

### 3. 首次启动
清理后首次启动时：
- Gateway 会重新从 Consul 读取配置
- 如果没有配置，会使用默认值
- 本地缓存文件会自动创建

---

## 💡 建议

### 定期清理
建议定期清理测试数据：
```bash
# 每周清理一次
0 0 * * 0 redis-cli -a 123123 FLUSHDB
```

### 备份重要数据
清理前备份重要配置：
```bash
# 备份 Redis 数据
redis-cli -a 123123 BGSAVE

# 备份 Consul KV
consul kv export > consul_backup.json

# 备份 Gateway 缓存
Copy-Item "gateway\data\*" "backup\"
```

### 自动化脚本
可以创建自动化清理脚本：
```powershell
# cleanup.ps1
Write-Host "停止服务..."
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force
Get-Process | Where-Object {$_.ProcessName -like "*consul*"} | Stop-Process -Force

Write-Host "清理 Redis..."
D:\BtSoft\redis\redis-cli.exe -a 123123 FLUSHDB

Write-Host "清理 Consul..."
Remove-Item "d:\python_project\consul\data\*" -Recurse -Force

Write-Host "清理 Gateway 缓存..."
Remove-Item "d:\python_project\gateway\data\*" -Force

Write-Host "✅ 清理完成！"
```

---

## 📝 相关文档

- [Gateway 缓存目录说明](../gateway/docs/缓存目录说明.md)
- [Gateway 测试指南](../gateway/TESTING.md)
- [Admin 注册流程说明](../admin/docs/注册流程说明.md)

---

**清理完成！所有测试数据已清空。** 🎉
