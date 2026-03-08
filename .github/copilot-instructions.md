# Copilot Instructions

## Project Overview

HH Parser — a FastAPI service that parses job vacancies from hh.ru (Russian job board), stores them in PostgreSQL, and evaluates student market value by semantically matching their university disciplines to hh.ru skills via vector embeddings (Qdrant + Ollama).

The primary language of the codebase (comments, docs, UI text, API messages) is **Russian**.

## Build & Run

```powershell
# Run all services via Docker (preferred)
docker-compose up --build -d

# Or run locally — requires PostgreSQL, Qdrant, Ollama on localhost
uv sync
uv run uvicorn app.main:app --reload

# Frontend dev server (proxies API to :8000)
cd frontend && npm install && npm run dev
```

Production builds the frontend into `app/static/dist/` and FastAPI serves the SPA via a catch-all route. No separate frontend container.

## Testing

Tests require PostgreSQL on `localhost:5432` (credentials: `postgres:postgres`). The test DB `hh_parser_test` is auto-created by fixtures.

```powershell
# All backend tests
uv run pytest tests/ -v

# Single test
uv run pytest tests/test_students.py::test_create_student_simple -v

# Frontend E2E (requires app running on :8000)
cd frontend && npx playwright test

# Lint (uses default ruff config)
uv run ruff check app/
```

`asyncio_mode = auto` in pytest.ini — no need for `@pytest.mark.asyncio` on test functions.

## Architecture

### Three-database system
- **PostgreSQL** — all relational data: users, students, vacancies, tags, chat messages, employer profiles (SQLAlchemy async ORM)
- **Qdrant** — vector embeddings of hh.ru skills for semantic search (cosine distance, 768-dim)
- **Ollama** — generates embeddings via `nomic-embed-text` model (multilingual, supports Russian)

### Valuation flow
Student disciplines → Ollama embeddings → Qdrant similarity search → match to hh.ru tags → weighted salary estimate from PostgreSQL. Formula: `similarity × log1p(vacancy_count) × grade_coefficient`.

### Authentication
JWT-based (passlib + PyJWT), HS256. Three roles: `admin`, `student`, `employer`. Access tokens expire in 30 min, refresh tokens in 7 days. Dependencies `get_current_user` and `require_role()` in `app/auth.py`.

### SPA serving
Vite builds frontend to `app/static/dist/`. FastAPI mounts `/assets` for JS/CSS, `/static/uploads` for photos, and a catch-all `/{path}` returns `index.html`. The admin panel at `/admin` is a separate static HTML file, not part of the React SPA.

### Key singletons
`vector_store`, `embedding_service`, `hh_parser`, `settings` — instantiated at module import time, not via DI. Initialized in the FastAPI lifespan handler.

## Backend Conventions

- **Package manager:** `uv` (not pip). Always use `uv sync`, `uv run`.
- **Async everywhere:** All DB access uses `AsyncSession`. All HTTP calls use `httpx.AsyncClient`.
- **SQLAlchemy 2.0 style:** `Mapped[type]` with `mapped_column()`, not legacy `Column()`.
- **Pydantic v2 schemas:** Use `from_attributes = True` in model config for ORM mode.
- **Settings:** Single `Settings(BaseSettings)` class in `app/config.py`, loaded from env vars / `.env`.
- **Router prefix:** All API routes under `/api/v1/`. WebSocket chat at `/ws/chat/{id}`.
- **Auth on routers:** Admin-only routers use `dependencies=[Depends(require_role(UserRole.admin))]`. Per-endpoint auth uses `Depends(require_role(...))` as a parameter.
- **DB sessions:** `Depends(get_db)` yields an auto-committing session. Tests override `get_db` with a savepoint-based session that rolls back after each test.
- **Schema distinction:** `StudentResponse` has basic fields; `StudentProfileResponse` adds `about_me`, `photo_url`, `work_ready_date`. Use the correct one based on endpoint context.
- **Flush, don't commit in middleware:** After adding related rows (e.g., `StudentDiscipline`), use `db.flush()` + `db.expire_all()` before querying — not `db.commit()`.
- **Auth endpoints:** Register returns HTTP 201, login returns 200 with `access_token` + `refresh_token`.

## Frontend Conventions

- **Stack:** React 19 + TypeScript + Vite. No Tailwind — uses custom CSS with CSS variables (dark theme).
- **State:** React Context (`AuthContext`) for auth; no Redux/Zustand. JWT stored in `localStorage`.
- **API client:** Axios instance in `frontend/src/api/client.ts` with `baseURL: '/api/v1'`. Interceptors auto-attach JWT and refresh on 401.
- **Types:** TypeScript interfaces in `frontend/src/api/types.ts` mirror backend Pydantic schemas.
- **Build output:** `npm run build` → `../app/static/dist/` (consumed by backend). Vite base is `/`.
- **Form inputs:** Login/register forms use `<input type="email">` / `<input type="password">` without label `for`/`id` linking — use type selectors in Playwright, not `getByLabel`.

## Testing Conventions

- **Fixtures in `tests/conftest.py`:** `admin_headers`, `student_headers`, `employer_headers` create users via API and return `{"Authorization": "Bearer ..."}` dicts.
- **DB isolation:** Each test gets its own transaction that rolls back. Tables are created/dropped per test function.
- **E2E tests:** Playwright specs in `frontend/e2e/`. Config targets `http://127.0.0.1:8000`.
- **Test DB URL:** Derived from `DATABASE_URL` env var; defaults to `localhost:5432`. In Docker, set `DATABASE_URL=...@db:5432`.

## Workflow

- Always write tests and self-validate changes.
- Run E2E tests via Playwright MCP after changes.
- All services run in Docker (`docker-compose up --build -d`).