from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Protocol, cast

from minio import Minio
from minio.error import S3Error

from eduagent.logger import get_logger
from eduagent.settings import settings

type MetadataValue = str | list[str] | tuple[str]
type MetadataDict = dict[str, MetadataValue]


class MinioObjectStream(Protocol):
    def read(self, amt: int | None = None) -> bytes: ...

    def close(self) -> None: ...

    def release_conn(self) -> None: ...


class MinioClientProtocol(Protocol):
    def bucket_exists(self, bucket: str) -> bool: ...

    def make_bucket(self, bucket: str) -> None: ...

    def stat_object(self, bucket: str, object_name: str) -> object: ...

    def put_object(  # noqa: PLR0913
        self,
        bucket: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        *,
        content_type: str,
        metadata: MetadataDict | None,
    ) -> None: ...

    def get_object(self, bucket: str, object_name: str) -> MinioObjectStream: ...


@dataclass(slots=True)
class StoredObject:
    object_id: str
    bucket: str
    object_name: str
    size: int
    checksum: str


class MinioService:
    """Utility wrapper to interact with MinIO storage."""

    _CHUNK_SIZE = 1024 * 1024
    _SPOOL_THRESHOLD = 16 * 1024 * 1024

    def __init__(
        self,
        client: Minio | MinioClientProtocol | None = None,
        *,
        bucket: str | None = None,
    ) -> None:
        cfg = settings.minio
        self.client = client or Minio(
            cfg.endpoint,
            access_key=cfg.access_key,
            secret_key=cfg.secret_key,
            secure=cfg.secure,
        )
        self.bucket = bucket or cfg.bucket
        self._bucket_ready = False
        self._logger = get_logger(__name__, component="storage.minio")

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        if not self.client.bucket_exists(self.bucket):
            self._logger.info("Creating minio bucket %s", self.bucket)
            self.client.make_bucket(self.bucket)
        self._bucket_ready = True

    @staticmethod
    def _object_name(object_id: str) -> str:
        return f"{object_id}.bin"

    def _stat_object(self, object_name: str) -> int | None:
        try:
            stat = self.client.stat_object(self.bucket, object_name)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                return None
            raise
        except FileNotFoundError:
            return None
        return getattr(stat, "size", None)

    def store_file(
        self,
        file_obj: BinaryIO,
        *,
        filename: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        """Upload file contents to MinIO and return stored object metadata."""

        self._ensure_bucket()
        hasher = hashlib.sha256()
        with SpooledTemporaryFile(max_size=self._SPOOL_THRESHOLD, mode="w+b") as temp:
            total_bytes = 0
            while True:
                chunk = file_obj.read(self._CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                temp.write(chunk)
                total_bytes += len(chunk)
            temp.seek(0)
            checksum = hasher.hexdigest()
            object_id = str(uuid.uuid5(uuid.NAMESPACE_URL, checksum))
            object_name = self._object_name(object_id)
            existing_size = self._stat_object(object_name)
            if existing_size is not None:
                return StoredObject(
                    object_id=object_id,
                    bucket=self.bucket,
                    object_name=object_name,
                    size=existing_size,
                    checksum=checksum,
                )
            metadata_payload: MetadataDict = {
                k: str(v) for k, v in (metadata or {}).items()
            }
            metadata_payload.setdefault("filename", filename)
            metadata_payload.setdefault("checksum", checksum)
            payload_metadata: MetadataDict | None = metadata_payload or None
            upload_content_type = content_type or "application/octet-stream"
            self.client.put_object(
                self.bucket,
                object_name,
                data=cast(BinaryIO, temp),
                length=total_bytes,
                content_type=upload_content_type,
                metadata=payload_metadata,
            )
        self._logger.info("Stored file %s as object %s", filename, object_id)
        return StoredObject(
            object_id=object_id,
            bucket=self.bucket,
            object_name=object_name,
            size=total_bytes,
            checksum=checksum,
        )

    def download_to_path(self, object_id: str, destination: Path) -> Path:
        self._ensure_bucket()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        object_name = self._object_name(object_id)
        response = self.client.get_object(self.bucket, object_name)
        try:
            with destination.open("wb") as target:
                copyfileobj(response, target)
        finally:
            response.close()
            release = getattr(response, "release_conn", None)
            if callable(release):
                release()
        return destination


minio_service = MinioService()

__all__ = ["MinioService", "StoredObject", "minio_service"]
