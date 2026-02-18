import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "timepoint-clockchain"
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_root_returns_200(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "timepoint-clockchain"
