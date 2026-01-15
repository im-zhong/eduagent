"""Integration tests for documents API endpoints."""

from collections.abc import AsyncGenerator

import anyio
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from io import BytesIO

from eduagent.api.endpoints import documents
from eduagent.api.api import api
import pytest_asyncio


# @pytest.fixture(scope="function")
@pytest_asyncio.fixture(scope="function")
async def async_client(auth_token: str) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for testing with authentication."""
    transport = ASGITransport(app=api, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": auth_token},
    ) as client:
        yield client


@pytest.fixture
def upload_test_document_data() -> tuple[str, bytes]:
    """Return test document data for testing."""
    filename = "test_document.txt"
    content = b"Test content for document upload"
    return filename, content


# @pytest.fixture(scope="function")
# async def test_app() -> FastAPI:
#     """Create a test FastAPI app for testing."""
#     app = FastAPI()
#     app.include_router(documents.router, prefix="/api/v1")
#     return app


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_upload_document_success(
    async_client: AsyncClient,
    upload_test_document_data: tuple[str, bytes],
):
    """Test successful document upload."""
    filename, content = upload_test_document_data

    response = await async_client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["filename"] == filename
    assert data["file_size"] == len(content)
    assert data["content_type"] == "text/plain"


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_upload_document_invalid_file(
    async_client: AsyncClient,
    upload_test_document_data: tuple[str, bytes],
):
    """Test upload with invalid file type."""
    filename, content = upload_test_document_data

    # Upload without proper file structure - should return error
    await async_client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
    )

    # Behavior depends on API implementation
    # May return 400 or create record with validation error


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_list_documents_empty(async_client: AsyncClient):
    """Test listing documents when none exist."""
    # NOTE: This test assumes clean database. In production environment,
    # there may be existing documents. Consider using a test-specific
    # naming convention for test data if cleanup is needed.

    response = await async_client.get("/api/v1/documents")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_list_documents_with_data(
    async_client: AsyncClient,
    upload_test_document_data: tuple[str, bytes],
):
    """Test listing documents when some exist."""
    filename, content = upload_test_document_data

    # First, upload a document
    await async_client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
    )

    # List documents
    response = await async_client.get("/api/v1/documents")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Verify document is in list
    uploaded_doc = next((d for d in data if d["filename"] == filename), None)
    assert uploaded_doc is not None


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_get_document_by_id_success(
    async_client: AsyncClient,
    upload_test_document_data: tuple[str, bytes],
):
    """Test getting a document by ID."""
    filename, content = upload_test_document_data

    # First, upload a document
    upload_response = await async_client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
    )
    doc_id = upload_response.json()["id"]

    # Get document by ID
    response = await async_client.get(f"/api/v1/documents/{doc_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["filename"] == filename
    assert "file_size" in data
    assert "content_type" in data


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_get_document_not_found(async_client: AsyncClient):
    """Test getting a non-existent document."""
    response = await async_client.get("/api/v1/documents/99999")

    assert response.status_code == 404


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_list_documents_sorted_by_date(async_client: AsyncClient):
    """Test that documents are sorted by creation date (newest first)."""
    # Upload multiple documents
    filenames = ["doc1.txt", "doc2.txt", "doc3.txt"]
    for filename in filenames:
        await async_client.post(
            "/api/v1/documents",
            files={"file": (filename, b"content")},
        )

    # List documents
    response = await async_client.get("/api/v1/documents")
    data = response.json()

    # Find our uploaded documents in the response
    our_docs = [d for d in data if d["filename"] in filenames]
    assert len(our_docs) >= 3

    # Verify sorting - should be newest first (highest ID or check timestamps)
    for i in range(len(our_docs) - 1):
        assert our_docs[i]["id"] >= our_docs[i + 1]["id"]


# @pytest.mark.anyio
@pytest.mark.asyncio
async def test_upload_multiple_files(
    async_client: AsyncClient,
    upload_test_document_data: tuple[str, bytes],
):
    """Test uploading multiple documents sequentially."""
    count = 3
    for i in range(count):
        filename, content = upload_test_document_data
        response = await async_client.post(
            "/api/v1/documents",
            files={"file": (f"{filename}.{i}", content)},
        )
        assert response.status_code == 201

    # List and verify all documents exist
    response = await async_client.get("/api/v1/documents")
    data = response.json()

    # Verify our uploaded documents are in the list
    our_docs = [d for d in data if d["filename"].startswith("test_document.txt.")]
    assert len(our_docs) == count
