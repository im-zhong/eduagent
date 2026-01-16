"""Unit tests for MinIO client.

Tests the MinIOConfig model and MinIOStorage class methods.
Uses real MinIO from settings for integration-style testing in dev container.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytest

from eduagent.settings import settings
from eduagent.storage.minio_client import MinIOConfig, MinIOStorage


# ================================
# Test Configuration
# ================================


def _get_minio_storage() -> MinIOStorage:
    """Create MinIOStorage instance with test configuration.

    Uses a separate test bucket to avoid conflicts with production data.
    """
    config = MinIOConfig(
        endpoint=settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.secure,
        bucket=f"{settings.minio.bucket}-test",  # Use test bucket
    )
    return MinIOStorage(config=config)


# ================================
# MinIOConfig Model Tests
# ================================


class TestMinIOConfig:
    """Test MinIOConfig Pydantic model validation."""

    def test_minio_config_with_valid_fields(self) -> None:
        """Test creating MinIOConfig with all required fields."""
        config = MinIOConfig(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket="eduagent-docs",
        )
        assert config.endpoint == "localhost:9000"
        assert config.access_key == "minioadmin"
        assert config.secret_key == "minioadmin"
        assert config.bucket == "eduagent-docs"
        assert config.secure is False  # Default value

    def test_minio_config_with_secure_true(self) -> None:
        """Test creating MinIOConfig with secure=True."""
        config = MinIOConfig(
            endpoint="minio.example.com",
            access_key="user",
            secret_key="pass",
            bucket="docs",
            secure=True,
        )
        assert config.secure is True

    def test_minio_config_from_settings(self) -> None:
        """Test creating MinIOConfig from global settings."""
        config = MinIOConfig(
            endpoint=settings.minio.endpoint,
            access_key=settings.minio.access_key,
            secret_key=settings.minio.secret_key,
            secure=settings.minio.secure,
            bucket=settings.minio.bucket,
        )
        assert config.endpoint == settings.minio.endpoint
        assert config.bucket == settings.minio.bucket


# ================================
# MinIOStorage.generate_object_name() Tests
# ================================


class TestGenerateObjectName:
    """Test the static generate_object_name method."""

    def test_generate_object_name_basic_filename(self) -> None:
        """Test object name generation with basic filename."""
        result = MinIOStorage.generate_object_name("test.pdf")
        # Format: documents/YYYYMMDDHHMMSS_test.pdf
        assert result.startswith("documents/")
        assert result.endswith("_test.pdf")
        # Verify timestamp format (14 digits)
        parts = result.split("/")
        timestamp_part = parts[1].split("_")[0]
        assert len(timestamp_part) == 14
        assert timestamp_part.isdigit()

    def test_generate_object_name_with_spaces(self) -> None:
        """Test that spaces in filename are replaced with underscores."""
        result = MinIOStorage.generate_object_name("my document.pdf")
        assert "_my_document.pdf" in result
        assert "my document.pdf" not in result

    def test_generate_object_name_with_forward_slash(self) -> None:
        """Test that forward slashes are replaced with underscores."""
        result = MinIOStorage.generate_object_name("folder/file.txt")
        assert "_folder_file.txt" in result
        assert "folder/file" not in result

    def test_generate_object_name_with_backslash(self) -> None:
        """Test that backslashes are replaced with underscores."""
        result = MinIOStorage.generate_object_name(r"folder\file.txt")
        assert "_folder_file.txt" in result
        assert r"folder\file" not in result

    def test_generate_object_name_with_multiple_issues(self) -> None:
        """Test filename with spaces, slashes, and backslashes."""
        result = MinIOStorage.generate_object_name(r"my folder/test file.pdf")
        assert "_my_folder_test_file.pdf" in result


# ================================
# MinIOStorage.ensure_bucket_exists() Tests
# ================================


class TestEnsureBucketExists:
    """Test the ensure_bucket_exists method with real MinIO."""

    @pytest.mark.asyncio
    async def test_ensure_bucket_creates_new_bucket(self) -> None:
        """Test ensure_bucket_exists creates bucket when it doesn't exist."""
        storage = _get_minio_storage()

        # First call should create the bucket
        await storage.ensure_bucket_exists()

        # Verify bucket exists by calling again (should not fail)
        await storage.ensure_bucket_exists()

    @pytest.mark.asyncio
    async def test_ensure_bucket_idempotent(self) -> None:
        """Test that ensure_bucket_exists is idempotent."""
        storage = _get_minio_storage()

        # Call multiple times should not fail
        await storage.ensure_bucket_exists()
        await storage.ensure_bucket_exists()
        await storage.ensure_bucket_exists()


