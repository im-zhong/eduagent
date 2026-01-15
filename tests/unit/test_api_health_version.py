from __future__ import annotations

import httpx
import pytest

from eduagent.api.api import api


async def _get_json(path: str) -> tuple[int, dict[str, str]]:
    transport = httpx.ASGITransport(app=api)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    return response.status_code, response.json()


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    status, payload = await _get_json("/api/v1/health")
    assert status == 200
    assert payload["status"] == "healthy"
    assert payload["service"] == "eduagent-api"


@pytest.mark.asyncio
async def test_version_endpoint() -> None:
    status, payload = await _get_json("/api/v1/version")
    assert status == 200
    assert payload["name"] == "eduagent"
    assert payload["version"] == "1.0.0"
