from __future__ import annotations

from contextlib import suppress
from typing import Any, cast
from uuid import uuid4

import pytest
from kombu import Connection

from eduagent.settings import settings

pytestmark = pytest.mark.integration

_RABBITMQ_TIMEOUT_MESSAGE = "Message was not received from RabbitMQ"


def test_rabbitmq_publish_consume() -> None:
    config = settings.rabbitmq
    queue_name = f"eduagent.integration.queue.{uuid4().hex}"
    payload = {"hello": "eduagent", "id": uuid4().hex}
    with Connection(config.amqp_url) as connection:
        connection_any = cast(Any, connection)
        simple_queue = connection_any.SimpleQueue(queue_name)
        try:
            simple_queue.put(payload, serializer="json")
            try:
                message = simple_queue.get(timeout=5)
            except Exception as exc:  # pragma: no cover - fail fast
                raise AssertionError(_RABBITMQ_TIMEOUT_MESSAGE) from exc
            assert message.payload == payload
            message.ack()
        finally:
            with suppress(Exception):
                simple_queue.queue.delete()
            with suppress(Exception):
                simple_queue.close()
