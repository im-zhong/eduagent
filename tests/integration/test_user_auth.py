"""
集成测试: 用户认证流程 (使用 PostgreSQL)

此测试需要 PostgreSQL 数据库运行。
在本地测试前, 请确保通过 docker-compose 启动了数据库服务。
"""

from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from eduagent.api.api import api
from eduagent.storage.engine import async_session_maker
from eduagent.user.models import User


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_auth_flow_postgres() -> None:
    """
    测试用户认证的全流程 (使用 PostgreSQL): 注册, 登录, 获取信息, 登出。
    """
    # 这个测试会使用默认的 get_async_session,
    # 它连接到 .env 文件中配置的 PostgreSQL 数据库。
    # 在运行前请确保 PostgreSQL 服务正在运行。
    user_credentials = {
        "email": "test-flow-pg@example.com",
        "password": "testpassword123",
    }

    async def cleanup_test_user() -> None:
        """清理测试用户"""
        async with async_session_maker() as session:
            # 查询测试用户
            result = await session.execute(
                select(User).where(User.email == user_credentials["email"])  # type: ignore[arg-type]
            )
            user = result.scalar_one_or_none()
            # 如果存在则删除
            if user:
                await session.delete(user)
                await session.commit()

    # 清理可能存在的测试用户
    await cleanup_test_user()

    try:
        client: AsyncClient
        async with AsyncClient(
            transport=ASGITransport(app=api), base_url="http://testserver"
        ) as client:
            # 1. 注册
            response_register = await client.post(
                "/api/v1/auth/register", json=user_credentials
            )
            assert response_register.status_code == HTTPStatus.CREATED, (
                response_register.text
            )
            registered_data = response_register.json()

            # 2. 登录
            login_data = {
                "username": user_credentials["email"],
                "password": user_credentials["password"],
            }
            response_login = await client.post(
                "/api/v1/auth/jwt/login", data=login_data
            )
            assert response_login.status_code == HTTPStatus.NO_CONTENT, (
                response_login.text
            )

            # 3. 获取用户信息
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

            # 5. 验证登出
            response_me_after_logout = await client.get("/api/v1/users/me")
            assert response_me_after_logout.status_code == HTTPStatus.UNAUTHORIZED
    finally:
        # 测试结束后清理
        await cleanup_test_user()
