import asyncio
from unittest.mock import AsyncMock, patch

import pytest


MOCK_FLASH_RESPONSE = {
    "id": "flash-integration-uuid",
    "name": "Fall of the Berlin Wall",
    "slug": "fall-of-the-berlin-wall",
    "year": 1989,
    "month": "november",
    "day": 9,
    "time": "2300",
    "country": "germany",
    "region": "berlin",
    "city": "berlin",
    "one_liner": "The Berlin Wall falls, reuniting East and West Germany",
    "tags": ["cold-war", "germany", "politics"],
    "figures": ["Mikhail Gorbachev", "Helmut Kohl"],
}


@pytest.mark.asyncio
async def test_full_integration(auth_client):
    # 1. Health check
    resp = await auth_client.get("/health")
    assert resp.status_code == 200
    health = resp.json()
    assert health["status"] == "healthy"
    assert health["nodes"] == 5
    assert health["edges"] == 3

    # 2. Verify seeds loaded — browse root
    resp = await auth_client.get("/api/v1/browse")
    assert resp.status_code == 200
    segments = [i["segment"] for i in resp.json()["items"]]
    assert "-44" in segments
    assert "1969" in segments

    # 3. Search for Caesar
    resp = await auth_client.get("/api/v1/search?q=caesar")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert "Caesar" in results[0]["name"]

    # 4. Get a specific moment
    resp = await auth_client.get(
        "/api/v1/moments/1945/july/16/0530/united-states/new-mexico/socorro/trinity-test"
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Trinity Test"

    # 5. Get graph stats
    resp = await auth_client.get("/api/v1/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_nodes"] == 5
    assert stats["total_edges"] == 3

    # 6. Generate a new moment (mocked Flash)
    with patch(
        "app.workers.renderer.FlashClient.generate_sync",
        new_callable=AsyncMock,
        return_value=MOCK_FLASH_RESPONSE,
    ):
        resp = await auth_client.post(
            "/api/v1/generate",
            json={"query": "Fall of the Berlin Wall", "visibility": "public"},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        # Wait for background processing
        await asyncio.sleep(0.5)

        # 7. Poll job status
        resp = await auth_client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        job = resp.json()
        assert job["status"] == "completed"
        assert job["path"] is not None

    # 8. Verify new node in search
    resp = await auth_client.get("/api/v1/search?q=berlin")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert "Berlin" in results[0]["name"]

    # 9. Verify stats updated
    resp = await auth_client.get("/api/v1/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_nodes"] == 6

    # 10. Browse now includes new year
    resp = await auth_client.get("/api/v1/browse")
    assert resp.status_code == 200
    segments = [i["segment"] for i in resp.json()["items"]]
    assert "1989" in segments

    # 11. Get neighbors of Apollo 11
    resp = await auth_client.get(
        "/api/v1/graph/neighbors/1969/july/20/2056/united-states/florida/cape-canaveral/apollo-11-moon-landing"
    )
    assert resp.status_code == 200
    neighbors = resp.json()
    assert len(neighbors) >= 1

    # 12. Random returns a public moment
    resp = await auth_client.get("/api/v1/random")
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "public"
