"""Инструментирование SQLAlchemy для метрик БД (Prometheus)."""

from __future__ import annotations

import threading
import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

DB_QUERY_TOTAL = Counter(
    "db_query_total",
    "Общее число SQL-запросов по типу операции",
    ("operation",),
)

DB_QUERY_LATENCY_SECONDS = Histogram(
    "db_query_latency_seconds",
    "Латентность SQL-запросов в секундах по типу операции",
    ("operation",),
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

DB_ACTIVE_CONNECTIONS = Gauge(
    "db_active_connections",
    "Количество активных (checked-out) соединений SQLAlchemy",
)

_KNOWN_OPERATIONS = {"SELECT", "INSERT", "UPDATE", "DELETE", "MERGE"}
_active_connections = 0
_active_connections_lock = threading.Lock()


def _extract_operation(statement: str) -> str:
    if not statement:
        return "OTHER"

    token = statement.lstrip().split(maxsplit=1)[0].upper()
    if token == "WITH":
        upper_stmt = statement.upper()
        for op in _KNOWN_OPERATIONS:
            if op in upper_stmt:
                return op
        return "OTHER"

    if token in _KNOWN_OPERATIONS:
        return token

    return "OTHER"


def _record_query_metrics(execution_context: Any | None) -> None:
    if execution_context is None:
        return

    operation = getattr(execution_context, "_db_metrics_operation", "OTHER")
    started_at = getattr(execution_context, "_db_metrics_started_at", None)

    DB_QUERY_TOTAL.labels(operation=operation).inc()

    if started_at is None:
        return

    duration = time.perf_counter() - started_at
    if duration >= 0:
        DB_QUERY_LATENCY_SECONDS.labels(operation=operation).observe(duration)


def _before_cursor_execute(
    conn: Any,  # noqa: ARG001
    cursor: Any,  # noqa: ARG001
    statement: str,
    parameters: Any,  # noqa: ARG001
    context: Any,
    executemany: bool,  # noqa: ARG001
) -> None:
    context._db_metrics_started_at = time.perf_counter()
    context._db_metrics_operation = _extract_operation(statement)


def _after_cursor_execute(
    conn: Any,  # noqa: ARG001
    cursor: Any,  # noqa: ARG001
    statement: str,  # noqa: ARG001
    parameters: Any,  # noqa: ARG001
    context: Any,
    executemany: bool,  # noqa: ARG001
) -> None:
    _record_query_metrics(context)


def _handle_error(exception_context: Any) -> None:
    _record_query_metrics(getattr(exception_context, "execution_context", None))


def _on_checkout(
    dbapi_connection: Any,  # noqa: ARG001
    connection_record: Any,  # noqa: ARG001
    connection_proxy: Any,  # noqa: ARG001
) -> None:
    global _active_connections
    with _active_connections_lock:
        _active_connections += 1
        DB_ACTIVE_CONNECTIONS.set(_active_connections)


def _on_checkin(
    dbapi_connection: Any,  # noqa: ARG001
    connection_record: Any,  # noqa: ARG001
) -> None:
    global _active_connections
    with _active_connections_lock:
        _active_connections = max(0, _active_connections - 1)
        DB_ACTIVE_CONNECTIONS.set(_active_connections)


_instrumented_engines: set[int] = set()


def instrument_async_engine(async_engine: AsyncEngine) -> None:
    """Подключает SQLAlchemy listeners к AsyncEngine (однократно)."""
    sync_engine: Engine = async_engine.sync_engine
    if id(sync_engine) in _instrumented_engines:
        return

    event.listen(sync_engine, "before_cursor_execute", _before_cursor_execute)
    event.listen(sync_engine, "after_cursor_execute", _after_cursor_execute)
    event.listen(sync_engine, "handle_error", _handle_error)
    event.listen(sync_engine, "checkout", _on_checkout)
    event.listen(sync_engine, "checkin", _on_checkin)

    _instrumented_engines.add(id(sync_engine))

