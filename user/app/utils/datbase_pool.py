"""
数据库连接池管理（支持多库）
"""
from typing import AsyncGenerator, Generator, Dict, Optional
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel
from contextlib import contextmanager, asynccontextmanager
from config.settings import settings
    
def _is_debug() -> bool:
    """安全的 DEBUG 值"""
    if isinstance(settings.DEBUG, bool):
        return settings.DEBUG
    return str(settings.DEBUG).lower() in ("true", "1", "yes")   

class DatabaseManage:
    def __init__(self):
        self._initialized = False
        self._engines: Dict[str, any] = {}  # {name: sync_engine}
        self._async_engines: Dict[str, any] = {}  # {name: async_engine}
        self._session_factories: Dict[str, sessionmaker] = {} # {name: sync_session_factory}
        self._async_session_factories: Dict[str, async_sessionmaker] = {} # {name: async_session_factory}

    def add_database(self, name: str, url: str, is_default: bool = False):
        """
        添加数据库连接
        
        Args:
            name: 数据库名称
            url: 数据库连接URL
            is_default: 是否为默认数据库
        """
        if self._initialized:
            raise RuntimeError("Cannot add database after initialization")
        
        # 同步引擎
        sync_engine = create_engine(
            url,
            poolclass=pool.QueuePool,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=_is_debug()
        )
        
        # 异步引擎
        async_url = self._to_async_url(url)
        async_engine = create_async_engine(
            async_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        # 会话工厂
        sync_factory = sessionmaker(
            bind=sync_engine,
            class_=Session,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        # 异步会话工厂
        async_factory = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        # 添加数据库连接信息
        self._engines[name] = sync_engine
        self._async_engines[name] = async_engine
        self._session_factories[name] = sync_factory
        self._async_session_factories[name] = async_factory
        
        # 设置默认数据库
        if is_default or not hasattr(self, '_default_db'):
            self._default_db = name

    def init(self):
        """初始化默认数据库（兼容旧接口）"""
        if self._initialized:
            return
        
        if not self._engines:
            # 如果没有手动添加，使用配置中的默认数据库
            self.add_database("default", settings.DATABASE_URL, is_default=True)
        
        self._initialized = True


    def _to_async_url(self, url: str) -> str:
        """将同步 URL 转换为异步 URL"""
        if url.startswith("mysql+pymysql://"):
            return url.replace("mysql+pymysql://", "mysql+aiomysql://")
        elif url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://")
        return url

    def _get_sync_engine(self, db_name: Optional[str] = None):
        """获取同步引擎"""
        name = db_name or self._default_db
        if name not in self._engines:
            raise KeyError(f"Database '{name}' not found")
        return self._engines[name]
    
    def _get_async_engine(self, db_name: Optional[str] = None):
        """获取异步引擎"""
        name = db_name or self._default_db
        if name not in self._async_engines:
            raise KeyError(f"Database '{name}' not found")
        return self._async_engines[name]
    
    def _get_sync_session(self, db_name: Optional[str] = None):
        """获取同步会话工厂"""
        name = db_name or self._default_db
        if name not in self._session_factories:
            raise KeyError(f"Database '{name}' not found")
        return self._session_factories[name]
    
    def _get_async_session(self, db_name: Optional[str] = None):
        """获取异步会话工厂"""
        name = db_name or self._default_db
        if name not in self._async_session_factories:
            raise KeyError(f"Database '{name}' not found")
        return self._async_session_factories[name]

    # 创建所有表
    def create_tables(self, db_name: Optional[str] = None):
        """创建指定数据库的所有表"""
        engine = self._get_sync_engine(db_name)
        SQLModel.metadata.create_all(engine)
    
    async def create_tables_async(self, db_name: Optional[str] = None):
        """异步创建指定数据库的所有表"""
        engine = self._get_async_engine(db_name)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    


    @contextmanager
    def session(self, db_name: Optional[str] = None) -> Generator[Session, None, None]:
        """同步会话"""
        session_factory = self._get_sync_session(db_name)
        try:
            with session_factory() as session:
                yield session
        except Exception as e:
            raise Exception(f"Failed to create database session: {e}")

    def close(self, db_name: Optional[str] = None):
        """关闭指定数据库的同步连接"""
        engine = self._get_sync_engine(db_name)
        engine.dispose()
    
    def close_all(self):
        """关闭所有数据库连接"""
        for engine in self._engines.values():
            engine.dispose()

    async def close_async(self, db_name: Optional[str] = None):
        """关闭指定数据库的异步连接"""
        engine = self._get_async_engine(db_name)
        await engine.dispose()
    
    async def close_all_async(self):
        """关闭所有数据库的异步连接"""
        for engine in self._async_engines.values():
            await engine.dispose()


db_manager = DatabaseManage() # 创建数据库管理实例


@contextmanager
def get_session(db_name: Optional[str] = None) -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的同步数据库会话"""
    session_factory = db_manager._get_sync_session(db_name)
    with session_factory() as session:
        yield session

async def get_session_async(db_name: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的异步数据库会话"""
    session_factory = db_manager._get_async_session(db_name)
    async with session_factory() as session:
        yield session
