from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any, cast
from uuid import uuid4

import httpx
import jwt
import pytest

from eduagent.settings import settings

BASE_URL = "http://api.eduagent:8000"


def _skip_if_missing_endpoint(response: httpx.Response) -> None:
    if response.status_code == HTTPStatus.NOT_FOUND:
        pytest.skip("Service auth verification endpoint not deployed")


def _auth_headers() -> dict[str, str]:
    cfg = settings.service_auth
    now = datetime.now(tz=UTC)
    payload = {
        "iss": cfg.issuer,
        "aud": cfg.audience,
        "sub": "integration-test",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=1)).timestamp()),
    }
    jwt_module = cast(Any, jwt)
    token = jwt_module.encode(payload, cfg.secret_key, algorithm=cfg.algorithm)
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint_with_token() -> None:
    response = httpx.get(f"{BASE_URL}/api/v1/health", headers=_auth_headers())
    assert response.status_code == HTTPStatus.OK


def test_quiz_job_not_found_returns_404_with_token() -> None:
    job_id = uuid4().hex
    response = httpx.get(
        f"{BASE_URL}/api/v1/quiz/jobs/{job_id}", headers=_auth_headers()
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_service_auth_endpoint_requires_token() -> None:
    response = httpx.get(f"{BASE_URL}/service-auth/verify")
    _skip_if_missing_endpoint(response)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_service_auth_endpoint_accepts_valid_token() -> None:
    response = httpx.get(
        f"{BASE_URL}/service-auth/verify",
        headers=_auth_headers(),
    )
    _skip_if_missing_endpoint(response)
    assert response.status_code == HTTPStatus.OK