# ================================
# MinIOStorage.upload_file() Tests
# ================================


class TestUploadFile:
    """Test the upload_file method with real MinIO."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self) -> None:
        """Test successful file upload to MinIO."""
        storage = _get_minio_storage()

        # Create test file data
        test_content = b"This is test content for MinIO upload"
        file_data = BytesIO(test_content)
        object_name = "test_upload.txt"
        content_type = "text/plain"
        length = len(test_content)

        # Upload the file
        await storage.upload_file(file_data, object_name, content_type, length)

        # Verify file exists after upload
        assert await storage.file_exists(object_name) is True

    @pytest.mark.asyncio
    async def test_upload_pdf_file(self) -> None:
        """Test uploading a PDF file."""
        storage = _get_minio_storage()

        # Simulate PDF content
        test_content = b"%PDF-1.4 fake pdf content"
        file_data = BytesIO(test_content)
        object_name = "test_document.pdf"
        content_type = "application/pdf"
        length = len(test_content)

        await storage.upload_file(file_data, object_name, content_type, length)

        # Verify upload
        assert await storage.file_exists(object_name) is True

    @pytest.mark.asyncio
    async def test_upload_with_generated_object_name(self) -> None:
        """Test upload with auto-generated object name."""
        storage = _get_minio_storage()

        test_content = b"Test file content"
        file_data = BytesIO(test_content)
        object_name = MinIOStorage.generate_object_name("test file.txt")
        length = len(test_content)

        await storage.upload_file(file_data, object_name, "text/plain", length)

        # Verify the generated name works
        assert await storage.file_exists(object_name) is True

    @pytest.mark.asyncio
    async def test_upload_overwrites_existing_file(self) -> None:
        """Test that uploading same object name overwrites existing file."""
        storage = _get_minio_storage()

        object_name = "overwrite_test.txt"

        # Upload first version
        await storage.upload_file(
            BytesIO(b"version 1"), object_name, "text/plain", 9
        )

        # Upload second version with same name
        await storage.upload_file(
            BytesIO(b"version 2"), object_name, "text/plain", 9
        )

        # Download and verify we get the second version
        downloaded = await storage.download_file(object_name)
        assert downloaded == b"version 2"


# ================================
# MinIOStorage.download_file() Tests
# ================================


class TestDownloadFile:
    """Test the download_file method with real MinIO."""

    @pytest.mark.asyncio
    async def test_download_file_success(self) -> None:
        """Test successful file download from MinIO."""
        storage = _get_minio_storage()

        # First upload a file
        test_content = b"Download test content"
        object_name = "download_test.txt"
        await storage.upload_file(BytesIO(test_content), object_name, "text/plain", len(test_content))

        # Then download it
        downloaded_content = await storage.download_file(object_name)

        # Verify content matches
        assert downloaded_content == test_content

    @pytest.mark.asyncio
    async def test_download_nonexistent_file_raises_exception(self) -> None:
        """Test that downloading non-existent file raises exception."""
        storage = _get_minio_storage()

        with pytest.raises(Exception):
            await storage.download_file("nonexistent_file.txt")

    @pytest.mark.asyncio
    async def test_download_pdf_file(self) -> None:
        """Test downloading a PDF file."""
        storage = _get_minio_storage()

        # Upload a fake PDF
        test_content = b"%PDF-1.4\n%%Fake PDF content"
        object_name = "test_download.pdf"
        await storage.upload_file(BytesIO(test_content), object_name, "application/pdf", len(test_content))

        # Download and verify
        downloaded = await storage.download_file(object_name)
        assert downloaded == test_content
        assert downloaded.startswith(b"%PDF")


# ================================
# MinIOStorage.delete_file() Tests
# ================================


class TestDeleteFile:
    """Test the delete_file method with real MinIO."""

    @pytest.mark.asyncio
    async def test_delete_file_success(self) -> None:
        """Test successful file deletion from MinIO."""
        storage = _get_minio_storage()

        # Upload a file first
        object_name = "delete_test.txt"
        await storage.upload_file(BytesIO(b"to be deleted"), object_name, "text/plain", 13)

        # Verify file exists
        assert await storage.file_exists(object_name) is True

        # Delete the file
        await storage.delete_file(object_name)

        # Verify file no longer exists
        assert await storage.file_exists(object_name) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_is_idempotent(self) -> None:
        """Test that deleting non-existent file is idempotent (no exception)."""
        storage = _get_minio_storage()

        # MinIO remove_object is idempotent - doesn't raise for non-existent files
        # This is standard S3/MinIO behavior
        await storage.delete_file("nonexistent_file.txt")

        # Verify file doesn't exist
        assert await storage.file_exists("nonexistent_file.txt") is False

    @pytest.mark.asyncio
    async def test_delete_multiple_files(self) -> None:
        """Test deleting multiple files in sequence."""
        storage = _get_minio_storage()

        # Upload multiple files
        object_names = ["file1.txt", "file2.txt", "file3.txt"]
        for name in object_names:
            await storage.upload_file(BytesIO(b"content"), name, "text/plain", 7)

        # Delete all
        for name in object_names:
            await storage.delete_file(name)

        # Verify all deleted
        for name in object_names:
            assert await storage.file_exists(name) is False


# ================================
# MinIOStorage.file_exists() Tests
# ================================


class TestFileExists:
    """Test the file_exists method with real MinIO."""

    @pytest.mark.asyncio
    async def test_file_exists_returns_true(self) -> None:
        """Test file_exists returns True when file exists."""
        storage = _get_minio_storage()

        # Upload a file
        object_name = "exists_test.txt"
        await storage.upload_file(BytesIO(b"content"), object_name, "text/plain", 7)

        # Check existence
        assert await storage.file_exists(object_name) is True

    @pytest.mark.asyncio
    async def test_file_exists_returns_false(self) -> None:
        """Test file_exists returns False when file doesn't exist."""
        storage = _get_minio_storage()

        assert await storage.file_exists("nonexistent.txt") is False

    @pytest.mark.asyncio
    async def test_file_exists_after_deletion(self) -> None:
        """Test file_exists returns False after file is deleted."""
        storage = _get_minio_storage()

        object_name = "delete_check.txt"

        # Upload file
        await storage.upload_file(BytesIO(b"content"), object_name, "text/plain", 7)
        assert await storage.file_exists(object_name) is True

        # Delete file
        await storage.delete_file(object_name)
        assert await storage.file_exists(object_name) is False


