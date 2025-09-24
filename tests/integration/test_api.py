from http import HTTPStatus

import httpx

BASE_URL = "http://api.eduagent:8000"


def test_hello_endpoint() -> None:
    response = httpx.get(f"{BASE_URL}/api/v1/health")
    assert response.status_code == HTTPStatus.OK
