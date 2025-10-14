from http import HTTPStatus

from fastapi.testclient import TestClient

from eduagent.api import api

client = TestClient(api)


def test_hello_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == HTTPStatus.OK


async def test_async() -> None:
    assert True
