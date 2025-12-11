from __future__ import annotations

from typing import Any, cast

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from eduagent.logger import get_logger
from eduagent.settings import settings

_bearer_scheme = HTTPBearer(auto_error=False)
security_logger = get_logger(__name__, component="api.auth")


async def require_service_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Validate the inbound service token and return decoded claims."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    token = credentials.credentials
    config = settings.service_auth
    try:
        jwt_module = cast(Any, jwt)
        payload = cast(
            dict[str, Any],
            jwt_module.decode(
                token,
                config.secret_key,
                algorithms=[config.algorithm],
                audience=config.audience or None,
                issuer=config.issuer or None,
                leeway=config.leeway_seconds,
                options={"verify_aud": bool(config.audience)},
            ),
        )
    except jwt.InvalidTokenError as exc:
        security_logger.warning("Invalid service token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    return payload
