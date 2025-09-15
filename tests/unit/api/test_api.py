# test_app.py
from fastapi.testclient import TestClient
from eduagent.api import api

client = TestClient(api)


def test_hello_endpoint():
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == "hello"
