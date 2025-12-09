from __future__ import annotations

from contextlib import suppress
from io import BytesIO
from uuid import uuid4

import pytest
from minio import Minio

from eduagent.settings import settings

pytestmark = pytest.mark.integration


def test_minio_object_roundtrip() -> None:
    config = settings.minio
    client = Minio(
        config.endpoint,
        access_key=config.access_key,
        secret_key=config.secret_key,
        secure=config.secure,
    )
    bucket_name = f"{config.bucket}-{uuid4().hex}"
    object_name = "sample.txt"
    payload = b"eduagent minio integration"
    client.make_bucket(bucket_name)
    try:
        client.put_object(
            bucket_name,
            object_name,
            data=BytesIO(payload),
            length=len(payload),
        )
        response = client.get_object(bucket_name, object_name)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
        assert content == payload
    finally:
        with suppress(Exception):
            client.remove_object(bucket_name, object_name)
        with suppress(Exception):
            client.remove_bucket(bucket_name)
