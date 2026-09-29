from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        started_at = perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{perf_counter() - started_at:.6f}"
        return response

