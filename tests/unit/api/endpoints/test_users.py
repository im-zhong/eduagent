from collections.abc import AsyncGenerator
from http import HTTPStatus

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eduagent.api.api import api
from eduagent.storage.engine import get_async_session
from eduagent.user.models import Base

# 创建一个专门用于测试的、在内存中运行的 SQLite 数据库
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
async_engine = create_async_engine(TEST_DATABASE_URL)

async_session_maker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


# 创建一个新的依赖函数, 它将替换掉应用中原来的 `get_async_session`
async def override_get_async_session() -> AsyncGenerator[AsyncSession]:
    """
    FastAPI 依赖项覆盖: 为测试提供一个独立的内存数据库会话。
    """
    async with async_session_maker() as session:
        yield session


# 使用 pytest fixture 来管理测试的准备和清理工作
@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_session() -> AsyncGenerator[None]:
    """
    Pytest Fixture: 在每个测试函数运行前, 创建所有数据库表;
    运行结束后, 删除所有表, 确保每个测试都是在干净的环境中运行。
    """
    api.dependency_overrides[get_async_session] = override_get_async_session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # 在这里运行测试函数

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_user_auth_flow() -> None:
    """
    测试用户认证的全流程: 注册, 登录, 获取信息, 登出。
    """
    user_credentials = {
        "email": "test-flow@example.com",
        "password": "testpassword123",
    }

    # 修正：使用 ASGITransport 包装 FastAPI 应用
    # 使用 http://testserver 作为 base_url，这是 FastAPI 测试的标准域名
    async with AsyncClient(
        transport=ASGITransport(app=api), base_url="http://testserver"
    ) as client:
        # 1. 注册一个新用户
        response_register = await client.post(
            "/api/v1/auth/register", json=user_credentials
        )
        assert response_register.status_code == HTTPStatus.CREATED, (
            response_register.text
        )
        registered_data = response_register.json()
        assert registered_data["email"] == user_credentials["email"]
        assert "id" in registered_data

        # 2. 使用相同的凭据登录
        login_data = {
            "username": user_credentials["email"],
            "password": user_credentials["password"],
        }
        response_login = await client.post("/api/v1/auth/jwt/login", data=login_data)

        # 登录接口返回204,不需要解析JSON
        assert response_login.status_code == HTTPStatus.NO_CONTENT, response_login.text

        # 3. 获取当前用户信息
        response_me = await client.get("/api/v1/users/me")
        assert response_me.status_code == HTTPStatus.OK, response_me.text
        me_data = response_me.json()
        assert me_data["email"] == user_credentials["email"]
        assert me_data["id"] == registered_data["id"]

        # 4. 登出
        response_logout = await client.post("/api/v1/auth/jwt/logout")
        assert response_logout.status_code == HTTPStatus.NO_CONTENT, (
            response_logout.text
        )

        # 5. 验证登出后无法访问用户信息
        response_me_after_logout = await client.get("/api/v1/users/me")
        assert response_me_after_logout.status_code in [
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
        ], f"期望401或403,实际得到{response_me_after_logout.status_code}"
