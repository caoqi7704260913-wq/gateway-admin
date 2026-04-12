"""
请求路由转发模块

核心功能：
- 路由匹配（根据路径转发到对应服务）
- 负载均衡选择后端
- 请求转发
- 熔断保护
"""

from typing import Optional,Any
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from loguru import logger
from config import settings
from app.services.discovery import get_service_discovery
from app.services.load_balancer import get_load_balancer
from app.services.circuit_breaker import get_circuit_breaker, CircuitOpenError
from app.utils.httpx_manager import get_http_client


class Router:
    """请求路由器"""

    def __init__(self):
        self.discovery = get_service_discovery()
        self.load_balancer = get_load_balancer()
        self.http_client = get_http_client()
        self.circuit_breakers: dict[str, Any] = {}  # 按服务名的熔断器

    def _get_circuit_breaker(self, service_name: str):
        """获取服务的熔断器"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = get_circuit_breaker(
                name=f"service:{service_name}",
                failure_threshold=5,
                success_threshold=2,
                timeout=30
            )
        return self.circuit_breakers[service_name]
    
    async def route(self, request: Request) -> Response:
        """
        路由转发请求
        
        Args:
            request: 原始请求
        
        Returns:
            后端服务响应
        """
        path = request.url.path
        
        # 1. 解析路由：path -> service_name
        service_name = self._match_route(path)
        if not service_name:
            return JSONResponse(
                status_code=404,
                content={"error": "Route not found", "path": path}
            )
        
        # 2. 获取健康的后端服务
        backends = await self.discovery.get_healthy_services(service_name)
        if not backends:
            logger.warning(f"No healthy backend for service: {service_name}")
            return JSONResponse(
                status_code=503,
                content={"error": "Service unavailable", "service": service_name}
            )

        # 3. 负载均衡选择后端
        backend = await self.load_balancer.select(backends)
        if not backend:
            return JSONResponse(
                status_code=503,
                content={"error": "No backend available"}
            )

        # 4. 转发请求（带熔断保护）
        return await self._forward(request, backend, service_name)
    
    def _match_route(self, path: str) -> Optional[str]:
        """
        路径匹配：提取服务名称
        
        规则：/service-name/path -> service-name
        例如：/user/api/v1 -> user
        
        Args:
            path: 请求路径
        
        Returns:
            服务名称，未匹配返回 None
        """
        # 去掉开头的 /
        path = path.lstrip("/")
        
        # 第一段作为服务名
        parts = path.split("/")
        if parts and parts[0]:
            return parts[0]
        
        return None
    
    async def _forward(self, request: Request, backend, service_name: str) -> Response:
        """
        转发请求到后端（带熔断保护）

        Args:
            request: 原始请求
            backend: 选中的后端服务
            service_name: 服务名称

        Returns:
            后端响应
        """
        cb = self._get_circuit_breaker(service_name)

        try:
            return await cb.execute(self._do_forward, request, backend)
        except CircuitOpenError:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service temporarily unavailable",
                    "service": service_name,
                    "circuit_state": "open"
                }
            )
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return JSONResponse(
                status_code=502,
                content={"error": "Bad gateway", "detail": str(e)}
            )

    async def _do_forward(self, request: Request, backend) -> Response:
        """
        执行请求转发

        Args:
            request: 原始请求
            backend: 选中的后端服务

        Returns:
            后端响应
        """
        # 构建目标 URL（正确处理路径）
        base_url = backend.url.rstrip("/")
        path = request.url.path.lstrip("/")
        remaining_path = "/".join(path.split("/")[1:]) if "/" in path else ""
        
        # 避免双斜杠
        if remaining_path:
            target_url = f"{base_url}/{remaining_path}"
        else:
            target_url = base_url

        # 构建请求头
        headers = dict(request.headers)
        headers["X-Forwarded-For"] = request.client.host if request.client else ""
        headers["X-Forwarded-Host"] = request.headers.get("host", "")
        headers["X-Forwarded-Proto"] = request.url.scheme
        headers.pop("host", None)
        headers.pop("content-length", None)

        try:
            body = await request.body()

            response = await self.http_client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                timeout=settings.REQUEST_TIMEOUT
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        except TimeoutError:
            logger.error(f"Request timeout: {target_url}")
            raise  # 让熔断器记录失败

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise  # 让熔断器记录失败


# 单例实例
_router: Optional[Router] = None


def get_router() -> Router:
    """获取路由器单例"""
    global _router
    if _router is None:
        _router = Router()
    return _router
