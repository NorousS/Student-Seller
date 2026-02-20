# HH.ru Student Evaluator

**HH.ru Student Evaluator** — полнофункциональная платформа для оценки рыночной стоимости студентов и взаимодействия между студентами и работодателями. Система парсит вакансии с hh.ru, использует семантический поиск на основе векторных эмбеддингов для сопоставления навыков студентов с требованиями рынка труда, и предоставляет современный веб-интерфейс с JWT-аутентификацией, профилями пользователей, чатами и ролевой моделью доступа.

## Основные возможности

✅ **Парсинг вакансий** — автоматический сбор вакансий с hh.ru с извлечением навыков и зарплат  
✅ **Семантическое сопоставление** — интеллектуальное сравнение дисциплин студента с навыками рынка (Qdrant + Ollama)  
✅ **Оценка рыночной стоимости** — расчёт потенциальной зарплаты студента на основе его дисциплин  
✅ **JWT-аутентификация** — безопасный вход с тремя ролями: admin, student, employer  
✅ **Профили студентов** — самостоятельное редактирование: ФИО, группа, фото, «О себе», дисциплины с оценками  
✅ **Поиск работодателей** — поиск и просмотр анонимизированных профилей студентов  
✅ **Система контактов** — отправка запросов на контакт от работодателей к студентам  
✅ **Real-time чат** — WebSocket-чат между студентом и работодателем после принятия запроса  
✅ **React-фронтенд** — современный SPA на React 18 + TypeScript + Vite с роутингом  
✅ **Админ-панель** — standalone HTML панель по адресу `/admin` с JWT-аутентификацией

---

## Быстрый старт

### Запуск через Docker Compose (рекомендуется)

```powershell
# Клонировать репозиторий
git clone <repository-url>
cd test_antigravity

# Сборка фронтенда и запуск всех сервисов
docker-compose up --build -d

# Проверка работоспособности
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Открыть приложение в браузере
start http://localhost:8000
```

После запуска доступны:
- **Веб-интерфейс**: http://localhost:8000
- **API документация**: http://localhost:8000/docs
- **Админ-панель**: http://localhost:8000/admin
- **Qdrant UI**: http://localhost:6333/dashboard
- **PostgreSQL**: localhost:5432

---

## Локальная разработка

### Установка зависимостей

```powershell
# Установка uv (менеджер пакетов Python)
irm https://astral.sh/uv/install.ps1 | iex

# Установка Python-зависимостей
uv sync

# Установка Node.js зависимостей для фронтенда
cd frontend
npm install
cd ..
```

### Запуск сервисов

```powershell
# Запуск БД и внешних сервисов через Docker
docker-compose up db qdrant ollama -d

# Сборка фронтенда (production build)
cd frontend
npm run build
cd ..

# Запуск backend
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/hh_parser"
$env:QDRANT_URL = "http://localhost:6333"
$env:OLLAMA_URL = "http://localhost:11434"
$env:SECRET_KEY = "your-secret-key-here"
uv run uvicorn app.main:app --reload
```

### Frontend в режиме разработки

```powershell
# В отдельном терминале
cd frontend
npm run dev
# Frontend доступен на http://localhost:5173
```

---

## Тестирование

```powershell
# Запуск всех тестов (64 теста)
uv run pytest tests\\ -v

# Запуск конкретного файла тестов
uv run pytest tests\\test_auth.py -v

# Запуск с coverage
uv run pytest tests\\ --cov=app --cov-report=html
```

**Тестовые файлы:**
- `tests\\test_auth.py` — аутентификация и JWT
- `tests\\test_students.py` — CRUD студентов (admin)
- `tests\\test_student_profile.py` — профиль студента
- `tests\\test_employer.py` — функции работодателя
- `tests\\test_chat.py` — WebSocket чат

---

## Структура API

Все эндпоинты начинаются с `/api/v1/`. JWT-токен передаётся в заголовке `Authorization: Bearer <token>`.

