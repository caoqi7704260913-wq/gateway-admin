"""
HTTP 客户端管理器
"""
import httpx
from typing import Optional


class HttpClientManager:
    """HTTP 客户端管理器"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def init(self):
        """初始化客户端"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    @property
    def client(self) -> httpx.AsyncClient:
        """获取客户端"""
        if self._client is None:
            raise RuntimeError("HTTP client not initialized")
        return self._client
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get(self, url: str, **kwargs):
        """GET 请求"""
        return await self.client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs):
        """POST 请求"""
        return await self.client.post(url, **kwargs)
    
    async def put(self, url: str, **kwargs):
        """PUT 请求"""
        return await self.client.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs):
        """DELETE 请求"""
        return await self.client.delete(url, **kwargs)


http_client = HttpClientManager()
