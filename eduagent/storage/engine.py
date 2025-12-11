from collections.abc import AsyncGenerator

from pydantic import BaseModel, Field
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import Pool

from eduagent.settings import DatabaseConfig, settings


class PGSQLSettings(BaseModel):
    username: str = Field(..., title="Postgres User")
    password: str = Field(..., title="Postgres Password")
    host: str = Field(..., title="Postgres Host")
    port: int = Field(..., title="Postgres Port")
    database: str = Field(..., title="Postgres Database")

    def get_pgsql_url(self) -> str:
        return f"postgresql+psycopg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


def create_pgsql_engine(pgsql_settings: PGSQLSettings) -> Engine:
    return create_engine(pgsql_settings.get_pgsql_url(), echo=True)


# ==============================================================================
# 异步引擎和会话，供 fastapi-users 使用
# ==============================================================================


def create_async_pgsql_engine(
    db_settings: DatabaseConfig, *, poolclass: type[Pool] | None = None
) -> AsyncEngine:
    """创建异步 PostgreSQL 引擎"""
    async_url = db_settings.sqlalchemy_url.replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    return create_async_engine(async_url, poolclass=poolclass)


async_engine = create_async_pgsql_engine(settings.database)

# 创建一个异步 sessionmaker 工厂
async_session_maker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


def create_async_session_factory(
    *, poolclass: type[Pool] | None = None
) -> async_sessionmaker[AsyncSession]:
    """Create a dedicated async session factory, optionally overriding the pool."""
    engine = create_async_pgsql_engine(settings.database, poolclass=poolclass)
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
