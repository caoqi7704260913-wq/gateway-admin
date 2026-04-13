"""
路径匹配工具

支持通配符匹配，用于公开路径白名单验证
"""
import fnmatch
from typing import List


def is_public_path(path: str, public_patterns: List[str]) -> bool:
    """
    判断路径是否匹配公开路径模式
    
    Args:
        path: 请求路径（如 /api/auth/login）
        public_patterns: 公开路径模式列表（支持通配符 *）
    
    Returns:
        是否匹配
    
    Examples:
        >>> is_public_path("/api/auth/login", ["/api/auth/*"])
        True
        >>> is_public_path("/api/admins", ["/api/auth/*"])
        False
        >>> is_public_path("/healthz", ["/healthz", "/docs"])
        True
    """
    for pattern in public_patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def parse_public_paths(config_string: str) -> List[str]:
    """
    解析配置字符串为路径列表
    
    Args:
        config_string: 逗号分隔的路径字符串
    
    Returns:
        路径列表
    
    Examples:
        >>> parse_public_paths("/healthz,/docs,/api/auth/*")
        ['/healthz', '/docs', '/api/auth/*']
    """
    if not config_string:
        return []
    
    return [path.strip() for path in config_string.split(",") if path.strip()]
