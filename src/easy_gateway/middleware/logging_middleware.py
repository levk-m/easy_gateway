import time

from fastapi import Request, Response
from loguru import logger

from easy_gateway.middleware.base import Middleware


class LoggingMiddleware(Middleware):
    async def before_request(self, req: Request) -> Request:
        req.state.start_time = time.monotonic()
        logger.debug(f"🫣 Request! Path -> {req.url.path}, method -> {req.method}.")
        return req

    async def after_response(self, req: Request, res: Response) -> Response:
        elapsed: float = time.monotonic() - req.state.start_time
        logger.debug(
            f"🥳 All Done! Response status-code -> {res.status_code}, time -> {elapsed}."
        )
        return res
