"""
FastAPI приложение для парсера вакансий hh.ru.
"""

import pathlib
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.database import create_tables
from app.routers import vacancies, students, evaluation
from app.vector_store import vector_store
from app.embeddings import embedding_service
from app.schemas import HealthResponse


STATIC_DIR = pathlib.Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan события приложения.
    Создаём таблицы при старте, инициализируем Qdrant.
    """
    await create_tables()
    # Инициализируем коллекции Qdrant
    try:
        await vector_store.init_collections()
    except Exception as e:
        print(f"Qdrant не доступен (можно запустить позже): {e}")
    # Проверяем модель в Ollama
    try:
        await embedding_service.ensure_model_loaded()
    except Exception as e:
        print(f"Ollama не доступен (можно запустить позже): {e}")
    yield


app = FastAPI(
    title="HH.ru Parser API",
    description="API для парсинга вакансий с hh.ru и анализа тегов/зарплат",
    version="1.0.0",
    lifespan=lifespan,
)

# Подключаем роутеры
app.include_router(vacancies.router)
app.include_router(evaluation.router)
app.include_router(students.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Проверка здоровья сервиса."""
    return HealthResponse(status="ok")


@app.get("/", include_in_schema=False)
async def root():
    """Редирект на фронтенд."""
    return RedirectResponse(url="/static/index.html")


# Статические файлы (фронтенд)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
