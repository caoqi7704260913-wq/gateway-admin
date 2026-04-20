"""
HTTP连接池模块
"""
import httpx
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential


class HttpxPool:
    """HTTP连接池"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def init(self):
        """初始化HTTP客户端"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        
    @property
    def client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if not self._client:
            raise RuntimeError("HttpxPool not initialized")
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """发送HTTP请求（带重试）"""
        return await self._client.request(method, url, **kwargs)
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """发送POST请求"""
        return await self._client.post(url, **kwargs)
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """发送GET请求"""
        return await self._client.get(url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """发送PUT请求"""
        return await self._client.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """发送DELETE请求"""
        return await self._client.delete(url, **kwargs)


httpx_pool = HttpxPool()
