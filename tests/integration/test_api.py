from http import HTTPStatus

import httpx

# 将 localhost 修改为 API 服务的容器名
BASE_URL = "http://eduagent-api:8000"


def test_hello_endpoint() -> None:
    """
    测试 API 健康检查接口是否可达
    """
    # 增加超时以应对可能的容器启动延迟
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "healthy", "service": "eduagent-api"}
