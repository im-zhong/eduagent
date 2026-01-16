"""Test configuration for integration tests."""

from collections.abc import AsyncGenerator

import jwt
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from eduagent.documents.models import Base as DocumentsBase
from eduagent.quiz.models import Base as QuizBase
from eduagent.settings import settings
from eduagent.storage.engine import (
    get_async_session,
    async_session_ctx,
    create_tables_for_module,
    async_engine,
)
from eduagent.storage.minio_client import MinIOConfig, MinIOStorage


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_database_tables():
    """Create database tables for integration tests.

    This fixture runs once per test session to ensure all required
    tables exist before tests start. Each module owns its own Base
    class for table management.

    Note: When creating tables, we need to handle foreign key constraints
    across modules (e.g., quiz.doc_id references source_document.id).
    We create all tables by combining both metadatas to ensure proper
    foreign key resolution.
    """
    # Combine both metadatas for table creation
    # This ensures cross-module foreign keys are resolved correctly
    from sqlalchemy import MetaData

    combined_metadata = MetaData()
    # Add all tables from both modules
    for table in DocumentsBase.metadata.tables.values():
        table.to_metadata(combined_metadata)
    for table in QuizBase.metadata.tables.values():
        table.to_metadata(combined_metadata)

    async with async_engine.begin() as conn:
        await conn.run_sync(combined_metadata.create_all)
    yield
    # No cleanup needed - tables persist for test session


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Create a database session for testing.

    Note: Uses production database in dev container for integration testing.
    Test cleanup functions are responsible for cleaning up test data.

    Using function scope to ensure each test gets its own session and avoid
    concurrent database operation conflicts.
    """
    async with async_session_ctx() as session:
        yield session


@pytest.fixture
def auth_token() -> str:
    """Generate a valid JWT token for testing."""
    config = settings.service_auth
    payload = {
        "sub": "test-service",
        "aud": config.audience,
        "iss": config.issuer,
    }
    token = jwt.encode(
        payload,
        config.secret_key,
        algorithm=config.algorithm,
    )
    return f"Bearer {token}"


@pytest.fixture
def minio_config() -> MinIOConfig:
    """MinIO configuration for testing."""
    return MinIOConfig(
        endpoint=settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.secure,
        bucket=f"eduagent-test-{settings.minio.bucket}",
    )


@pytest.fixture
def mock_file_upload(tmp_path) -> tuple[str, bytes]:
    """Create a mock file for testing."""
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("This is a test document content")
    content = test_file.read_bytes()
    return str(test_file.name), content


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
