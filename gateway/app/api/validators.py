"""
统一参数验证管理器

提供各类参数的验证方法，防止注入攻击和无效数据
"""

import re
from typing import Optional, List, Any
from fastapi import HTTPException

# ==================== 验证常量 ====================
MAX_NAME_LENGTH = 64
MAX_HOST_LENGTH = 128
MAX_ORIGIN_LENGTH = 256
MAX_SECRET_KEY_LENGTH = 256
MIN_PORT = 1
MAX_PORT = 65535
MIN_WEIGHT = 1
MAX_WEIGHT = 100

# ==================== 正则表达式 ====================
HOST_PATTERN = re.compile(
    r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    r'|^(\d{1,3}\.){3}\d{1,3}$'
)
IP_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
DOMAIN_PATTERN = re.compile(
    r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
)
URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
APP_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')
SERVICE_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
HTTP_METHOD_PATTERN = re.compile(r'^[A-Z]{1,16}$')
HEADER_PATTERN = re.compile(r'^[a-zA-Z0-9-]+$')


class ValidationError(Exception):
    """验证错误"""
    def __init__(self, message: str, field: str = ""):
        self.message = message
        self.field = field
        super().__init__(message)


class RequestValidator:
    """请求参数验证器"""

    @staticmethod
    def validate_service_name(name: str, field: str = "name") -> str:
        """验证服务名称"""
        if not name:
            raise HTTPException(status_code=400, detail=f"{field}: 不能为空")
        if len(name) > MAX_NAME_LENGTH:
            raise HTTPException(status_code=400, detail=f"{field}: 长度不能超过{MAX_NAME_LENGTH}个字符")
        if not SERVICE_NAME_PATTERN.match(name):
            raise HTTPException(status_code=400, detail=f"{field}: 必须以字母开头，只能包含字母、数字、下划线和连字符")
        return name

    @staticmethod
    def validate_host(host: str, field: str = "host") -> str:
        """验证主机地址（域名或IP）"""
        if not host:
            raise HTTPException(status_code=400, detail=f"{field}: 不能为空")
        if len(host) > MAX_HOST_LENGTH:
            raise HTTPException(status_code=400, detail=f"{field}: 长度不能超过{MAX_HOST_LENGTH}个字符")
        if not HOST_PATTERN.match(host):
            raise HTTPException(status_code=400, detail=f"{field}: 格式无效，请输入有效的域名或IP地址")
        return host

    @staticmethod
    def validate_port(port: int, field: str = "port") -> int:
        """验证端口号"""
        if not MIN_PORT <= port <= MAX_PORT:
            raise HTTPException(status_code=400, detail=f"{field}: 端口号必须在{MIN_PORT}-{MAX_PORT}之间")
        return port

    @staticmethod
    def validate_weight(weight: int, field: str = "weight") -> int:
        """验证权重"""
        if not MIN_WEIGHT <= weight <= MAX_WEIGHT:
            raise HTTPException(status_code=400, detail=f"{field}: 权重必须在{MIN_WEIGHT}-{MAX_WEIGHT}之间")
        return weight

    @staticmethod
    def validate_url(url: Optional[str], field: str = "url") -> Optional[str]:
        """验证URL"""
        if url is None:
            return url
        if len(url) > MAX_HOST_LENGTH * 2:
            raise HTTPException(status_code=400, detail=f"{field}: URL过长")
        if not URL_PATTERN.match(url):
            raise HTTPException(status_code=400, detail=f"{field}: URL格式无效")
        return url

    @staticmethod
    def validate_app_id(app_id: str, field: str = "app_id") -> str:
        """验证App ID"""
        if not app_id:
            raise HTTPException(status_code=400, detail=f"{field}: 不能为空")
        if not APP_ID_PATTERN.match(app_id):
            raise HTTPException(status_code=400, detail=f"{field}: 只能包含字母、数字、下划线和连字符，长度1-32")
        return app_id

    @staticmethod
    def validate_secret_key(key: Optional[str], field: str = "secret_key", min_len: int = 16) -> Optional[str]:
        """验证密钥"""
        if key is None:
            return key
        if len(key) < min_len:
            raise HTTPException(status_code=400, detail=f"{field}: 长度至少{min_len}个字符")
        if len(key) > MAX_SECRET_KEY_LENGTH:
            raise HTTPException(status_code=400, detail=f"{field}: 长度不能超过{MAX_SECRET_KEY_LENGTH}个字符")
        return key

    @staticmethod
    def validate_cors_origin(origin: str, field: str = "origin") -> str:
        """验证CORS源"""
        if not origin:
            raise HTTPException(status_code=400, detail=f"{field}: 不能为空")
        if len(origin) > MAX_ORIGIN_LENGTH:
            raise HTTPException(status_code=400, detail=f"{field}: 长度不能超过{MAX_ORIGIN_LENGTH}个字符")
        if not URL_PATTERN.match(origin):
            raise HTTPException(status_code=400, detail=f"{field}: URL格式无效")
        return origin

    @staticmethod
    def validate_http_method(method: str, field: str = "method") -> str:
        """验证HTTP方法"""
        method = method.upper()
        if not HTTP_METHOD_PATTERN.match(method):
            raise HTTPException(status_code=400, detail=f"{field}: 无效的HTTP方法")
        valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'}
        if method not in valid_methods:
            raise HTTPException(status_code=400, detail=f"{field}: 不支持的HTTP方法: {method}")
        return method

    @staticmethod
    def validate_header_name(header: str, field: str = "header") -> str:
        """验证请求头名称"""
        if len(header) > 64:
            raise HTTPException(status_code=400, detail=f"{field}: 名称过长")
        if not HEADER_PATTERN.match(header):
            raise HTTPException(status_code=400, detail=f"{field}: 格式无效，只能包含字母、数字和连字符")
        return header.title()

    @staticmethod
    def validate_cors_origins(origins: List[str], field: str = "origins") -> List[str]:
        """验证CORS源列表"""
        if not origins:
            raise HTTPException(status_code=400, detail=f"{field}: 至少需要配置一个允许的源")
        validated = [RequestValidator.validate_cors_origin(o, f"{field}[{i}]") for i, o in enumerate(origins)]
        return list(set(validated))  # 去重

    @staticmethod
    def validate_cors_methods(methods: List[str], field: str = "methods") -> List[str]:
        """验证CORS方法列表"""
        if not methods:
            raise HTTPException(status_code=400, detail=f"{field}: 至少需要配置一个允许的方法")
        validated = [RequestValidator.validate_http_method(m, f"{field}[{i}]") for i, m in enumerate(methods)]
        return validated

    @staticmethod
    def validate_cors_headers(headers: List[str], field: str = "headers") -> List[str]:
        """验证CORS请求头列表"""
        if not headers:
            raise HTTPException(status_code=400, detail=f"{field}: 至少需要配置一个允许的请求头")
        validated = [RequestValidator.validate_header_name(h, f"{field}[{i}]") for i, h in enumerate(headers)]
        return validated

    @staticmethod
    def validate_service_id(service_id: str, field: str = "service_id") -> str:
        """验证服务ID"""
        if not service_id:
            raise HTTPException(status_code=400, detail=f"{field}: 不能为空")
        if len(service_id) > MAX_NAME_LENGTH:
            raise HTTPException(status_code=400, detail=f"{field}: 长度不能超过{MAX_NAME_LENGTH}个字符")
        return service_id


# 导出单例
validator = RequestValidator()
