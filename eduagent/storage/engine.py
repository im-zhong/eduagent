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
from contextlib import asynccontextmanager


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


# FastAPI DB dependency notes:
# - FastAPI supports async *generator* dependencies (yield-based) for setup/teardown.
# - Code before `yield` runs before the request; code after `yield` runs after the request.
# - This behavior is FastAPI-specific magic; Python itself does NOT treat async generators
#   as async context managers.
# - Therefore, async generator dependencies MUST ONLY be used via `Depends()`.

# Testing (pytest) notes:
# - pytest fixtures must own the resource lifecycle explicitly.
# - You CANNOT use `async with get_async_session()` if it is an async generator.
# - Do NOT reuse FastAPI generator dependencies directly inside pytest fixtures.
# - Instead, either:
#     (a) duplicate the sessionmaker logic in the fixture, or
#     (b) factor shared logic into an @asynccontextmanager and reuse it.

# Architecture rule of thumb:
# - FastAPI owns dependency generators.
# - pytest owns fixtures.
# - Shared DB lifecycle logic belongs in an async context manager.
# - Never nest or cross-use async generators across frameworks.


# Testing safety:
# - Committing in test sessions is OK for integration tests but unsafe for isolation.
# - Preferred pattern is per-test transaction + rollback for clean, parallel-safe tests.
@asynccontextmanager
async def async_session_ctx():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    # """Get async session for dependency injection with automatic commit/rollback.

    # On success: commits before yielding
    # On exception: rolls back and re-raises
    # """
    # async with async_session_maker() as session:
    #     try:
    #         yield session
    #         await session.commit()
    #     except Exception:
    #         await session.rollback()
    #         raise
    async with async_session_ctx() as session:
        yield session


async def create_tables_for_module(base: type[DeclarativeBase]) -> None:
    """Create tables for a specific module's Base class.

    Deprecated: All modules should now use the shared Base from
    eduagent.storage.models. Use create_all_tables() instead.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)


async def create_all_tables() -> None:
    """Create all database tables using the global Base class.

    This is the recommended way to create tables. All modules (documents,
    quiz, etc.) inherit from the shared Base in eduagent.storage.models,
    which enables cross-module foreign keys to work correctly.

    Architecture note:
        - Single global Base class (eduagent.storage.models.Base)
        - Each module owns its models (SourceDocument, Quiz, etc.)
        - String-based FKs (e.g., "source_document.id") work correctly
        - SQLAlchemy handles table creation order automatically
    """
    # Import Base to ensure all models are registered
    from eduagent.storage.models import Base

    # Create all tables - SQLAlchemy handles dependency ordering
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
