# Copilot Instructions

## Project Overview

HH Parser — a FastAPI service that parses job vacancies from hh.ru (Russian job board), stores them in PostgreSQL, and evaluates student market value by semantically matching their university disciplines to hh.ru skills via vector embeddings (Qdrant + Ollama).

The primary language of the codebase (comments, docs, UI text, API messages) is **Russian**.

## Build & Run

```powershell
# Install dependencies
uv sync

# Run all services (app + PostgreSQL + Qdrant + Ollama)
docker-compose up --build -d

# Run app locally (requires PostgreSQL on localhost)
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/hh_parser"
uv run uvicorn app.main:app --reload
```

## Testing

Tests require a running PostgreSQL instance on `localhost:5432` (credentials: `postgres:postgres`). The test DB `hh_parser_test` is auto-created by fixtures.

```powershell
# Run all tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_students.py::test_create_student_simple -v
```

pytest is configured with `asyncio_mode = auto` — no need for `@pytest.mark.asyncio` on test functions, though the existing tests do use it.

## Architecture

**Three-database architecture:**
- **PostgreSQL** — vacancies, tags, students, disciplines, users, chat messages (SQLAlchemy async ORM)
- **Qdrant** — vector embeddings of hh.ru skills for semantic search (cosine distance, 768-dim)
- **Ollama** — generates embeddings via `nomic-embed-text` model (multilingual, supports Russian)

**Authentication:** JWT-based (passlib + PyJWT). Three roles: `admin`, `student`, `employer`. Protected via `get_current_user` and `require_role()` FastAPI dependencies in `app/auth.py`.

**Valuation flow:** Student disciplines → Ollama embeddings → Qdrant similarity search → match to hh.ru tags → weighted salary estimate from PostgreSQL. Weighting formula: `similarity × log1p(vacancy_count) × grade_coefficient`.

**Key services are module-level singletons:** `vector_store`, `embedding_service`, `hh_parser`, `settings` — instantiated at import time, not via DI.

## Code Conventions

- **Package manager:** `uv` (not pip). Use `uv sync`, `uv run`.
- **Async everywhere:** All DB access uses SQLAlchemy async (`AsyncSession`). All HTTP calls use `httpx.AsyncClient`.
- **Models use SQLAlchemy 2.0 mapped columns:** `Mapped[type]` with `mapped_column()`, not legacy `Column()`.
- **Schemas use Pydantic v2:** `model_config` or `class Config` with `from_attributes = True`.
- **Configuration via `pydantic-settings`:** All settings in `app/config.py` as a single `Settings` class, loaded from env vars / `.env`.
- **Router structure:** All API routes under `/api/v1/`, split into `routers/auth.py`, `routers/vacancies.py`, `routers/students.py`, `routers/evaluation.py`.
- **Auth pattern:** Admin-only endpoints use `dependencies=[Depends(require_role(UserRole.admin))]` on the router. Per-endpoint auth uses `Depends(require_role(...))` as a parameter.
- **DB sessions via FastAPI `Depends(get_db)`:** Session auto-commits on success, auto-rollbacks on exception.
- **Tests override `get_db`** with a savepoint-based session for isolation; tables are created/dropped per test function. Auth helper fixtures (`admin_headers`, `student_headers`, `employer_headers`) are in `conftest.py`.
