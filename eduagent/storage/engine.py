"""Database engine and session management."""

from collections.abc import AsyncGenerator

from pydantic import BaseModel, Field
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import Pool

from eduagent.settings import DatabaseConfig, settings


class PGSQLSettings(BaseModel):
    """PostgreSQL connection settings."""

    username: str = Field(..., title="Postgres User")
    password: str = Field(..., title="Postgres Password")
    host: str = Field(..., title="Postgres Host")
    port: int = Field(..., title="Postgres Port")
    database: str = Field(..., title="Postgres Database")

    def get_pgsql_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql+psycopg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


def create_pgsql_engine(pgsql_settings: PGSQLSettings) -> Engine:
    """Create synchronous PostgreSQL engine."""
    return create_engine(pgsql_settings.get_pgsql_url(), echo=True)


def create_async_pgsql_engine(
    db_settings: DatabaseConfig, *, poolclass: type[Pool] | None = None
) -> AsyncEngine:
    """Create asynchronous PostgreSQL engine."""
    async_url = db_settings.sqlalchemy_url.replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    # 我艹！！真的是这样！session复用connection就会出现这样的问题！
    # anyio的event loop是每个测试都会创建一个，而asyncio就只有一个eventloop，然后async engine又只能绑定到一个event loop上
    # 这两个问题叠加导致的单元测试一直失败
    # nullpool的意思就是不会有复用的连接池，每个sql session的执行都会创建一个新的tcp connectino，这样就很慢，但是很安全
    return create_async_engine(async_url, poolclass=NullPool)


async_engine = create_async_pgsql_engine(settings.database)

async_session_maker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


def create_async_session_factory(
    *, poolclass: type[Pool] | None = None
) -> async_sessionmaker[AsyncSession]:
    """Create a dedicated async session factory."""
    engine = create_async_pgsql_engine(settings.database, poolclass=poolclass)
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Get async session for dependency injection."""
    async with async_session_maker() as session:
        yield session


async def create_tables_for_module(base: type[DeclarativeBase]) -> None:
    """Create tables for a specific module's Base class."""
    async with async_engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
