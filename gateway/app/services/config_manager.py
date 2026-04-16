"""
配置管理器

集中管理 HMAC 密钥和 CORS 配置到 Redis
支持降级策略：Redis → 本地缓存
"""

import json
import os
import secrets
from typing import Optional, Dict, Any, List

from loguru import logger

from app.utils.redis_manager import get_redis_manager
from config import settings
from config.settings import BASE_DIR


class ConfigManager:
    """配置管理器"""

    # Redis key 前缀
    HMAC_KEY_PREFIX = "config:hmac:"
    CORS_CONFIG_KEY = "config:cors"
    GLOBAL_CONFIG_KEY = "config:global"

    def __init__(self):
        self.redis = get_redis_manager()
        
        # 本地缓存
        self._cache_file = os.path.join(BASE_DIR, "data", "config_cache.json")
        self._local_cache: Dict[str, Any] = {}
        
        # 加载本地缓存
        self._load_local_cache()


    def _load_local_cache(self):
        """加载本地缓存"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    self._local_cache = json.load(f)
                    logger.info(f"已加载 {len(self._local_cache)} 个配置项到本地缓存")
        except Exception as e:
            logger.warning(f"加载本地配置缓存失败: {e}")
            self._local_cache = {}

    def _save_local_cache(self):
        """保存本地缓存"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self._local_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存本地配置缓存失败: {e}")

    def _cache_get(self, key: str) -> Optional[str]:
        """从本地缓存获取"""
        return self._local_cache.get(key)

    def _cache_set(self, key: str, value: str):
        """设置到本地缓存"""
        self._local_cache[key] = value
        self._save_local_cache()

    # ==================== HMAC 密钥管理 ====================

    async def create_hmac_key(self, app_id: str, secret_key: Optional[str] = None) -> str:
        """
        创建或更新 HMAC 密钥（同步到 Redis 和本地缓存）

        Args:
            app_id: 应用标识
            secret_key: 密钥（不提供则自动生成）

        Returns:
            密钥
        """
        if secret_key is None:
            secret_key = secrets.token_urlsafe(32)

        key = f"{self.HMAC_KEY_PREFIX}{app_id}"
        
        # 1. 保存到 Redis
        try:
            await self.redis.set(key, secret_key)
        except Exception as e:
            logger.error(f"HMAC 密钥保存到 Redis 失败: {e}")
        
        # 2. 同步到本地缓存（始终执行，作为兜底）
        self._cache_set(key, secret_key)

        logger.info(f"HMAC密钥已创建/更新: {app_id}")
        return secret_key

    async def get_hmac_key(self, app_id: str) -> Optional[str]:
        """
        获取 HMAC 密钥（降级策略：Redis → 本地缓存）

        Args:
            app_id: 应用标识

        Returns:
            密钥，不存在返回 None
        """
        key = f"{self.HMAC_KEY_PREFIX}{app_id}"
        
        # 1. 优先从 Redis 获取
        try:
            value = await self.redis.get(key)
            if value:
                # 保存到本地缓存
                self._cache_set(key, value)
                return value
        except Exception as e:
            logger.error(f"从 Redis 获取 HMAC 密钥失败: {e}")
        
        # 2. 从本地缓存获取
        logger.warning(f"HMAC 密钥降级到本地缓存: {app_id}")
        return self._cache_get(key)

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
        设置 CORS 配置（同步到 Redis 和本地缓存）

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
        config_json = json.dumps(config)
        
        # 1. 保存到 Redis
        try:
            await self.redis.set(self.CORS_CONFIG_KEY, config_json)
            logger.info("CORS配置已保存到 Redis")
        except Exception as e:
            logger.error(f"CORS 配置保存到 Redis 失败: {e}")
        
        # 2. 同步到本地缓存（始终执行，作为兜底）
        self._cache_set(self.CORS_CONFIG_KEY, config_json)

        logger.info("CORS配置已更新")
        return True

    async def get_cors_config(self) -> Optional[Dict[str, Any]]:
        """
        获取 CORS 配置（降级策略：Redis → 本地缓存）

        Returns:
            CORS 配置字典，不存在返回 None
        """
        # 1. 从 Redis 获取
        try:
            data = await self.redis.get(self.CORS_CONFIG_KEY)
            if data:
                # 保存到本地缓存
                self._cache_set(self.CORS_CONFIG_KEY, data)
                return json.loads(data)
        except Exception as e:
            logger.error(f"从 Redis 获取 CORS 配置失败: {e}")
        
        # 2. 从本地缓存获取
        logger.warning("CORS 配置降级到本地缓存")
        cached = self._cache_get(self.CORS_CONFIG_KEY)
        if cached:
            config = json.loads(cached)
            # 同步到 Redis
            try:
                await self.redis.set(self.CORS_CONFIG_KEY, cached)
                logger.info("CORS 配置已从本地缓存同步到 Redis")
            except Exception as e:
                logger.error(f"CORS 配置同步到 Redis 失败: {e}")
            return config
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
            origins: 默认源列表（不提供则从 .env 读取）

        Returns:
            是否初始化成功
        """
        if origins is None:
            # 从环境变量读取 CORS_ORIGINS 配置
            from config.settings import settings
            origins = settings.CORS_ORIGINS
            logger.info(f"使用 .env 中的 CORS_ORIGINS: {origins}")

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
            # 使用默认配置并强制写入 Redis
            logger.info("Redis 中无 CORS 配置，正在初始化默认配置...")
            await self.init_default_cors()
            cors_config = await self.get_cors_config()
            if cors_config:
                update_cors_cache(cors_config)
                logger.info(f"默认 CORS 配置已加载并同步: {len(cors_config.get('origins', []))} 个源")
            else:
                logger.warning("CORS 配置初始化失败，使用本地兜底")

        # 加载 HMAC 密钥
        hmac_keys = await self.list_hmac_keys()
        for app_id in hmac_keys:
            # 调用 get_hmac_key 会自动保存到本地缓存
            await self.get_hmac_key(app_id)
        logger.info(f"HMAC 密钥已加载: {len(hmac_keys)} 个")

        logger.info("配置加载完成")



# 全局实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
