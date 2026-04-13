"""
数据库连接池管理
"""
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from contextlib import contextmanager, asynccontextmanager
from config import settings


def _is_debug() -> bool:
    """安全的 DEBUG 值"""
    if isinstance(settings.DEBUG, bool):
        return settings.DEBUG
    return str(settings.DEBUG).lower() in ("true", "1", "yes")


class DatabaseManager:
    """数据库连接池管理器"""
    
    def __init__(self):
        # 连接参数
        self.database_url = settings.DATABASE_URL
        self._initialized = False
        
        # 引擎将在 init() 中创建
        self.sync_engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
    
    async def init(self):
        """初始化数据库连接池"""
        if self._initialized:
            return
        
        try:
            # 同步引擎
            self.sync_engine = create_engine(
                self.database_url,
                poolclass=pool.QueuePool,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=_is_debug()
            )
            
            # 异步引擎
            self.async_url = self._to_async_url(self.database_url)
            self.async_engine = create_async_engine(
                self.async_url,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            # 同步 Session 工厂 (SQLModel Session)
            self.SessionLocal = sessionmaker(
                bind=self.sync_engine,
                class_=Session,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            # 异步 Session 工厂
            self.AsyncSessionLocal = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._initialized = True
        except Exception as e:
            raise Exception(f"Failed to initialize database connection pool: {e}")
    
    def _to_async_url(self, url: str) -> str:
        """将同步 URL 转换为异步 URL"""
        if url.startswith("mysql+pymysql://"):
            return url.replace("mysql+pymysql://", "mysql+aiomysql://")
        elif url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://")
        return url
    
    def create_tables(self):
        """创建所有表（同步）"""
        SQLModel.metadata.create_all(self.sync_engine)
    
    async def create_tables_async(self):
        """创建所有表（异步）"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    
    def drop_tables(self):
        """删除所有表"""
        SQLModel.metadata.drop_all(self.sync_engine)
    
    @contextmanager
    def get_session(self):
        """获取同步数据库会话"""
        with self.SessionLocal() as session:
            yield session
    
    def close(self):
        """关闭所有连接"""
        self.sync_engine.dispose()
    
    async def async_close(self):
        """异步关闭所有连接"""
        await self.async_engine.dispose()


db_manager = DatabaseManager()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的同步数据库会话"""
    with db_manager.SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的异步数据库会话"""
    async with db_manager.AsyncSessionLocal() as session:
        yield session
