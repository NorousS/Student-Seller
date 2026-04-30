"""Middleware для логирования HTTP-запросов и ответов."""

from __future__ import annotations

import time
import uuid

import jwt
import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

EXCLUDED_PATHS = {"/health", "/metrics"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Логирует метод, путь, статус, длительность, user_id и request_id."""

    @staticmethod
    def _extract_user_id(request: Request) -> int | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            sub = payload.get("sub")
            if sub is None:
                return None
            return int(sub)
        except (jwt.InvalidTokenError, ValueError, TypeError):
            return None

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        started = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        user_id = self._extract_user_id(request)
        status_code = 500

        request.state.request_id = request_id
        request.state.user_id = user_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "HTTP request completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id,
            )
            structlog.contextvars.clear_contextvars()

