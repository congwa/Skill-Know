"""数据库连接管理

使用 SQLite + aiosqlite 异步数据库。
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("database")

# 创建异步引擎（SQLite 使用 NullPool 避免并发问题）
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    echo=settings.DEBUG,
)

# 会话工厂
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（上下文管理器）"""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise


async def init_db() -> None:
    """初始化数据库（创建表）"""
    from app.models.base import Base

    settings.ensure_data_dir()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("数据库表初始化完成")
