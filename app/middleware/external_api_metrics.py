"""Prometheus-метрики для внешних API (Ollama, hh.ru, Qdrant)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from prometheus_client import Counter, Histogram

EXTERNAL_API_REQUESTS_TOTAL = Counter(
    "external_api_requests_total",
    "Общее число запросов к внешним сервисам",
    ("service", "operation", "status"),
)

EXTERNAL_API_LATENCY_SECONDS = Histogram(
    "external_api_latency_seconds",
    "Латентность запросов к внешним сервисам в секундах",
    ("service", "operation"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)


@asynccontextmanager
async def track_external_api_call(service: str, operation: str) -> AsyncIterator[None]:
    """Трекер метрик для одного внешнего вызова."""
    started_at = time.perf_counter()
    status = "success"

    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.perf_counter() - started_at
        EXTERNAL_API_REQUESTS_TOTAL.labels(
            service=service,
            operation=operation,
            status=status,
        ).inc()
        if duration >= 0:
            EXTERNAL_API_LATENCY_SECONDS.labels(
                service=service,
                operation=operation,
            ).observe(duration)
