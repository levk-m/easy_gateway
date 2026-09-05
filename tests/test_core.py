import base64
import json
from unittest.mock import AsyncMock

import httpx

from easy_gateway.gateway.core import EasyGateway


async def _client(gateway):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=gateway.app), base_url="http://test"
    )


def test_init_no_config():
    gateway = EasyGateway(config={})
    assert gateway.config == {}
    assert gateway.cache_exp == 180
    assert len(gateway.middlewares) == 0
    assert gateway.redis is None


def test_init_default_config_path(monkeypatch, tmp_path, caplog):
    conf = tmp_path / "easy_conf.yaml"
    conf.write_text("server:\n  host: 127.0.0.1\n  port: 9000\n")
    monkeypatch.chdir(tmp_path)
    gateway = EasyGateway()
    assert gateway.config["server"]["port"] == 9000


def test_init_populates_routes(gateway_config):
    gateway = EasyGateway(config=gateway_config)
    assert gateway.router.find_target("/api/users")[0] == "https://backend.test"
    assert gateway.router.find_target("/users")[0] == "https://users.test/users"


def test_init_populates_middleware_from_config():
    config = {
        "middlewares": [
            {"name": "LoggingMiddleware", "enabled": True},
            {"name": "RateLimitMiddleware", "enabled": True, "requests_per_minute": 5},
            {"name": "DisabledMiddleware", "enabled": False},
            {"name": "UnknownMiddleware", "enabled": True},
        ]
    }
    gateway = EasyGateway(config=config)
    from easy_gateway.middleware.logging_middleware import LoggingMiddleware
    from easy_gateway.middleware.rate_limit_middleware import RateLimitMiddleware

    assert isinstance(gateway.middlewares[0], LoggingMiddleware)
    assert isinstance(gateway.middlewares[1], RateLimitMiddleware)
    assert gateway.middlewares[1].requests_per_minute == 5
    assert len(gateway.middlewares) == 2


def test_init_no_routes_warns():
    gateway = EasyGateway(config={})
    assert len(gateway.router.exact_routes) == 0
    assert len(gateway.router.prefix_routes) == 0


def test_generate_cache_key_deterministic():
    key1 = EasyGateway.generate_cache_key("/api/x", "GET", {"a": "1", "b": "2"})
    key2 = EasyGateway.generate_cache_key("/api/x", "GET", {"b": "2", "a": "1"})
    assert key1 == key2
    assert key1.startswith("cache:/api/x:GET:")


def test_generate_cache_key_no_params():
    key = EasyGateway.generate_cache_key("/health", "GET", {})
    assert key.startswith("cache:/health:GET:")


async def test_check_route_cache_exact(configured_gateway):
    gateway = EasyGateway(
        config={
            "redis": {"enabled": True},
            "routes": [{"path": "/users", "target": "https://x.test", "cache": True}],
        }
    )
    assert gateway.check_route_cache("/users") is True
    assert gateway.check_route_cache("/other") is False


async def test_check_route_cache_prefix(configured_gateway):
    gateway = EasyGateway(
        config={
            "redis": {"enabled": True},
            "routes": [{"path": "/api/*", "target": "https://x.test/", "cache": True}],
        }
    )
    assert gateway.check_route_cache("/api/users") is True


def test_check_route_cache_disabled_redis(gateway_config):
    gateway = EasyGateway(config=gateway_config)
    assert gateway.check_route_cache("/users") is False


async def test_get_set_invalidate_cache(configured_gateway, monkeypatch_redis):
    redis = AsyncMock()
    with monkeypatch_redis(redis):
        gateway = EasyGateway(
            config={
                "redis": {"enabled": True, "expire_time": 60},
                "routes": [
                    {"path": "/users", "target": "https://x.test", "cache": True}
                ],
            }
        )
        await gateway._setup_cache()
        assert gateway.redis is not None

    key = gateway.generate_cache_key("/users", "GET", {})
    await gateway.set_cache_data(key, {"status_code": 200, "body": "aGk="})
    redis.set.assert_called_once()

    redis.get.return_value = json.dumps({"status_code": 200, "body": "aGk="})
    data = await gateway.get_cache_data(key)
    assert data["status_code"] == 200

    redis.scan.return_value = (0, [b"cache:/users:GET:abc"])
    await gateway.invalidate_cache("/users")
    redis.delete.assert_called_once()


async def test_cache_operations_without_redis(configured_gateway):
    assert await configured_gateway.get_cache_data("k") is None
    await configured_gateway.set_cache_data("k", {"a": 1})
    await configured_gateway.invalidate_cache("/x")


async def test_setup_cache_disabled(monkeypatch_redis):
    gateway = EasyGateway(config={"redis": {"enabled": False}})
    await gateway._setup_cache()
    assert gateway.redis is None


