# syntax=docker/dockerfile:1

# --- Stage 1: Build React frontend ---
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python backend ---
FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Рабочая директория
WORKDIR /app

# Копируем файлы зависимостей и README (нужен для hatchling)
COPY pyproject.toml uv.lock* README.md ./

# Устанавливаем зависимости через uv. Dev-зависимости нужны test service в docker compose.
RUN uv sync --dev --no-cache

# Копируем код приложения
COPY app ./app
<<<<<<< HEAD
COPY scripts ./scripts
=======
>>>>>>> github/main
COPY tests ./tests
COPY pytest.ini ./
COPY .env* ./

# Копируем собранный фронтенд (Vite builds to ../app/static/dist relative to frontend/)
COPY --from=frontend-build /app/static/dist ./app/static/dist

# Указываем порт
EXPOSE 8000

# Запускаем через uv run
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
