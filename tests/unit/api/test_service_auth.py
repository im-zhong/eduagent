from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Annotated, Any

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from eduagent.api.security import require_service_token
from eduagent.settings import settings


def _issue_token(overrides: dict[str, Any] | None = None) -> str:
    config = settings.service_auth
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": "user-123",
        "iss": config.issuer,
        "aud": config.audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=1)).timestamp()),
        "scope": "quiz:write",
    }
    if overrides:
        payload.update(overrides)
    return jwt.encode(payload, config.secret_key, algorithm=config.algorithm)


app = FastAPI()


@app.get("/secure")
async def secure_endpoint(
    claims: Annotated[dict[str, Any], Depends(require_service_token)],
) -> dict[str, Any]:
    return {"subject": claims.get("sub")}


def _create_test_client() -> TestClient:
    return TestClient(app)


def test_require_service_token_missing_header() -> None:
    client = _create_test_client()
    response = client.get("/secure")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_require_service_token_valid_token() -> None:
    client = _create_test_client()
    token = _issue_token()
    response = client.get("/secure", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == HTTPStatus.OK
    assert response.json()["subject"] == "user-123"


def test_require_service_token_invalid_signature() -> None:
    client = _create_test_client()
    token = _issue_token()
    tampered = token[::-1]
    response = client.get("/secure", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
