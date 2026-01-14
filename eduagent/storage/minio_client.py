"""MinIO client wrapper for async object storage operations."""
import asyncio
from datetime import datetime
from functools import partial

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
        file_data: bytes,
        object_name: str,
        content_type: str,
    ) -> None:
        """Upload a file to MinIO.

        Uses run_in_executor to avoid blocking the event loop.

        Args:
            file_data: File content as bytes
            object_name: Object name in MinIO
            content_type: MIME content type

        Raises:
            Exception: If upload fails
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
                    len(file_data),
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
