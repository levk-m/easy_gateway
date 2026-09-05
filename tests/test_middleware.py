from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from easy_gateway.middleware.base import Middleware
from easy_gateway.middleware.logging_middleware import LoggingMiddleware
from easy_gateway.middleware.rate_limit_middleware import RateLimitMiddleware


@pytest.fixture
def request_mock():
    req = AsyncMock(spec=Request)
    req.state = type("State", (), {})()
    req.client = type("Client", (), {"host": "127.0.0.1"})()
    req.url = type("URL", (), {"path": "/test"})()
    req.method = "GET"
    return req


async def test_base_middleware_passthrough():
    mw = Middleware()
    req = AsyncMock(spec=Request)
    result = await mw.before_request(req)
    assert result is req


async def test_base_middleware_after_response_passthrough():
    mw = Middleware()
    res = AsyncMock()
    assert await mw.after_response(None, res) is res


async def test_logging_middleware_sets_start_time(request_mock):
    mw = LoggingMiddleware()
    await mw.before_request(request_mock)
    assert getattr(request_mock.state, "start_time", None) is not None


async def test_rate_limit_allows_within_limit(request_mock):
    mw = RateLimitMiddleware(requests_per_minute=2)
    result = await mw.before_request(request_mock)
    assert result is request_mock
    assert len(mw.requests["127.0.0.1"]) == 1


async def test_rate_limit_blocks_over_limit(request_mock):
    mw = RateLimitMiddleware(requests_per_minute=2)
    await mw.before_request(request_mock)
    await mw.before_request(request_mock)

    result = await mw.before_request(request_mock)
    assert isinstance(result, JSONResponse)
    assert result.status_code == 429
    assert result.headers["Retry-After"] == "60"


async def test_rate_limit_cleans_old_requests(request_mock):
    mw = RateLimitMiddleware(requests_per_minute=10)
    mw.requests["127.0.0.1"] = [100.0, 200.0]

    with patch(
        "easy_gateway.middleware.rate_limit_middleware.time.time", return_value=300.0
    ):
        await mw.before_request(request_mock)

    assert mw.requests["127.0.0.1"] == [300.0]


async def test_rate_limit_unknown_client():
    req = AsyncMock(spec=Request)
    req.client = None
    req.state = type("State", (), {})()
    req.url = type("URL", (), {"path": "/test"})()
    req.method = "GET"

    mw = RateLimitMiddleware(requests_per_minute=1)
    result = await mw.before_request(req)
    assert result is req
    assert "unknown" in mw.requests
