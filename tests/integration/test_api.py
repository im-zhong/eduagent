import httpx

BASE_URL = "http://eduagent-api:8000"  # your FastAPI service URL


def test_hello_endpoint():
    response = httpx.get(f"{BASE_URL}/hello")
    assert response.status_code == 200
    assert response.json() == "hello"
