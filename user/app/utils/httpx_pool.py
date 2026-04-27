"""
HTTP连接池模块（单例模式 + 自动懒加载）
"""
import httpx
import asyncio
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential


class HttpxPool:
    """HTTP连接池（单例）"""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（自动懒加载 + 线程安全）"""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(10.0),
                        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                    )
        return self._client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """发送HTTP请求（带重试）"""
        client = await self.get_client()
        return await client.request(method, url, **kwargs)
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """发送POST请求"""
        client = await self.get_client()
        return await client.post(url, **kwargs)
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """发送GET请求"""
        client = await self.get_client()
        return await client.get(url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """发送PUT请求"""
        client = await self.get_client()
        return await client.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """发送DELETE请求"""
        client = await self.get_client()
        return await client.delete(url, **kwargs)


httpx_pool = HttpxPool()


def get_httpx_pool() -> HttpxPool:
    """获取 HTTPX 连接池单例"""
    return httpx_pool

