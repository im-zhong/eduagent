import uuid

from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)

from eduagent.settings import settings
from eduagent.user.models import User

cookie_transport = CookieTransport(cookie_name="eduagent", cookie_max_age=3600)

SECRET = settings.api.secret_key  # 假设 API secret key 在 settings 中


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend: AuthenticationBackend[User, uuid.UUID] = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
