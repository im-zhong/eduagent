from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pytest

from eduagent.storage.minio_service import MinioService


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._buffer = BytesIO(payload)

    def read(self, amt: int | None = None) -> bytes:
        return self._buffer.read(amt)

    def close(self) -> None:
        self._buffer.close()

    def release_conn(self) -> None:  # pragma: no cover - compatibility hook
        return None


class _FakeStat:
    def __init__(self, size: int) -> None:
        self.size = size


class FakeMinioClient:
    def __init__(self) -> None:
        self._buckets: set[str] = set()
        self._objects: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_calls = 0

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self._buckets

    def make_bucket(self, bucket: str) -> None:
        self._buckets.add(bucket)

    def stat_object(self, bucket: str, object_name: str) -> _FakeStat:
        key = (bucket, object_name)
        if key not in self._objects:
            raise FileNotFoundError(object_name)
        payload = self._objects[key]
        return _FakeStat(len(payload["data"]))

    def put_object(  # noqa: PLR0913
        self,
        bucket: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        *,
        content_type: str,
        metadata: dict[str, Any] | None,
    ) -> None:
        payload = data.read(length)
        self._objects[(bucket, object_name)] = {
            "data": payload,
            "content_type": content_type,
            "metadata": metadata or {},
        }
        self.put_calls += 1

    def get_object(self, bucket: str, object_name: str) -> _FakeResponse:
        key = (bucket, object_name)
        if key not in self._objects:
            raise FileNotFoundError(object_name)
        return _FakeResponse(self._objects[key]["data"])


def _service(fake: FakeMinioClient) -> MinioService:
    return MinioService(client=fake, bucket="unit-test-bucket")


def test_store_file_uploads_once() -> None:
    fake = FakeMinioClient()
    service = _service(fake)
    payload = b"hello from eduagent"
    stored = service.store_file(BytesIO(payload), filename="lesson.docx")
    assert stored.bucket == "unit-test-bucket"
    assert stored.size == len(payload)
    assert stored.object_id == "lesson.docx"
    assert stored.object_name == "lesson.docx"
    assert fake.put_calls == 1


def test_store_file_generates_unique_name_on_conflict() -> None:
    fake = FakeMinioClient()
    service = _service(fake)
    payload = b"duplicate payload"
    first = service.store_file(BytesIO(payload), filename="dup.docx")
    second = service.store_file(BytesIO(payload), filename="dup.docx")
    assert first.object_id == "dup.docx"
    assert second.object_id == "dup-1.docx"
    expected_uploads = 2
    assert fake.put_calls == expected_uploads


def test_download_to_path_restores_payload(tmp_path: Path) -> None:
    fake = FakeMinioClient()
    service = _service(fake)
    payload = b"download me"
    stored = service.store_file(BytesIO(payload), filename="sample.docx")
    destination = tmp_path / "output.docx"
    path = service.download_to_path(stored.object_id, destination)
    assert path == destination
    assert destination.read_bytes() == payload


def test_download_missing_object_raises() -> None:
    fake = FakeMinioClient()
    service = _service(fake)
    with pytest.raises(FileNotFoundError):
        service.download_to_path("missing", Path("irrelevant"))
