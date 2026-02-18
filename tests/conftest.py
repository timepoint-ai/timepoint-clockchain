import os
import shutil

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("SERVICE_API_KEY", "test-key")
os.environ.setdefault("FLASH_SERVICE_KEY", "flash-key")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _test_data_dir(tmp_path):
    seeds_src = os.path.join(os.path.dirname(__file__), "..", "data", "seeds.json")
    if os.path.exists(seeds_src):
        shutil.copy(seeds_src, tmp_path / "seeds.json")
    os.environ["DATA_DIR"] = str(tmp_path)
    yield
    os.environ.pop("DATA_DIR", None)


@pytest.fixture()
def service_key():
    return "test-key"


@pytest.fixture()
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture()
async def auth_client(service_key):
    from app.main import app
    transport = ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"X-Service-Key": service_key},
        ) as ac:
            yield ac
