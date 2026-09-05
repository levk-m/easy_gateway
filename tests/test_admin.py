import httpx
import pytest

from easy_gateway.gateway.core import EasyGateway


@pytest.fixture
def authed_headers():
    return {"Authorization": "Basic YWRtaW46YWRtaW4="}


async def _client(gateway):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=gateway.app), base_url="http://test"
    )


async def test_add_route(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.post(
            "/admin/add_route",
            params={"path": "/new", "target": "https://new.test"},
            headers=authed_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert configured_gateway.router.find_target("/new")[0] == "https://new.test/new"


async def test_delete_route(configured_gateway, authed_headers):
    configured_gateway.router.add_route("/tmp", "https://tmp.test")
    async with await _client(configured_gateway) as client:
        resp = await client.delete(
            "/admin/del_route", params={"path": "/tmp"}, headers=authed_headers
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


async def test_delete_route_not_found(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.delete(
            "/admin/del_route", params={"path": "/missing"}, headers=authed_headers
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


async def test_all_routes(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.get("/admin/all_routes", headers=authed_headers)
    body = resp.json()
    assert resp.status_code == 200
    assert "/api" in body["Prefix routes"]
    assert "/users" in body["Exact routes"]


async def test_all_routes_empty(authed_headers):
    empty_gateway = EasyGateway(config={})
    async with await _client(empty_gateway) as client:
        resp = await client.get("/admin/all_routes", headers=authed_headers)
    body = resp.json()
    assert body["Exact routes"] == "It's empty :("
    assert body["Prefix routes"] == "It's empty :("


async def test_update_route(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.put(
            "/admin/update//users",
            params={"new_target": "https://updated.test"},
            headers=authed_headers,
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert (
        configured_gateway.router.find_target("/users")[0]
        == "https://updated.test/users"
    )


async def test_update_route_not_found(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.put(
            "/admin/update/missing",
            params={"new_target": "https://x.test"},
            headers=authed_headers,
        )
    assert resp.status_code == 500


async def test_check_route_found(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.get("/admin/check//users", headers=authed_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["target"] == "https://users.test/users"


async def test_check_route_not_found(configured_gateway, authed_headers):
    async with await _client(configured_gateway) as client:
        resp = await client.get("/admin/check/nope", headers=authed_headers)
    assert resp.status_code == 200
    assert "not found" in resp.text


async def test_admin_requires_auth(configured_gateway):
    async with await _client(configured_gateway) as client:
        resp = await client.get("/admin/all_routes")
    assert resp.status_code == 401


async def test_admin_rejects_bad_credentials(configured_gateway):
    headers = {"Authorization": "Basic YWRtaW46d3Jvbmc="}
    async with await _client(configured_gateway) as client:
        resp = await client.get("/admin/all_routes", headers=headers)
    assert resp.status_code == 401
