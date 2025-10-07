from http import HTTPStatus

from fastapi.testclient import TestClient

from eduagent.api.api import api

# --- 注意：这是一个同步测试，不再需要 pytest-asyncio ---


def test_user_auth_flow() -> None:
    """
    测试用户认证的全流程:注册、登录、获取信息、登出。
    """
    # 1. 创建一个 TestClient 实例，它在内部处理了应用的生命周期
    client = TestClient(api)

    # 2. 注册一个新用户
    registered_user = {
        "email": "test-sync-flow@example.com",
        "password": "testpassword123",
    }
    response_register = client.post("/api/v1/auth/register", json=registered_user)

    # 3. 验证注册
    assert response_register.status_code == HTTPStatus.CREATED
    register_data = response_register.json()
    assert register_data["email"] == registered_user["email"]

    # 4. 使用该用户的凭证进行登录
    login_data = {
        "username": registered_user["email"],
        "password": registered_user["password"],
    }
    response_login = client.post("/api/v1/auth/jwt/login", data=login_data)

    # 5. 验证登录
    assert response_login.status_code == HTTPStatus.NO_CONTENT
    assert "eduagent" in response_login.cookies

    # 6. 使用登录后获得的 cookie 访问受保护的 "me" 接口
    # TestClient 会自动管理和发送 cookie
    response_me = client.get("/api/v1/users/me")

    # 7. 验证是否成功获取到当前用户信息
    assert response_me.status_code == HTTPStatus.OK
    user_data = response_me.json()
    assert user_data["email"] == registered_user["email"]

    # 8. 登出
    response_logout = client.post("/api/v1/auth/jwt/logout")
    assert response_logout.status_code == HTTPStatus.NO_CONTENT

    # 9. 再次访问受保护接口，应返回 401 未授权
    response_me_after_logout = client.get("/api/v1/users/me")
    assert response_me_after_logout.status_code == HTTPStatus.UNAUTHORIZED
