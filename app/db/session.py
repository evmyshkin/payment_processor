from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import config


@lru_cache
def get_engine() -> AsyncEngine:
    """Возвращает кешированный async-движок для PostgreSQL."""
    return create_async_engine(
        config.get_db_url(),
        pool_pre_ping=True,
    )


@lru_cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Возвращает кешированный фабричный метод создания AsyncSession."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency для выдачи AsyncSession."""
    async with get_session_maker()() as session:
        yield session
