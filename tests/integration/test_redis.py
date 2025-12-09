from __future__ import annotations

from uuid import uuid4

import pytest
import redis

from eduagent.settings import settings

pytestmark = pytest.mark.integration


def test_redis_set_get_delete() -> None:
    config = settings.redis
    client = redis.Redis(
        host=config.host,
        port=config.port,
        db=config.db,
        decode_responses=True,
    )
    key = f"eduagent:test:{uuid4().hex}"
    value = f"value-{uuid4().hex}"
    client.set(key, value, ex=60)
    assert client.get(key) == value
    client.delete(key)
    assert client.get(key) is None
