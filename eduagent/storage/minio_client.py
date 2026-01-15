"""MinIO client wrapper for async object storage operations."""
import asyncio
from datetime import datetime
from functools import partial
from io import BytesIO
from typing import BinaryIO

from minio import Minio
from pydantic import BaseModel, Field

from eduagent.logger import get_logger

logger = get_logger(__name__, component="storage.minio")


class MinIOConfig(BaseModel):
    """MinIO configuration."""

    endpoint: str = Field(..., description="MinIO server endpoint")
    access_key: str = Field(..., description="Access key")
    secret_key: str = Field(..., description="Secret key")
    secure: bool = Field(default=False, description="Use HTTPS")
    bucket: str = Field(..., description="Bucket name")


class MinIOStorage:
    """MinIO storage client wrapper with async support via run_in_executor."""

    def __init__(
        self,
        config: MinIOConfig,
    ) -> None:
        """Initialize MinIO storage client.

        Args:
            config: MinIO configuration
        """
        self.config = config

        # Create sync MinIO client
        self.client = Minio(
            self.config.endpoint,
            access_key=self.config.access_key,
            secret_key=self.config.secret_key,
            secure=self.config.secure,
        )

    async def ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if not.

        Uses run_in_executor to avoid blocking the event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            bucket_exists = await loop.run_in_executor(
                None,
                self.client.bucket_exists,
                self.config.bucket,
            )
            if not bucket_exists:
                logger.info("Creating bucket: %s", self.config.bucket)
                await loop.run_in_executor(
                    None,
                    self.client.make_bucket,
                    self.config.bucket,
                )
                logger.info("Bucket created successfully: %s", self.config.bucket)
            else:
                logger.debug("Bucket exists: %s", self.config.bucket)
        except Exception as e:
            logger.error("Failed to ensure bucket exists: %s", e)
            raise

    @staticmethod
    def generate_object_name(filename: str) -> str:
        """Generate a unique object name for storage.

        Uses timestamp prefix for chronological organization.

        Args:
            filename: Original filename

        Returns:
            Object name in format: documents/YYYYMMDDHHMMSS_filename.ext
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        safe_filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
        return f"documents/{timestamp}_{safe_filename}"

    async def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: str,
        length: int,
    ) -> None:
        """Upload a file to MinIO.

        DESIGN CHOICE: Accept BinaryIO instead of bytes

        Why BinaryIO (file-like object) over bytes:

        1. Memory Efficiency:
           - bytes: Entire file loaded into memory before upload
           - BinaryIO: Enables streaming, only chunks held in memory
           - For large files (>100MB), bytes causes OOM errors

        2. Alignment with FastAPI:
           - UploadFile.file is already a SpooledTemporaryFile (BinaryIO)
           - Passing bytes requires reading entire file first (await file.read())
           - Direct pass of UploadFile.file is more efficient

        3. No Redundant Wrapping:
           - bytes would need BytesIO(bytes) to satisfy MinIO API
           - BinaryIO eliminates this extra conversion step

        4. Thread Safety with run_in_executor:
           - The file object passed must be thread-safe for run_in_executor
           - For async file objects (UploadFile), use .file attribute which is sync
           - For in-memory data, use BytesIO (creates thread-safe copy)
           - For disk files, use open() with mode='rb' (sync file is thread-safe)

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            file_data: File object with read() method (BinaryIO interface)
                      Must be thread-safe for executor usage
            object_name: Object name in MinIO
            content_type: MIME content type
            length: File size in bytes (required by MinIO's put_object)

        Raises:
            Exception: If upload fails

        Example usage:
            # From FastAPI UploadFile (recommended for HTTP uploads)
            await upload_file(
                file_data=upload_file.file,
                object_name="doc.txt",
                content_type="text/plain",
                length=upload_file.size,
            )

            # From in-memory bytes
            await upload_file(
                file_data=BytesIO(b"content"),
                object_name="doc.txt",
                content_type="text/plain",
                length=len(b"content"),
            )

            # From disk file
            with open("file.txt", "rb") as f:
                await upload_file(
                    file_data=f,
                    object_name="doc.txt",
                    content_type="text/plain",
                    length=os.path.getsize("file.txt"),
                )
        """
        try:
            await self.ensure_bucket_exists()
            logger.info("Uploading file to MinIO: %s", object_name)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(
                    self.client.put_object,
                    self.config.bucket,
                    object_name,
                    file_data,
                    length,
                    content_type=content_type,
                    metadata={
                        "X-Amz-Meta-Uploaded-At": datetime.utcnow().isoformat(),
                    },
                ),
            )
            logger.info("File uploaded successfully: %s", object_name)
        except Exception as e:
            logger.error("Failed to upload file to MinIO: %s", e)
            raise

    async def download_file(self, object_name: str) -> bytes:
        """Download a file from MinIO.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            object_name: Object name in MinIO

        Returns:
            File content as bytes

        Raises:
            Exception: If download fails
        """
        try:
            logger.info("Downloading file from MinIO: %s", object_name)

            loop = asyncio.get_event_loop()

            def _download_and_read() -> bytes:
                response = self.client.get_object(self.config.bucket, object_name)
                return response.read()

            file_data = await loop.run_in_executor(None, _download_and_read)
            logger.info("File downloaded successfully: %s", object_name)
            return file_data
        except Exception as e:
            logger.error("Failed to download file from MinIO: %s", e)
            raise

    async def delete_file(self, object_name: str) -> None:
        """Delete a file from MinIO.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            object_name: Object name in MinIO

        Raises:
            Exception: If deletion fails
        """
        try:
            logger.info("Deleting file from MinIO: %s", object_name)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.client.remove_object, self.config.bucket, object_name),
            )
            logger.info("File deleted successfully: %s", object_name)
        except Exception as e:
            logger.error("Failed to delete file from MinIO: %s", e)
            raise

    async def file_exists(self, object_name: str) -> bool:
        """Check if a file exists in MinIO.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            object_name: Object name in MinIO

        Returns:
            True if file exists, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                partial(self.client.stat_object, self.config.bucket, object_name),
            )
            return True
        except Exception:
            return False