async def test_setup_cache_connection_error(monkeypatch_redis):
    redis = AsyncMock()
    redis.ping.side_effect = Exception("boom")
    with monkeypatch_redis(redis):
        gateway = EasyGateway(config={"redis": {"enabled": True}})
        await gateway._setup_cache()
    assert gateway.redis is None


async def test_welcome_endpoint(configured_gateway):
    async with await _client(configured_gateway) as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert "easy gateway is running" in resp.json()["Status"]


async def test_health_endpoint_no_redis(configured_gateway):
    async with await _client(configured_gateway) as client:
        resp = await client.get("/health")
    body = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "healthy"
    assert body["checks"]["cache"] == "ok"


async def test_health_endpoint_with_redis(monkeypatch_redis):
    redis = AsyncMock()
    with monkeypatch_redis(redis):
        gateway = EasyGateway(config={"redis": {"enabled": True, "routes": []}})
        await gateway._setup_cache()
    async with await _client(gateway) as client:
        resp = await client.get("/health")
    assert resp.json()["checks"]["cache"] == "ok"


async def test_catch_all_returns_cached_response(configured_gateway, monkeypatch_redis):
    redis = AsyncMock()
    redis.get.return_value = json.dumps(
        {
            "status_code": 201,
            "body": base64.b64encode(b"cached-body").decode(),
            "headers": {"X-Cache": "hit"},
        }
    )
    with monkeypatch_redis(redis):
        gateway = EasyGateway(
            config={
                "redis": {"enabled": True},
                "routes": [
                    {"path": "/users", "target": "https://x.test", "cache": True}
                ],
            }
        )
        await gateway._setup_cache()

    async with await _client(gateway) as client:
        resp = await client.get("/users")

    assert resp.status_code == 201
    assert resp.content == b"cached-body"
    assert resp.headers["X-Cache"] == "hit"


async def test_catch_all_invalidates_cache_on_non_get(
    configured_gateway, monkeypatch_redis
):
    redis = AsyncMock()
    redis.scan.return_value = (0, [b"cache:/users:GET:abc"])
    with monkeypatch_redis(redis):
        gateway = EasyGateway(
            config={
                "redis": {"enabled": True, "routes": []},
                "routes": [
                    {"path": "/users", "target": "https://x.test", "cache": True}
                ],
            }
        )
        await gateway._setup_cache()

    class FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(204)

    async with await _client(gateway) as client:
        gateway.client = httpx.AsyncClient(transport=FakeTransport())
        resp = await client.post("/users", content=b"")
        await gateway.client.aclose()

    assert resp.status_code == 204
    redis.scan.assert_called()
    redis.delete.assert_called_once()


async def test_catch_all_proxies_request(configured_gateway):
    class FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(
                200, json={"path": request.url.path, "method": request.method}
            )

    async def _client_with_transport():
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=configured_gateway.app),
            base_url="http://test",
        )

    async with await _client_with_transport() as client:
        configured_gateway.client = httpx.AsyncClient(transport=FakeTransport())
        resp = await client.get("/api/users/42")
        await configured_gateway.client.aclose()

    assert resp.status_code == 200
    assert resp.json()["path"] == "/users/42"


async def test_catch_all_reaches_correct_exact_target(configured_gateway):
    """Prefix routes proxy to the target with the remaining path appended."""

    class FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, json={"url": str(request.url)})

    async with await _client(configured_gateway) as client:
        configured_gateway.client = httpx.AsyncClient(transport=FakeTransport())
        resp = await client.get("/users")
        await configured_gateway.client.aclose()

    assert resp.status_code == 200
    assert resp.json()["url"].endswith("/users/")


async def test_catch_all_404_no_route(configured_gateway):
    async with await _client(configured_gateway) as client:
        configured_gateway.client = httpx.AsyncClient()
        resp = await client.get("/completely/missing")
        await configured_gateway.client.aclose()
    assert resp.status_code == 404


async def test_catch_all_connect_error(configured_gateway):
    class FailingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            raise httpx.ConnectError("nope")

    async with await _client(configured_gateway) as client:
        configured_gateway.client = httpx.AsyncClient(transport=FailingTransport())
        resp = await client.get("/users")
        await configured_gateway.client.aclose()
    assert resp.status_code == 502


async def test_catch_all_timeout_error(configured_gateway):
    class TimeoutTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            raise httpx.ReadTimeout("slow")

    async with await _client(configured_gateway) as client:
        configured_gateway.client = httpx.AsyncClient(transport=TimeoutTransport())
        resp = await client.get("/users")
        await configured_gateway.client.aclose()
    assert resp.status_code == 504