### Аутентификация (`/api/v1/auth/`)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST  | `/api/v1/auth/register` | Регистрация (email, password, role) |
| POST  | `/api/v1/auth/login` | Вход (возвращает access + refresh token) |
| POST  | `/api/v1/auth/refresh` | Обновление access token |
| GET   | `/api/v1/auth/me` | Текущий пользователь |

### Студенты — Admin CRUD (`/api/v1/students/`)

Только для **admin**. Управление студентами.

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET   | `/api/v1/students/` | Список всех студентов |
| POST  | `/api/v1/students/` | Создание студента |
| GET   | `/api/v1/students/{id}` | Детали студента |
| PUT   | `/api/v1/students/{id}` | Редактирование студента |
| DELETE| `/api/v1/students/{id}` | Удаление студента |
| POST  | `/api/v1/students/{id}/disciplines` | Добавление дисциплин |

### Профиль студента (`/api/v1/profile/student/`)

Для роли **student**. Самостоятельное управление профилем.

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET   | `/api/v1/profile/student/me` | Мой профиль |
| PUT   | `/api/v1/profile/student/me` | Редактировать профиль |
| POST  | `/api/v1/profile/student/me/photo` | Загрузить фото |
| POST  | `/api/v1/profile/student/me/disciplines` | Добавить дисциплины |
| DELETE| `/api/v1/profile/student/me/disciplines/{id}` | Удалить дисциплину |
| GET   | `/api/v1/profile/student/me/contact-requests` | Мои запросы на контакт |
| POST  | `/api/v1/profile/student/me/contact-requests/{id}/accept` | Принять запрос |
| POST  | `/api/v1/profile/student/me/contact-requests/{id}/reject` | Отклонить запрос |

### Профиль работодателя (`/api/v1/profile/employer/`)

Для роли **employer**.

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET   | `/api/v1/profile/employer/me` | Мой профиль |
| PUT   | `/api/v1/profile/employer/me` | Редактировать профиль |

### Работодатель — поиск студентов (`/api/v1/employer/`)

Для роли **employer**. Поиск и контакт со студентами.

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET   | `/api/v1/employer/students` | Поиск студентов (анонимно) |
| GET   | `/api/v1/employer/students/{id}` | Полный профиль студента |
| POST  | `/api/v1/employer/contact-requests` | Отправить запрос на контакт |
| GET   | `/api/v1/employer/contact-requests` | Мои запросы |

### Вакансии (`/api/v1/vacancies/`)

| Метод | Эндпоинт | Описание | Доступ |
|-------|----------|----------|--------|
| POST  | `/api/v1/vacancies/parse` | Парсинг вакансий с hh.ru | Admin |
| GET   | `/api/v1/vacancies/` | Список вакансий | Все |
| GET   | `/api/v1/vacancies/tags` | Статистика тегов | Все |

### Оценка (`/api/v1/evaluation/`)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST  | `/api/v1/evaluation/evaluate` | Оценка рыночной стоимости |
| GET   | `/api/v1/evaluation/skills` | Навыки студента в терминах hh.ru |

**Параметры `/evaluate`:**
- `student_id` — ID студента
- `specialty` — специальность для фильтрации вакансий
- `top_k` (1–20, по умолчанию 5) — навыков на дисциплину
- `experience` — фильтр опыта: `noExperience`, `between1And3`, `between3And6`, `moreThan6`
- `excluded_skills` — навыки для исключения

### Чат (`/api/v1/chat/`, `/ws/chat/{request_id}`)

| Тип | Эндпоинт | Описание |
|-----|----------|----------|
| GET | `/api/v1/chat/{request_id}/messages` | История сообщений |
| POST| `/api/v1/chat/{request_id}/mark-read` | Отметить как прочитанные |
| WS  | `/ws/chat/{request_id}?token=<jwt>` | WebSocket для real-time чата |

---

## Технологии

### Backend
- **FastAPI** — асинхронный веб-фреймворк
- **SQLAlchemy 2.0** — ORM (async mode)
- **Pydantic v2** — валидация схем
- **PostgreSQL 16** — реляционная БД (asyncpg driver)
- **JWT** — аутентификация (passlib + PyJWT)

