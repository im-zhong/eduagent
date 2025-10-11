from http import HTTPStatus

import httpx

BASE_URL = "http://eduagent-api:8000"


def test_hello_endpoint() -> None:
    """
    测试 API 健康检查接口 (/health) 是否可达且返回正确内容。
    """

    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/health")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "healthy", "service": "eduagent-api"}
