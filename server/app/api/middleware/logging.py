from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logger import api_logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        api_logger.info("Request started", method=request.method, path=request.url.path)
        response = await call_next(request)
        api_logger.info("Request completed", method=request.method, path=request.url.path, status=response.status_code)
        return response

