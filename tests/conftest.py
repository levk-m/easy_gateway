from unittest.mock import AsyncMock, patch

import httpx
import pytest

from easy_gateway.gateway.core import EasyGateway
from easy_gateway.router.router import Router


@pytest.fixture
def router():
    return Router()


@pytest.fixture
def gateway():
    return EasyGateway(config={})


@pytest.fixture
def gateway_config():
    return {
        "server": {"host": "0.0.0.0", "port": 8000},
        "redis": {"enabled": False},
        "routes": [
            {"path": "/api/*", "target": "https://backend.test/", "cache": False},
            {"path": "/users", "target": "https://users.test", "cache": False},
        ],
        "middlewares": [],
        "cors": {"allow_origins": ["https://frontend.test"]},
    }


@pytest.fixture
def configured_gateway(gateway_config):
    return EasyGateway(config=gateway_config)


@pytest.fixture
def asgi_client():
    def _make(gateway):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=gateway.app), base_url="http://test"
        )

    return _make


@pytest.fixture
def redis_mock():
    client = AsyncMock()
    return client


@pytest.fixture
def monkeypatch_redis():
    def _patch(redis_client=None):
        return patch(
            "easy_gateway.gateway.core.aioredis.from_url",
            new=AsyncMock(return_value=redis_client or AsyncMock()),
        )

    return _patch
