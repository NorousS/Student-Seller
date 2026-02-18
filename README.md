# HH.ru Parser API

Сервис для парсинга вакансий с hh.ru по ключевому слову. Извлекает теги (ключевые навыки), зарплату и сохраняет данные в PostgreSQL.

## Быстрый старт

```powershell
# Запуск через Docker Compose
docker-compose up --build -d

# Проверка здоровья
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Парсинг вакансий
$body = @{ query = "python"; count = 10 } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/parse" -Body $body -ContentType "application/json"
```

## API Endpoints

### POST /api/v1/parse
Парсит вакансии по ключевому слову.

**Request:**
```json
{
  "query": "python",
  "count": 50
}
```

**Response:**
```json
{
  "total_parsed": 50,
  "tags": [
    {"name": "Python", "count": 45},
    {"name": "SQL", "count": 30}
  ],
  "average_salary": 150000.0
}
```

### GET /api/v1/vacancies
Получает сохранённые вакансии из БД.

### GET /health
Проверка здоровья сервиса.

## Локальная разработка

```powershell
# Установка uv (если нет)
irm https://astral.sh/uv/install.ps1 | iex

# Установка зависимостей
uv sync

# Запуск PostgreSQL
docker-compose up db -d

# Запуск приложения
# Запуск приложения
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/hh_parser"
uv run uvicorn app.main:app --reload

# Заполнение тестовыми данными (студенты)
python seed_students.py
```

## Работа со студентами

### POST /api/v1/students
Создать студента с дисциплинами.

**Request:**
```json
{
  "full_name": "Иванов Иван",
  "group_name": "CS-101",
  "disciplines": ["Python", "SQL"]
}
```

### GET /api/v1/students/{id}
Получить профиль студента.

**Response:**
```json
{
  "id": 1,
  "full_name": "Иванов Иван",
  "group_name": "CS-101",
  "disciplines": [
    {"name": "Python", "id": 1},
    {"name": "SQL", "id": 2}
  ]
}
```

### POST /api/v1/students/{id}/disciplines
Добавить дисциплины студенту.

**Request:**
```json
{
  "disciplines": ["Docker", "FastAPI"]
}
```

### POST /api/v1/students/{id}/evaluate
Оценка рыночной стоимости студента.

**Параметры:**
- `specialty` (обязательный) — специальность для фильтрации
- `top_k` (1–20, по умолчанию 5) — навыков на дисциплину
- `experience` — фильтр опыта: `noExperience`, `between1And3`, `between3And6`, `moreThan6`
- `excluded_skills` — навыки для исключения из расчёта

**Пример:**
```powershell
# Базовая оценка
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/students/1/evaluate?specialty=Python%20разработчик&top_k=3"

# С исключением навыков
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/students/1/evaluate?specialty=Python&top_k=5&excluded_skills=Django&excluded_skills=Flask"
```

## Технологии

- **FastAPI** — веб-фреймворк
- **SQLAlchemy** — ORM для PostgreSQL
- **Qdrant** — векторная база данных
- **Ollama** — локальные LLM и эмбеддинги
- **httpx** — асинхронный HTTP-клиент
- **uv** — менеджер зависимостей
- **Docker** — контейнеризация

