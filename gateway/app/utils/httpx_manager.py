"""
HTTP 客户端管理器

提供全局唯一的 HTTPX 异步客户端实例，统一管理连接池和生命周期
"""
import httpx
import asyncio
import threading
from typing import Optional, Dict, Any, List, Tuple, Union, cast
from loguru import logger
import time

from config import settings
from app.utils.redis_manager import get_redis_manager


class HTTPClientManager:
    """HTTP 客户端管理器（单例模式）"""
    
    _client: Optional[httpx.AsyncClient] = None
    _lock: threading.Lock = threading.Lock()
    
    # 线程安全的 metrics 访问
    _metrics: Dict[str, Any] = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "total_response_time": 0.0,
        "average_response_time": 0.0,
        "active_connections": 0,
        "connection_pool_size": 0
    }
    _metrics_lock: threading.Lock = threading.Lock()
    
    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """
        获取全局 HTTP 客户端实例（线程安全）
        
        Returns:
            httpx.AsyncClient: 全局唯一的客户端实例
        """
        if cls._client is None:
            with cls._lock:
                # 双重检查锁定模式
                if cls._client is None:
                    # 创建连接池配置
                    limits = httpx.Limits(
                        max_keepalive_connections=min(settings.HTTP_MAX_KEEPALIVE, 10),
                        max_connections=min(settings.HTTP_MAX_CONNECTIONS, 20)
                    )
                    
                    # 创建超时配置
                    timeout = httpx.Timeout(
                        connect=settings.HTTP_CONNECT_TIMEOUT,
                        read=settings.HTTP_READ_TIMEOUT,
                        write=settings.HTTP_WRITE_TIMEOUT,
                        pool=settings.HTTP_POOL_TIMEOUT
                    )
                    
                    # 创建客户端实例
                    http2_enabled = getattr(settings, 'HTTP_HTTP2_ENABLED', False)
                    cls._client = httpx.AsyncClient(
                        limits=limits,
                        timeout=timeout,
                        follow_redirects=False,  # 默认不自动跟随重定向
                        http2=http2_enabled,
                        trust_env=True  # 信任环境变量中的代理设置
                    )
                    
                    # 更新连接池大小指标
                    with cls._metrics_lock:
                        cls._metrics["connection_pool_size"] = settings.HTTP_MAX_CONNECTIONS
                    
                    logger.info(
                        f"HTTP 客户端初始化成功 - "
                        f"Max Connections: {settings.HTTP_MAX_CONNECTIONS}, "
                        f"Max Keepalive: {settings.HTTP_MAX_KEEPALIVE}, "
                        f"HTTP/2: {http2_enabled}"
                    )
        
        return cls._client
    
    @classmethod
    async def close(cls) -> None:
        """
        关闭 HTTP 客户端
        
        在应用关闭时调用，释放所有连接资源
        """
        with cls._lock:
            if cls._client is not None:
                await cls._client.aclose()
                cls._client = None
                logger.info("HTTP 客户端已关闭")
    
    @classmethod
    async def health_check(cls) -> bool:
        """
        健康检查
        
        Returns:
            bool: 客户端是否可用
        """
        if cls._client is None:
            return False
        
        try:
            # 检查客户端是否已关闭
            if cls._client.is_closed:
                logger.warning("HTTP 客户端已关闭")
                return False
            return True
        except Exception as e:
            logger.error(f"HTTP 客户端健康检查失败：{e}")
            return False
    
    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        """
        获取 HTTP 客户端指标
        
        Returns:
            Dict[str, Any]: 客户端指标
        """
        return cls._metrics
    
    @classmethod
    def update_metrics(cls, successful: bool, response_time: float):
        """
        更新 HTTP 客户端指标（线程安全）
        
        Args:
            successful: 请求是否成功
            response_time: 响应时间（秒）
        """
        with cls._metrics_lock:
            cls._metrics["total_requests"] += 1
            if successful:
                cls._metrics["successful_requests"] += 1
            else:
                cls._metrics["failed_requests"] += 1
            cls._metrics["total_response_time"] += response_time
            if cls._metrics["total_requests"] > 0:
                cls._metrics["average_response_time"] = (
                    cls._metrics["total_response_time"] / cls._metrics["total_requests"]
                )
    
    @classmethod
    async def request_with_retry(
        cls,
        method: str,
        url: str,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        **kwargs
    ) -> httpx.Response:
        """
        带重试的请求
        
        Args:
            method: 请求方法
            url: 请求 URL
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            **kwargs: 其他请求参数
        
        Returns:
            httpx.Response: 响应对象
        """
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                client = cls.get_client()
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()  # 触发 HTTP 错误
                
                # 更新指标
                response_time = time.time() - start_time
                cls.update_metrics(True, response_time)
                
                return response
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                if attempt == max_retries - 1:
                    # 最后一次尝试失败
                    response_time = time.time() - start_time
                    cls.update_metrics(False, response_time)
                    logger.error(f"HTTP 请求失败：{method} {url}, 错误：{e}")
                    raise
                
                # 重试
                logger.warning(
                    f"HTTP 请求失败，重试 {attempt+1}/{max_retries}：{method} {url}, 错误：{e}"
                )
                await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
        
        # 理论上不会到达这里，但为了类型提示添加
        raise httpx.RequestError("All retry attempts failed")
    
    @classmethod
    async def get_with_cache(
        cls,
        url: str,
        cache_key: Optional[str] = None,
        cache_ttl: int = 60,
        **kwargs
    ) -> httpx.Response:
        """
        带缓存的 GET 请求
        
        Args:
            url: 请求 URL
            cache_key: 缓存键（默认为 URL）
            cache_ttl: 缓存过期时间（秒）
            **kwargs: 其他请求参数
        
        Returns:
            httpx.Response: 响应对象
        """
        import json
        
        # 获取 Redis 管理器实例
        redis = get_redis_manager()
        
        # 生成缓存键
        if not cache_key:
            cache_key = f"http_cache:{url}"
        
        # 尝试从缓存获取
        cached_response = await redis.get(cache_key)
        if cached_response:
            try:
                # 解析缓存的响应
                cached_data = json.loads(cached_response)
                # ✅ 正确构造 httpx.Response
                response = httpx.Response(
                    status_code=cached_data["status_code"],
                    content=cached_data["content"].encode() if isinstance(cached_data["content"], str) else cached_data["content"],
                    headers=cached_data["headers"],
                    request=httpx.Request("GET", url),
                    extensions={"http_version": b"HTTP/1.1"}
                )
                return response
            except Exception as e:
                logger.warning(f"解析缓存响应失败：{e}")
        
        # 缓存未命中，发送请求
        response = await cls.request_with_retry("GET", url, **kwargs)
        
        # 缓存响应
        try:
            cache_data = {
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers)
            }
            await redis.set(cache_key, json.dumps(cache_data), ex=cache_ttl)
        except Exception as e:
            logger.warning(f"缓存响应失败：{e}")
        
        return response
    
    @classmethod
    async def batch_requests(
        cls,
        requests: List[Tuple[str, str, Dict[str, Any]]]
    ) -> List[Union[httpx.Response, Exception]]:
        """
        批量请求
        
        Args:
            requests: 请求列表，每个元素为 (method, url, kwargs)
        
        Returns:
            List[Union[httpx.Response, Exception]]: 响应列表，可能包含异常对象
        """
        tasks = []
        
        for method, url, kwargs in requests:
            task = asyncio.create_task(
                cls.request_with_retry(method, url, **kwargs)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 记录失败的请求
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                method, url, _ = requests[i]
                logger.error(f"批量请求 [{method} {url}] 失败：{result}")
        
        # 类型断言：asyncio.gather 返回 list[BaseException | T]，但我们期望 list[Response | Exception]
        return cast(List[Union[httpx.Response, Exception]], results)


# 便捷的模块级函数
def get_http_client() -> httpx.AsyncClient:
    """获取全局 HTTP 客户端实例"""
    return HTTPClientManager.get_client()


async def close_http_client() -> None:
    """关闭 HTTP 客户端"""
    await HTTPClientManager.close()


async def request_with_retry(
    method: str,
    url: str,
    max_retries: int = 3,
    retry_delay: float = 0.5,
    **kwargs
) -> httpx.Response:
    """带重试的请求"""
    return await HTTPClientManager.request_with_retry(
        method, url, max_retries, retry_delay, **kwargs
    )


async def get_with_cache(
    url: str,
    cache_key: Optional[str] = None,
    cache_ttl: int = 60,
    **kwargs
) -> httpx.Response:
    """带缓存的 GET 请求"""
    return await HTTPClientManager.get_with_cache(
        url, cache_key, cache_ttl, **kwargs
    )


async def batch_requests(
    requests: List[Tuple[str, str, Dict[str, Any]]]
) -> List[Union[httpx.Response, Exception]]:
    """批量请求"""
    return await HTTPClientManager.batch_requests(requests)

