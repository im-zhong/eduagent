from http import HTTPStatus

import httpx

BASE_URL = "http://eduagent-api:8000"  # your FastAPI service URL


def test_hello_endpoint() -> None:
    response = httpx.get(f"{BASE_URL}/hello")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == "hello"
