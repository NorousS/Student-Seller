# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Рабочая директория
WORKDIR /app

# Копируем файлы зависимостей и README (нужен для hatchling)
COPY pyproject.toml uv.lock* README.md ./

# Устанавливаем зависимости через uv
# --frozen: использует uv.lock если есть
# --no-cache: не кэшируем для уменьшения размера образа
RUN uv sync --no-dev --no-cache

# Копируем код приложения
COPY app ./app
COPY .env* ./

# Указываем порт
EXPOSE 8000

# Запускаем через uv run
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
