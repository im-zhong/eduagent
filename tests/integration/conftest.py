"""Test configuration for integration tests."""

from collections.abc import AsyncGenerator

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from eduagent.settings import settings
from eduagent.storage.minio_client import MinIOConfig, MinIOStorage


# @pytest.fixture(scope="function")
# async def db_session() -> AsyncGenerator[AsyncSession]:
#     """Create a database session for testing.

#     Note: Uses production database in dev container for integration testing.
#     Test cleanup functions are responsible for cleaning up test data.

#     Using function scope to ensure each test gets its own session and avoid
#     concurrent database operation conflicts.
#     """
#     # 我觉得可以直接用fastapi自带的engine啊
#     # engine = create_async_engine(settings.database.sqlalchemy_url)
#     # async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

#     # async with async_session_maker() as session:
#     #     yield session

#     # await engine.dispose()
#     pass


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
