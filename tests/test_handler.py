from unittest.mock import AsyncMock

from fastapi import Request
from fastapi.responses import JSONResponse
from httpx import Response as HTTPXResponse

from easy_gateway.gateway.handler import (
    process_request_middleware,
    process_response_middleware,
)
from easy_gateway.middleware.base import Middleware


async def test_process_request_no_middleware():
    req = AsyncMock(spec=Request)
    result_req, result_res = await process_request_middleware([], req)
    assert result_req is req
    assert result_res is None


async def test_process_request_passes_through_in_order():
    calls = []

    class First(Middleware):
        async def before_request(self, req):
            calls.append("first")
            req.state.seen = ["first"]
            return req

    class Second(Middleware):
        async def before_request(self, req):
            calls.append("second")
            req.state.seen.append("second")
            return req

    req = AsyncMock(spec=Request)
    req.state = type("State", (), {})()
    result_req, response = await process_request_middleware([First(), Second()], req)
    assert response is None
    assert result_req.state.seen == ["first", "second"]
    assert calls == ["first", "second"]


async def test_process_request_early_return():
    blocking = JSONResponse({"blocked": True}, status_code=429)

    class Reporter(Middleware):
        def __init__(self, silently: bool):
            self.silently = silently
            self.called = False

        async def before_request(self, req):
            self.called = True
            if self.silently:
                return blocking
            return req

    first = Reporter(silently=True)
    second = Reporter(silently=False)

    req = AsyncMock(spec=Request)
    req.state = type("State", (), {})()
    result_req, response = await process_request_middleware([second, first], req)

    assert second.called is True
    assert first.called is True
    assert response is blocking


async def test_process_response_middleware_reverse_order():
    order = []

    class Tracker(Middleware):
        def __init__(self, name):
            self.name = name

        async def after_response(self, req, res):
            order.append(self.name)
            return res

    response = HTTPXResponse(200, content=b"ok", headers={"X-Test": "1"})
    result = await process_response_middleware(
        [Tracker("first"), Tracker("second")], AsyncMock(), response
    )

    assert order == ["second", "first"]
    assert result.status_code == 200
    assert result.body == b"ok"
    assert result.headers["X-Test"] == "1"


async def test_process_request_middleware_modifies_request_object():
    class Mutator(Middleware):
        async def before_request(self, req):
            req.state.modified = True
            return req

    req = AsyncMock(spec=Request)
    req.state = type("State", (), {})()
    result_req, response = await process_request_middleware([Mutator()], req)
    assert result_req.state.modified is True
    assert response is None
