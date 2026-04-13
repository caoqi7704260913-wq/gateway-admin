"""
操作审计中间件

记录所有敏感操作的日志，用于安全审计
"""
import json
import time
from typing import Optional, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from config.settings import settings
from app.utils.path_matcher import parse_public_paths, is_public_path


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    操作审计中间件
    
    记录以下信息：
    - 操作人（管理员 ID/用户名）
    - 操作时间
    - 请求方法、路径
    - 请求参数（脱敏）
    - 响应状态码
    - 客户端 IP
    """
    
    def __init__(self, app):
        super().__init__(app)
        # 从配置读取敏感路径
        self.sensitive_paths = parse_public_paths(settings.AUDIT_SENSITIVE_PATHS)
        logger.info(f"Audit sensitive paths loaded: {self.sensitive_paths}")
    
    # 需要脱敏的字段
    SENSITIVE_FIELDS = [
        "password",
        "secret",
        "token",
        "authorization",
    ]
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录审计日志"""
        
        start_time = time.time()
        
        # 执行请求
        response = await call_next(request)
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 判断是否需要审计
        if self._should_audit(request.url.path, request.method):
            await self._log_audit(request, response, duration)
        
        return response
    
    def _should_audit(self, path: str, method: str) -> bool:
        """
        判断是否需要审计
        
        审计条件：
        1. 路径匹配敏感路径（从配置读取，支持通配符）
        2. 方法是写操作（POST/PUT/DELETE/PATCH）
        """
        
        # 只审计写操作
        if method.upper() not in ["POST", "PUT", "DELETE", "PATCH"]:
            return False
        
        # 检查路径是否匹配敏感路径
        return is_public_path(path, self.sensitive_paths)
    
    async def _log_audit(self, request: Request, response, duration: float):
        """记录审计日志"""
        
        # 获取操作人信息
        caller_source = getattr(request.state, 'caller_source', 'unknown')
        caller_service = getattr(request.state, 'caller_service', 'unknown')
        
        # 如果是 Gateway 转发，尝试从 Header 中获取用户信息
        admin_username = "unknown"
        if caller_source == "gateway":
            # Gateway 可能会在 Header 中传递用户信息
            admin_username = request.headers.get("X-Admin-Username", "gateway_user")
        
        # 获取请求信息
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        # 获取请求参数（脱敏）
        try:
            if method in ["POST", "PUT", "PATCH"]:
                body = await request.json()
                sanitized_body = self._sanitize_data(body)
            else:
                sanitized_body = dict(request.query_params)
        except Exception:
            sanitized_body = {}
        
        # 构建审计日志
        audit_log = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "caller_source": caller_source,
            "caller_service": caller_service,
            "admin_username": admin_username,
            "action": f"{method} {path}",
            "client_ip": client_ip,
            "request_params": sanitized_body,
            "response_status": response.status_code,
            "duration_ms": round(duration * 1000, 2),
        }
        
        # 记录日志
        if response.status_code >= 400:
            logger.warning(f"⚠️ Audit Log (Failed): {json.dumps(audit_log, ensure_ascii=False)}")
        else:
            logger.info(f"📝 Audit Log: {json.dumps(audit_log, ensure_ascii=False)}")
        
        # TODO: 可以将审计日志写入数据库或发送到日志系统
        # await self._save_to_database(audit_log)
    
    def _sanitize_data(self, data: dict, level: int = 0) -> dict:
        """
        脱敏敏感数据
        
        Args:
            data: 原始数据
            level: 递归层级（防止无限递归）
        
        Returns:
            脱敏后的数据
        """
        
        if level > 3:  # 最多递归 3 层
            return {"__truncated__": True}
        
        sanitized = {}
        
        for key, value in data.items():
            # 检查是否是敏感字段
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            
            # 递归处理嵌套字典
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value, level + 1)
            
            # 递归处理列表中的字典
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item, level + 1) if isinstance(item, dict) else item
                    for item in value
                ]
            
            else:
                sanitized[key] = value
        
        return sanitized
