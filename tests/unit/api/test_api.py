from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

import jwt
from fastapi.testclient import TestClient

from eduagent.api import api
from eduagent.settings import settings

client = TestClient(api)


def _issue_service_token() -> str:
    config = settings.service_auth
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": "test-user",
        "iss": config.issuer,
        "aud": config.audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=1)).timestamp()),
    }
    return jwt.encode(payload, config.secret_key, algorithm=config.algorithm)


def test_hello_endpoint() -> None:
    token = _issue_service_token()
    response = client.get(
        "/api/v1/health", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == HTTPStatus.OK


async def test_async() -> None:
    assert True