### AI/ML
- **Qdrant** — векторная БД (cosine distance, 768-dim)
- **Ollama** — генерация эмбеддингов (nomic-embed-text)

### Frontend
- **React 18** — UI-библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **React Router** — маршрутизация
- **Zustand** — state management

### Инфраструктура
- **Docker Compose** — оркестрация контейнеров
- **uv** — менеджер Python-пакетов
- **npm** — менеджер Node-пакетов
- **pytest** — тестирование (asyncio_mode=auto)

---

## Структура проекта

```
C:\\projects\\test_antigravity\\
│
├── app\\                          # Backend (FastAPI)
│   ├── main.py                   # Главный файл приложения
│   ├── models.py                 # SQLAlchemy модели
│   ├── schemas.py                # Pydantic схемы
│   ├── auth.py                   # JWT аутентификация
│   ├── config.py                 # Настройки (pydantic-settings)
│   ├── database.py               # Подключение к БД
│   ├── parser.py                 # hh.ru парсер
│   ├── vector_store.py           # Qdrant клиент
│   ├── embeddings.py             # Ollama эмбеддинги
│   ├── valuation.py              # Алгоритм оценки
│   ├── routers\\                 # API роутеры
│   │   ├── auth.py
│   │   ├── students.py           # Admin CRUD
│   │   ├── student_profile.py    # Student self-service
│   │   ├── employer.py           # Employer functions
│   │   ├── vacancies.py
│   │   ├── evaluation.py
│   │   └── chat.py
│   └── static\\                  # Статика
│       └── admin.html            # Legacy admin panel
│
├── frontend\\                     # Frontend (React + TypeScript)
│   ├── src\\
│   │   ├── pages\\               # Страницы (Login, Admin, Student, Employer)
│   │   ├── components\\          # React-компоненты
│   │   ├── store\\               # Zustand stores
│   │   ├── hooks\\               # Custom hooks
│   │   ├── api\\                 # API-клиенты
│   │   └── App.tsx               # Главный компонент
│   ├── public\\                  # Публичные файлы
│   ├── package.json
│   └── vite.config.ts
│
├── tests\\                        # Тесты (pytest)
│   ├── conftest.py               # Fixtures
│   ├── test_auth.py
│   ├── test_students.py
│   ├── test_student_profile.py
│   ├── test_employer.py
│   └── test_chat.py
│
├── Dockerfile                    # Multi-stage: Node + Python
├── docker-compose.yml            # app + postgres + qdrant + ollama
├── pyproject.toml                # Python dependencies (uv)
├── pytest.ini                    # Pytest config
├── README.md                     # Этот файл
├── ARCHITECTURE.md               # Архитектура системы
└── FULL_PROJECT_DOCUMENTATION.md # Полная документация

```

---

## Роли и доступ

### Admin
- CRUD студентов (создание, редактирование, удаление)
- Парсинг вакансий с hh.ru
- Просмотр статистики тегов
- Управление всеми сущностями системы

### Student
- Редактирование своего профиля (ФИО, группа, фото, «О себе»)
- Управление дисциплинами (добавление, удаление, оценки)
- Просмотр запросов на контакт от работодателей
- Принятие/отклонение запросов
- Чат с работодателями (после принятия)
- Оценка своей рыночной стоимости

### Employer
- Редактирование профиля (название компании, должность)
- Поиск студентов (просмотр анонимных профилей)
- Просмотр полного профиля студента по ID
- Отправка запросов на контакт
- Чат со студентами (после принятия)

---

## Полезные ссылки

- **API документация (Swagger UI)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Архитектура системы**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Подробная документация**: [FULL_PROJECT_DOCUMENTATION.md](FULL_PROJECT_DOCUMENTATION.md)
- **Как работает оценка**: [HOW_VALUATION_WORKS.md](HOW_VALUATION_WORKS.md)
- **Как работают теги**: [HOW_TAGS_WORK.md](HOW_TAGS_WORK.md)

---

## Лицензия

MIT License

