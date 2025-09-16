# test_app.py
from http import HTTPStatus

from fastapi.testclient import TestClient

from eduagent.api import api

client = TestClient(api)


def test_hello_endpoint() -> None:
    response = client.get("/hello")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == "hello"


async def test_async() -> None:
    assert True