# ================================
# End-to-End Workflow Tests
# ================================


class TestEndToEndWorkflows:
    """Test complete workflows with real MinIO."""

    @pytest.mark.asyncio
    async def test_full_upload_download_delete_workflow(self) -> None:
        """Test complete workflow: upload -> download -> delete."""
        storage = _get_minio_storage()

        # Step 1: Upload
        original_content = b"End-to-end test content with some data"
        object_name = "workflow_test.txt"
        await storage.upload_file(BytesIO(original_content), object_name, "text/plain", len(original_content))
        assert await storage.file_exists(object_name) is True

        # Step 2: Download
        downloaded_content = await storage.download_file(object_name)
        assert downloaded_content == original_content

        # Step 3: Delete
        await storage.delete_file(object_name)
        assert await storage.file_exists(object_name) is False

    @pytest.mark.asyncio
    async def test_multiple_files_with_unique_names(self) -> None:
        """Test uploading multiple files with auto-generated unique names."""
        storage = _get_minio_storage()

        # Generate unique object names based on timestamp
        names = []
        for i in range(3):
            object_name = MinIOStorage.generate_object_name(f"file{i}.txt")
            names.append(object_name)
            await storage.upload_file(BytesIO(f"content{i}".encode()), object_name, "text/plain", 8)

        # Verify all files exist and have unique names
        assert len(names) == len(set(names)), "Object names should be unique"
        for name in names:
            assert await storage.file_exists(name) is True

        # Cleanup
        for name in names:
            await storage.delete_file(name)

    @pytest.mark.asyncio
    async def test_upload_large_file(self) -> None:
        """Test uploading a larger file (1MB)."""
        storage = _get_minio_storage()

        # Create 1MB of data
        large_content = b"x" * (1024 * 1024)
        object_name = "large_file_test.bin"

        await storage.upload_file(BytesIO(large_content), object_name, "application/octet-stream", len(large_content))

        # Verify size is correct by downloading
        downloaded = await storage.download_file(object_name)
        assert len(downloaded) == len(large_content)
        assert downloaded == large_content

        # Cleanup
        await storage.delete_file(object_name)
