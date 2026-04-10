"""
数据库连接池管理
"""
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from contextlib import contextmanager
from typing import Generator
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
    
    def _to_async_url(self, url: str) -> str:
        """将同步 URL 转换为异步 URL"""
        if url.startswith("mysql+pymysql://"):
            return url.replace("mysql+pymysql://", "mysql+aiomysql://")
        elif url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://")
        return url
    
    def create_tables(self):
        """创建所有表"""
        SQLModel.metadata.create_all(self.sync_engine)
    
    def drop_tables(self):
        """删除所有表"""
        SQLModel.metadata.drop_all(self.sync_engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取同步数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self):
        """关闭所有连接"""
        self.sync_engine.dispose()
    
    async def async_close(self):
        """异步关闭所有连接"""
        await self.async_engine.dispose()


db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入用的数据库会话"""
    with db_manager.get_session() as session:
        yield session
