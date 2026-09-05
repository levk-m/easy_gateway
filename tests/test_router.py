import pytest
from fastapi import HTTPException

from easy_gateway.router.router import RouteType


def test_add_exact_route(router):
    router.add_route("/api/users", "https://example.com")
    target, remaining, _ = router.find_target("/api/users")
    assert target == "https://example.com/api/users"
    assert remaining == ""


def test_add_prefix_route(router):
    router.add_route("/api/*", "https://example.com")
    target, remaining, _ = router.find_target("/api/users/123")
    assert target == "https://example.com"
    assert remaining == "/users/123"


def test_route_not_found(router):
    target, _, _ = router.find_target("/nonexistent")
    assert target is None


def test_exact_overrides_prefix(router):
    router.add_route("/api/users", "https://users.example.com")
    router.add_route("/api/*", "https://api.example.com")
    _, _, route_type = router.find_target("/api/users")
    assert route_type == RouteType.EXACT


def test_longest_prefix_wins(router):
    router.add_route("/api/*", "https://api.example.com")
    router.add_route("/api/users/*", "https://users.example.com")
    target, remaining, _ = router.find_target("/api/users/admin/settings")
    assert target == "https://users.example.com"
    assert remaining == "/admin/settings"


def test_delete_route(router):
    router.add_route("/api", "https://example.com")
    assert router.delete_route("/api") is True
    assert router.find_target("/api")[0] is None


def test_delete_nonexistent_route(router):
    assert router.delete_route("/nope") is False


def test_delete_prefix_route(router):
    router.add_route("/api/*", "https://example.com")
    assert router.delete_route("/api") is True
    assert router.find_target("/api/x")[0] is None


def test_update_route(router):
    router.add_route("/api", "https://old.com")
    router.update_route("/api", "https://new.com")
    target, _, _ = router.find_target("/api")
    assert target == "https://new.com/api"


def test_update_prefix_route(router):
    router.add_route("/api/*", "https://old.com/")
    assert router.update_route("/api/*", "https://new.com/") is True
    target, remaining, _ = router.find_target("/api/users")
    assert target == "https://new.com"
    assert remaining == "/users"


def test_update_route_not_found(router):
    with pytest.raises(HTTPException) as exc:
        router.update_route("/missing", "https://new.com")
    assert exc.value.status_code == 404


def test_update_prefix_route_not_found(router):
    with pytest.raises(HTTPException) as exc:
        router.update_route("/missing/*", "https://new.com")
    assert exc.value.status_code == 404


def test_update_bare_prefix_key(router):
    router.add_route("/api/*", "https://old.com/")
    assert router.update_route("/api", "https://new.com/") is True
    target, remaining, route_type = router.find_target("/api/users")
    assert target == "https://new.com"
    assert remaining == "/users"
    assert route_type == RouteType.PREFIX


def test_prefix_find_target_returns_prefix_type(router):
    router.add_route("/api/*", "https://example.com")
    _, _, route_type = router.find_target("/api/users")
    assert route_type == RouteType.PREFIX


def test_rejects_invalid_target(router):
    with pytest.raises(HTTPException) as exc:
        router.add_route("/path", "localhost:8080")
    assert exc.value.status_code == 400
