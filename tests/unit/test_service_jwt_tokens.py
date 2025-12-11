from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from eduagent.settings import settings


def test_generate_service_jwt_from_settings() -> None:
    cfg = settings.service_auth
    now = datetime.now(tz=UTC)
    payload = {
        "iss": cfg.issuer,
        "aud": cfg.audience,
        "sub": "unit-test-service",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=30)).timestamp()),
    }
    token: str = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        payload, cfg.secret_key, algorithm=cfg.algorithm
    )
    print(f"Service JWT: {token}")

    decoded: dict[str, Any] = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
        token,
        cfg.secret_key,
        algorithms=[cfg.algorithm],
        audience=cfg.audience,
        issuer=cfg.issuer,
    )
    assert decoded["sub"] == payload["sub"]
