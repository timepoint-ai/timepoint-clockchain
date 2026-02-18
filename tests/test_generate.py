import asyncio

import pytest
from unittest.mock import AsyncMock, patch


MOCK_FLASH_RESPONSE = {
    "id": "flash-uuid-123",
    "name": "Battle of Thermopylae",
    "slug": "battle-of-thermopylae",
    "year": -480,
    "month": "august",
    "day": 20,
    "time": "0600",
    "country": "greece",
    "region": "central-greece",
    "city": "thermopylae",
    "one_liner": "300 Spartans hold the pass against the Persian army",
    "tags": ["battle", "ancient-greece", "sparta"],
    "figures": ["Leonidas", "Xerxes"],
}


@pytest.mark.asyncio
async def test_generate_creates_job(auth_client):
    with patch(
        "app.workers.renderer.FlashClient.generate_sync",
        new_callable=AsyncMock,
        return_value=MOCK_FLASH_RESPONSE,
    ):
        resp = await auth_client.post(
            "/api/v1/generate",
            json={"query": "Battle of Thermopylae", "preset": "balanced"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_generate_and_poll_completion(auth_client):
    with patch(
        "app.workers.renderer.FlashClient.generate_sync",
        new_callable=AsyncMock,
        return_value=MOCK_FLASH_RESPONSE,
    ):
        resp = await auth_client.post(
            "/api/v1/generate",
            json={"query": "Battle of Thermopylae"},
        )
        job_id = resp.json()["job_id"]

        # Give background task time to complete
        await asyncio.sleep(0.5)

        resp = await auth_client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["path"] is not None
        assert "thermopylae" in data["path"]


@pytest.mark.asyncio
async def test_generate_adds_node_to_graph(auth_client):
    with patch(
        "app.workers.renderer.FlashClient.generate_sync",
        new_callable=AsyncMock,
        return_value=MOCK_FLASH_RESPONSE,
    ):
        resp = await auth_client.post(
            "/api/v1/generate",
            json={"query": "Battle of Thermopylae"},
        )
        job_id = resp.json()["job_id"]
        await asyncio.sleep(0.5)

        # Search should find the new node
        resp = await auth_client.get("/api/v1/search?q=thermopylae")
        assert resp.status_code == 200
        # Node was added as private by default, so search (public only) won't find it
        # Let's check via the job path
        job_resp = await auth_client.get(f"/api/v1/jobs/{job_id}")
        path = job_resp.json()["path"]
        assert path is not None


@pytest.mark.asyncio
async def test_job_not_found(auth_client):
    resp = await auth_client.get("/api/v1/jobs/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_publish_moment(auth_client):
    with patch(
        "app.workers.renderer.FlashClient.generate_sync",
        new_callable=AsyncMock,
        return_value=MOCK_FLASH_RESPONSE,
    ):
        resp = await auth_client.post(
            "/api/v1/generate",
            json={"query": "Battle of Thermopylae"},
        )
        job_id = resp.json()["job_id"]
        await asyncio.sleep(0.5)

        job_resp = await auth_client.get(f"/api/v1/jobs/{job_id}")
        path = job_resp.json()["path"].lstrip("/")

        # Publish
        resp = await auth_client.post(
            f"/api/v1/moments/{path}/publish",
            json={"visibility": "public"},
        )
        assert resp.status_code == 200
        assert resp.json()["visibility"] == "public"

        # Now search should find it
        resp = await auth_client.get("/api/v1/search?q=thermopylae")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_index_endpoint(auth_client):
    resp = await auth_client.post(
        "/api/v1/index",
        json={
            "path": "/1066/october/14/0900/united-kingdom/east-sussex/hastings/battle-of-hastings",
            "flash_timepoint_id": "flash-uuid-456",
            "metadata": {
                "name": "Battle of Hastings",
                "year": 1066,
                "month": "october",
                "day": 14,
                "one_liner": "William the Conqueror defeats Harold II",
                "tags": ["battle", "england"],
                "figures": ["William the Conqueror", "Harold II"],
            },
            "visibility": "public",
            "created_by": "system",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "indexed"

    # Should be searchable
    resp = await auth_client.get("/api/v1/search?q=hastings")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
