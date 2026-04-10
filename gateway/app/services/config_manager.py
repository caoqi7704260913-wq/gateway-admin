"""
配置管理器

集中管理 HMAC 密钥和 CORS 配置到 Redis 和 Consul
"""

import json
import secrets
from typing import Optional, Dict, Any, List
from loguru import logger

from app.utils.redis_manager import get_redis_manager
from config import settings


class ConfigManager:
    """配置管理器"""

    # Redis key 前缀
    HMAC_KEY_PREFIX = "config:hmac:"
    CORS_CONFIG_KEY = "config:cors"
    GLOBAL_CONFIG_KEY = "config:global"

    # Consul KV key 前缀
    CONSUL_KV_PREFIX = "gateway/config/"

    def __init__(self):
        self.redis = get_redis_manager()
        self._consul_enabled = settings.CONSUL_ENABLED
        self._consul_client = None
        if self._consul_enabled:
            self._init_consul()

    def _init_consul(self):
        """初始化 Consul 连接"""
        try:
            import consul
            self._consul_client = consul.Consul(
                host=settings.CONSUL_HOST,
                port=settings.CONSUL_PORT,
                token=settings.CONSUL_TOKEN,
                scheme=settings.CONSUL_SCHEME,
                verify=settings.CONSUL_VERIFY
            )
            logger.info(f"ConfigManager 已连接 Consul: {settings.CONSUL_HOST}:{settings.CONSUL_PORT}")
        except Exception as e:
            logger.error(f"Consul 连接失败: {e}")
            self._consul_enabled = False
            self._consul_client = None

    # ==================== HMAC 密钥管理 ====================

    async def create_hmac_key(self, app_id: str, secret_key: Optional[str] = None) -> str:
        """
        创建或更新 HMAC 密钥（同步到 Redis 和 Consul）

        Args:
            app_id: 应用标识
            secret_key: 密钥（不提供则自动生成）

        Returns:
            密钥
        """
        if secret_key is None:
            secret_key = secrets.token_urlsafe(32)

        key = f"{self.HMAC_KEY_PREFIX}{app_id}"
        await self.redis.set(key, secret_key)

        # 同步到 Consul KV
        if self._consul_enabled and self._consul_client:
            try:
                consul_key = f"{self.CONSUL_KV_PREFIX}hmac/{app_id}"
                self._consul_client.kv.put(consul_key, secret_key)
            except Exception as e:
                logger.error(f"HMAC 密钥同步到 Consul 失败: {e}")

        logger.info(f"HMAC密钥已创建/更新: {app_id}")
        return secret_key

    async def get_hmac_key(self, app_id: str) -> Optional[str]:
        """
        获取 HMAC 密钥

        Args:
            app_id: 应用标识

        Returns:
            密钥，不存在返回 None
        """
        key = f"{self.HMAC_KEY_PREFIX}{app_id}"
        return await self.redis.get(key)

    async def delete_hmac_key(self, app_id: str) -> bool:
        """
        删除 HMAC 密钥

        Args:
            app_id: 应用标识

        Returns:
            是否删除成功
        """
        key = f"{self.HMAC_KEY_PREFIX}{app_id}"
        return await self.redis.delete(key)

    async def list_hmac_keys(self) -> List[str]:
        """
        获取所有 HMAC 密钥的 app_id 列表

        Returns:
            app_id 列表
        """
        pattern = f"{self.HMAC_KEY_PREFIX}*"
        keys = await self.redis.keys(pattern)
        prefix_len = len(self.HMAC_KEY_PREFIX)
        return [k[prefix_len:] for k in keys if k]

    # ==================== CORS 配置管理 ====================

    async def set_cors_config(self, config: Dict[str, Any]) -> bool:
        """
        设置 CORS 配置（同步到 Redis 和 Consul）

        Args:
            config: CORS 配置字典
                {
                    "origins": ["http://localhost:9527"],
                    "credentials": True,
                    "methods": ["GET", "POST"],
                    "headers": ["Authorization"]
                }

        Returns:
            是否设置成功
        """
        await self.redis.set(self.CORS_CONFIG_KEY, json.dumps(config))

        # 同步到 Consul KV
        if self._consul_enabled and self._consul_client:
            try:
                consul_key = f"{self.CONSUL_KV_PREFIX}cors"
                self._consul_client.kv.put(consul_key, json.dumps(config))
                logger.info("CORS配置已同步到 Consul")
            except Exception as e:
                logger.error(f"Consul KV 同步失败: {e}")

        logger.info("CORS配置已更新")
        return True

    async def get_cors_config(self) -> Optional[Dict[str, Any]]:
        """
        获取 CORS 配置（优先从 Consul 读取）

        Returns:
            CORS 配置字典，不存在返回 None
        """
        # 优先从 Consul 读取
        if self._consul_enabled and self._consul_client:
            try:
                consul_key = f"{self.CONSUL_KV_PREFIX}cors"
                _, data = self._consul_client.kv.get(consul_key)
                if data and data.get('Value'):
                    value = data['Value'].decode('utf-8') if isinstance(data['Value'], bytes) else data['Value']
                    logger.debug("CORS配置从 Consul 读取")
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"从 Consul 读取 CORS 配置失败: {e}")

        # 回退到 Redis
        data = await self.redis.get(self.CORS_CONFIG_KEY)
        if data:
            return json.loads(data)
        return None

    async def update_cors_origins(self, origins: List[str]) -> bool:
        """
        更新 CORS 允许的源

        Args:
            origins: 源列表

        Returns:
            是否更新成功
        """
        config = await self.get_cors_config() or {}
        config["origins"] = origins
        return await self.set_cors_config(config)

    async def add_cors_origin(self, origin: str) -> bool:
        """
        添加 CORS 允许的源

        Args:
            origin: 源

        Returns:
            是否添加成功
        """
        config = await self.get_cors_config() or {"origins": []}
        if origin not in config["origins"]:
            config["origins"].append(origin)
        return await self.set_cors_config(config)

    async def remove_cors_origin(self, origin: str) -> bool:
        """
        移除 CORS 允许的源

        Args:
            origin: 源

        Returns:
            是否移除成功
        """
        config = await self.get_cors_config() or {"origins": []}
        if origin in config["origins"]:
            config["origins"].remove(origin)
        return await self.set_cors_config(config)

    # ==================== 全局配置管理 ====================

    async def set_global_config(self, key: str, value: Any) -> bool:
        """
        设置全局配置

        Args:
            key: 配置键
            value: 配置值

        Returns:
            是否设置成功
        """
        config = await self.get_global_config()
        config[key] = value
        await self.redis.set(self.GLOBAL_CONFIG_KEY, json.dumps(config))
        return True

    async def get_global_config(self, key: Optional[str] = None) -> Any:
        """
        获取全局配置

        Args:
            key: 配置键，不提供则返回全部

        Returns:
            配置值
        """
        data = await self.redis.get(self.GLOBAL_CONFIG_KEY)
        config = json.loads(data) if data else {}

        if key is None:
            return config
        return config.get(key)

    async def delete_global_config(self, key: str) -> bool:
        """
        删除全局配置

        Args:
            key: 配置键

        Returns:
            是否删除成功
        """
        config = await self.get_global_config()
        if key in config:
            del config[key]
            await self.redis.set(self.GLOBAL_CONFIG_KEY, json.dumps(config))
            return True
        return False

    # ==================== 初始化默认配置 ====================

    async def init_default_cors(self, origins: Optional[List[str]] = None) -> bool:
        """
        初始化默认 CORS 配置

        Args:
            origins: 默认源列表

        Returns:
            是否初始化成功
        """
        if origins is None:
            origins = ["http://localhost:9527", "http://127.0.0.1:9527"]

        default_config = {
            "origins": origins,
            "credentials": True,
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "headers": ["Authorization", "Content-Type", "X-Requested-With", "X-Signature", "X-Timestamp", "X-Nonce"]
        }
        return await self.set_cors_config(default_config)

    # ==================== 启动时初始化 ====================

    async def load_configs(self) -> None:
        """
        启动时加载所有配置到内存

        从 Redis 加载 CORS 配置和 HMAC 密钥到内存缓存
        """
        from app.middleware.dynamic_cors import update_cors_cache

        logger.info("正在加载配置...")

        # 加载 CORS 配置
        cors_config = await self.get_cors_config()
        if cors_config:
            update_cors_cache(cors_config)
            logger.info(f"CORS 配置已加载: {len(cors_config.get('origins', []))} 个源")
        else:
            # 使用默认配置
            await self.init_default_cors()
            cors_config = await self.get_cors_config()
            if cors_config:
                update_cors_cache(cors_config)
            logger.info("CORS 使用默认配置")

        # 加载 HMAC 密钥
        hmac_keys = await self.list_hmac_keys()
        logger.info(f"HMAC 密钥已加载: {len(hmac_keys)} 个")

        # 启动 Consul 监听
        if self._consul_enabled and self._consul_client:
            self._start_consul_watch()

        logger.info("配置加载完成")

    # ==================== Consul 监听（配置热更新） ====================

    def _start_consul_watch(self):
        """启动 Consul 监听，监听配置变化"""
        import threading

        def watch_configs():
            client = self._consul_client
            if client is None:
                return
            try:
                logger.info("Consul 配置监听已启动")
                index = None
                while True:
                    try:
                        if index:
                            _, data = client.kv.get(
                                f"{self.CONSUL_KV_PREFIX}cors",
                                wait="10s",
                                index=index
                            )
                        else:
                            _, data = client.kv.get(
                                f"{self.CONSUL_KV_PREFIX}cors",
                                wait="10s"
                            )

                        if data:
                            index = data.get('ModifyIndex')
                            if data.get('Value'):
                                value = data['Value'].decode('utf-8') if isinstance(data['Value'], bytes) else data['Value']
                                new_config = json.loads(value)
                                from app.middleware.dynamic_cors import update_cors_cache
                                update_cors_cache(new_config)
                                logger.info("CORS 配置已从 Consul 监听更新")
                    except Exception as e:
                        logger.warning(f"Consul 监听异常: {e}")
                        import time
                        time.sleep(5)
            except Exception as e:
                logger.error(f"Consul 监听线程异常: {e}")

        thread = threading.Thread(target=watch_configs, daemon=True)
        thread.start()
        logger.info("Consul 配置监听线程已启动")


# 全局实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
