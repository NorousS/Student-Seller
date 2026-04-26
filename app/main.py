"""
FastAPI приложение для парсера вакансий hh.ru.
"""

import pathlib
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import create_tables, engine
from app.logging_config import configure_logging, get_logger
from app.middleware.db_metrics import instrument_async_engine
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import vacancies, students, evaluation, auth, student_profile, employer, chat, diagnostics, admin, partnership, landing, admin_disciplines
from app.vector_store import vector_store
from app.embeddings import embedding_service
from app.schemas import HealthResponse

configure_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = get_logger(__name__)


STATIC_DIR = pathlib.Path(__file__).parent / "static"
DIST_DIR = STATIC_DIR / "dist"
INDEX_HTML = DIST_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan события приложения.
    Создаём таблицы при старте, инициализируем Qdrant.
    """
    logger.info("Запуск приложения: начинаем инициализацию сервисов")

    if settings.PROMETHEUS_ENABLED:
        instrument_async_engine(engine)
        logger.info("Метрики SQLAlchemy-инструментирования включены")

    logger.info("Инициализация PostgreSQL: создание таблиц")
    await create_tables()
    logger.info("Инициализация PostgreSQL завершена")

    try:
        logger.info("Инициализация Qdrant: проверка и создание коллекций")
        await vector_store.init_collections()
        logger.info("Инициализация Qdrant завершена")
    except Exception as e:
        logger.warning(
            "Qdrant недоступен (можно запустить позже)",
            error=str(e),
            exc_info=True,
        )

    try:
        logger.info("Инициализация Ollama: проверка модели эмбеддингов")
        model_loaded = await embedding_service.ensure_model_loaded()
        if model_loaded:
            logger.info(
                "Инициализация Ollama завершена",
                model=embedding_service.model,
            )
        else:
            logger.warning(
                "Ollama недоступен или модель не подтверждена (можно запустить позже)",
                model=embedding_service.model,
            )
    except Exception as e:
        logger.warning(
            "Ollama недоступен (можно запустить позже)",
            error=str(e),
            exc_info=True,
        )

    logger.info("Инициализация приложения завершена")
    yield
    logger.info("Остановка приложения: завершение lifespan")


app = FastAPI(
    title="HH.ru Parser API",
    description="API для парсинга вакансий с hh.ru и анализа тегов/зарплат",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)

if settings.PROMETHEUS_ENABLED:
    Instrumentator().instrument(app)
    logger.info("Prometheus-инструментирование включено")

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(vacancies.router)
app.include_router(evaluation.router)
app.include_router(students.router)
app.include_router(student_profile.router)
app.include_router(employer.router)
app.include_router(chat.router)
app.include_router(diagnostics.router)
app.include_router(admin.router)
app.include_router(partnership.router)
app.include_router(admin_disciplines.router)
app.include_router(landing.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Проверка здоровья сервиса."""
    return HealthResponse(status="ok")


if settings.PROMETHEUS_ENABLED:
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        """Метрики Prometheus для скрейпинга."""
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Статические ассеты фронтенда (JS, CSS)
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

# Загрузки (фото студентов)
uploads_dir = STATIC_DIR / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


def _serve_spa():
    """Возвращает index.html для SPA-роутинга."""
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return HTMLResponse("<h1>Frontend not built</h1><p>Run: cd frontend && npm run build</p>", status_code=503)


@app.get("/", include_in_schema=False)
async def root():
    return _serve_spa()


@app.get("/admin-panel", include_in_schema=False)
async def admin_panel():
    """Старая админ-панель (standalone HTML)."""
    admin_html = STATIC_DIR / "admin.html"
    if admin_html.exists():
        return FileResponse(admin_html)
    return HTMLResponse("<h1>Admin panel not found</h1>", status_code=404)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_catch_all(full_path: str):
    """SPA catch-all: все неизвестные пути возвращают index.html."""
    return _serve_spa()
