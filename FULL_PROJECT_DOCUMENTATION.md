# Полная документация проекта: HH.ru Student Evaluator

## Оглавление

1. [Описание проекта](#описание-проекта)
2. [Архитектура системы](#архитектура-системы)
3. [Стек технологий](#стек-технологий)
4. [Структура файлов](#структура-файлов)
5. [База данных (PostgreSQL)](#база-данных-postgresql)
6. [Векторная база данных (Qdrant)](#векторная-база-данных-qdrant)
7. [Эмбеддинги (Ollama)](#эмбеддинги-ollama)
8. [Алгоритм оценки стоимости студента](#алгоритм-оценки-стоимости-студента)
9. [JWT-аутентификация и роли](#jwt-аутентификация-и-роли)
10. [API-эндпоинты](#api-эндпоинты)
11. [WebSocket чат](#websocket-чат)
12. [Фронтенд (React SPA)](#фронтенд-react-spa)
13. [Админ-панель (standalone HTML)](#админ-панель-standalone-html)
14. [Парсинг вакансий с hh.ru](#парсинг-вакансий-с-hhru)
15. [Профили пользователей](#профили-пользователей)
16. [Система контактов](#система-контактов)
17. [Инфраструктура (Docker)](#инфраструктура-docker)
18. [Тестирование](#тестирование)
19. [Развёртывание](#развёртывание)

---

## Описание проекта

**HH.ru Student Evaluator** — полнофункциональная веб-платформа для оценки рыночной стоимости студентов и организации взаимодействия между студентами и работодателями. Система использует технологии машинного обучения для семантического сопоставления академических знаний с требованиями рынка труда.

### Зачем это нужно

**Для студентов:**
- Понять, насколько их образование востребовано на рынке
- Получить объективную оценку потенциальной зарплаты
- Связаться с работодателями напрямую
- Создать профиль с фото и описанием

**Для работодателей:**
- Найти студентов с нужными навыками
- Просмотреть анонимизированные профили
- Отправить запрос на контакт
- Общаться со студентами через встроенный чат

**Для вузов и администраторов:**
- Анализировать соответствие программ обучения рынку труда
- Управлять базой студентов
- Парсить актуальные вакансии
- Просматривать статистику востребованных навыков

### Ключевые возможности

✅ **Парсинг вакансий** — автоматический сбор вакансий с hh.ru с извлечением навыков (тегов) и зарплат  
✅ **Семантическое сопоставление** — интеллектуальное сравнение дисциплин студента с навыками рынка через векторные эмбеддинги (Qdrant + Ollama)  
✅ **Оценка рыночной стоимости** — взвешенный расчёт потенциальной зарплаты с учётом similarity, популярности навыка и оценок  
✅ **JWT-аутентификация** — безопасный вход с тремя ролями: admin, student, employer  
✅ **Профили студентов** — самостоятельное редактирование: ФИО, группа, фото, «О себе», дисциплины с оценками (3/4/5)  
✅ **Профили работодателей** — название компании, должность  
✅ **Поиск студентов** — работодатели могут искать студентов с нужными навыками  
✅ **Система контактов** — отправка запросов от работодателей, принятие/отклонение студентами  
✅ **Real-time чат** — WebSocket-чат между студентом и работодателем после принятия запроса  
✅ **React-фронтенд** — современный SPA на React 18 + TypeScript + Vite с роутингом по ролям  
✅ **Админ-панель** — standalone HTML панель по адресу `/admin` с JWT-аутентификацией и 4 вкладками  
✅ **Comprehensive tests** — 64 теста на pytest с покрытием всех ключевых функций

---

## Архитектура системы

Система построена по микросервисной архитектуре с разделением на frontend, backend и внешние сервисы:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                              │
│                                                                     │
│  ┌────────────────────────────────┐  ┌───────────────────────────┐ │
│  │   React SPA (Vite + TS)        │  │  Legacy Admin Panel       │ │
│  │                                │  │  (admin.html)             │ │
│  │  Pages:                        │  │                           │ │
│  │   • /login, /register          │  │  JWT-авторизация          │ │
│  │   • /admin (admin dashboard)   │  │  Standalone HTML          │ │
│  │   • /student (profile + chat)  │  │                           │ │
│  │   • /employer (search + chat)  │  └───────────────────────────┘ │
│  │                                │                                │
│  │  State: Zustand                │                                │
│  │  Routing: React Router         │                                │
│  └────────────────────────────────┘                                │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
                       │ HTTP REST API + WebSocket
                       │
┌──────────────────────┴──────────────────────────────────────────────┐
│                        Backend Layer (FastAPI)                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  API Routers (/api/v1/*)                                   │   │
│  │  ┌──────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐ │   │
│  │  │   auth   │ │  students  │ │  employer  │ │vacancies  │ │   │
│  │  └──────────┘ └────────────┘ └────────────┘ └───────────┘ │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐ │   │
│  │  │student_profile│ │  evaluation  │ │       chat         │ │   │
│  │  └──────────────┘ └──────────────┘ └────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  WebSocket Handler                                          │   │
│  │  /ws/chat/{request_id}?token=<jwt>                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Core Services                                              │   │
│  │  • auth.py — JWT токены, проверка ролей                    │   │
│  │  • parser.py — парсинг hh.ru                               │   │
│  │  • valuation.py — алгоритм оценки стоимости                │   │
│  │  • embeddings.py — Ollama клиент                           │   │
│  │  • vector_store.py — Qdrant клиент                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Data Layer (SQLAlchemy 2.0 async)                         │   │
│  │  • models.py — User, Student, Vacancy, Tag, Message, etc.  │   │
│  │  • schemas.py — Pydantic v2 валидация                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────┬────────────────┬──────────────────┬────────────────────────┘
         │                │                  │
    ┌────┴─────┐    ┌────┴────┐      ┌──────┴──────┐
    │PostgreSQL│    │ Qdrant  │      │   Ollama    │
    │    16    │    │ v1.13.2 │      │   latest    │
    └──────────┘    └─────────┘      └─────────────┘
```

### Основные компоненты

1. **Frontend Layer** — два интерфейса:
   - **React SPA** — современный интерфейс с роутингом для всех ролей
   - **Legacy Admin Panel** — standalone HTML для быстрого доступа администраторов

2. **Backend Layer (FastAPI)** — асинхронный API-сервер с JWT-аутентификацией, WebSocket-чатом, роутерами для каждой роли

3. **PostgreSQL** — хранение пользователей, студентов, вакансий, тегов, сообщений

4. **Qdrant** — векторная БД для семантического поиска навыков

5. **Ollama** — генерация эмбеддингов (nomic-embed-text, 768-dim)

---

## Стек технологий

### Backend

| Технология | Версия | Назначение |
|------------|--------|------------|
| **Python** | 3.12 | Язык программирования |
| **FastAPI** | latest | Асинхронный веб-фреймворк |
| **SQLAlchemy** | 2.0+ | ORM (async mode) |
| **Pydantic** | v2 | Валидация схем и настроек |
| **asyncpg** | latest | Асинхронный PostgreSQL драйвер |
| **passlib** | latest | Хеширование паролей (bcrypt) |
| **PyJWT** | latest | Создание и проверка JWT-токенов |
| **httpx** | latest | Асинхронный HTTP-клиент для hh.ru API |
| **qdrant-client** | latest | Python SDK для Qdrant |
| **python-multipart** | latest | Обработка form-data для загрузки файлов |

### Frontend

| Технология | Версия | Назначение |
|------------|--------|------------|
| **React** | 18 | UI-библиотека |
| **TypeScript** | 5.x | Статическая типизация |
| **Vite** | 5.x | Сборщик и dev-сервер |
| **React Router** | 6.x | Клиентский роутинг |
| **Zustand** | latest | Легковесный state management |
| **Axios** | latest | HTTP-клиент для API |

### AI/ML

| Технология | Версия | Назначение |
|------------|--------|------------|
| **Qdrant** | 1.13.2 | Векторная БД (cosine distance) |
| **Ollama** | latest | Локальный inference сервер |
| **nomic-embed-text** | latest | Мультиязычная модель эмбеддингов (768-dim) |

### Инфраструктура

| Технология | Версия | Назначение |
|------------|--------|------------|
| **PostgreSQL** | 16-alpine | Реляционная БД |
| **Docker** | latest | Контейнеризация |
| **Docker Compose** | latest | Оркестрация контейнеров |
| **uv** | latest | Менеджер Python-пакетов |
| **npm** | latest | Менеджер Node.js пакетов |

### Тестирование

| Технология | Версия | Назначение |
|------------|--------|------------|
| **pytest** | latest | Фреймворк тестирования |
| **pytest-asyncio** | latest | Поддержка async тестов |
| **httpx** | latest | TestClient для FastAPI |

---

## Структура файлов

```
C:\projects\test_antigravity\
│
├── app\                          # Backend (FastAPI)
│   ├── main.py                   # Главный файл приложения, CORS, роутеры
│   ├── models.py                 # SQLAlchemy модели (User, Student, Vacancy, etc.)
│   ├── schemas.py                # Pydantic схемы для валидации
│   ├── auth.py                   # JWT аутентификация, get_current_user, require_role
│   ├── config.py                 # Настройки (pydantic-settings из .env)
│   ├── database.py               # Async engine, sessionmaker, Base
│   ├── parser.py                 # hh.ru парсер вакансий
│   ├── vector_store.py           # Qdrant клиент (upsert, search)
│   ├── embeddings.py             # Ollama клиент для эмбеддингов
│   ├── valuation.py              # Алгоритм оценки рыночной стоимости
│   │
│   ├── routers\                  # API роутеры
│   │   ├── auth.py               # /api/v1/auth/* (register, login, refresh, me)
│   │   ├── students.py           # /api/v1/students/* (Admin CRUD)
│   │   ├── student_profile.py    # /api/v1/profile/student/* (Self-service)
│   │   ├── employer.py           # /api/v1/employer/* (Search, contact requests)
│   │   ├── vacancies.py          # /api/v1/vacancies/* (Parsing, list, tags)
│   │   ├── evaluation.py         # /api/v1/evaluation/* (Evaluate, skills)
│   │   └── chat.py               # /api/v1/chat/* + /ws/chat/* (Messages, WebSocket)
│   │
│   └── static\                   # Статические файлы
│       ├── admin.html            # Legacy admin panel
│       └── uploads\              # Загруженные фото студентов
│
├── frontend\                     # Frontend (React + TypeScript + Vite)
│   ├── src\
│   │   ├── pages\                # Страницы
│   │   │   ├── Login.tsx         # Страница входа
│   │   │   ├── Register.tsx      # Страница регистрации
│   │   │   ├── StudentPanel.tsx  # Панель студента
│   │   │   └── EmployerPanel.tsx # Панель работодателя
│   │   │
│   │   ├── components\           # React-компоненты
│   │   │   ├── Header.tsx        # Шапка с навигацией
│   │   │   ├── ChatWindow.tsx    # Окно чата
│   │   │   ├── StudentCard.tsx   # Карточка студента
│   │   │   └── ...
│   │   │
│   │   ├── store\                # Zustand stores
│   │   │   ├── authStore.ts      # Управление аутентификацией
│   │   │   └── chatStore.ts      # Управление чатами
│   │   │
│   │   ├── hooks\                # Custom React hooks
│   │   │   ├── useAuth.ts        # Hook для работы с auth
│   │   │   └── useWebSocket.ts   # Hook для WebSocket
│   │   │
│   │   ├── api\                  # API-клиенты
│   │   │   ├── auth.ts           # Запросы к /api/v1/auth/*
│   │   │   ├── students.ts       # Запросы к /api/v1/students/*
│   │   │   └── ...
│   │   │
│   │   ├── styles\               # CSS/SCSS файлы
│   │   ├── App.tsx               # Главный компонент с роутингом
│   │   └── main.tsx              # Entry point
│   │
│   ├── public\                   # Публичные файлы
│   │   └── favicon.ico
│   │
│   ├── package.json              # Node.js зависимости
│   ├── vite.config.ts            # Конфигурация Vite
│   └── tsconfig.json             # TypeScript конфигурация
│
├── tests\                        # Тесты (pytest)
│   ├── conftest.py               # Fixtures (async_client, test users)
│   ├── test_auth.py              # Тесты аутентификации
│   ├── test_students.py          # Тесты Admin CRUD
│   ├── test_student_profile.py   # Тесты self-service студента
│   ├── test_employer.py          # Тесты функций работодателя
│   └── test_chat.py              # Тесты WebSocket чата
│
├── Dockerfile                    # Multi-stage: Node (frontend) + Python (backend)
├── docker-compose.yml            # Оркестрация: app, postgres, qdrant, ollama
├── pyproject.toml                # Python зависимости (uv)
├── pytest.ini                    # Pytest конфигурация (asyncio_mode=auto)
├── .env.example                  # Пример файла окружения
│
├── README.md                     # Быстрый старт и основная информация
├── ARCHITECTURE.md               # Подробная архитектура системы
├── FULL_PROJECT_DOCUMENTATION.md # Этот файл
├── HOW_VALUATION_WORKS.md        # Как работает алгоритм оценки
└── HOW_TAGS_WORK.md              # Как работают теги и парсинг
```

---

## База данных (PostgreSQL)

### Схема базы данных

#### Таблица `users` — Пользователи системы

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `email` | VARCHAR(255) | Email (unique, index) |
| `password_hash` | VARCHAR(255) | Хеш пароля (bcrypt) |
| `role` | ENUM | Роль: `admin`, `student`, `employer` (index) |
| `is_active` | BOOLEAN | Активен ли пользователь |
| `created_at` | TIMESTAMP | Дата регистрации |

**Связи:**
- `user` ← `student` (1:1, CASCADE при удалении пользователя)
- `user` ← `employer_profile` (1:1, CASCADE при удалении)

#### Таблица `students` — Профили студентов

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `user_id` | INTEGER (FK) | Ссылка на `users.id` (unique, nullable, SET NULL) |
| `full_name` | VARCHAR(200) | ФИО студента (index) |
| `group_name` | VARCHAR(50) | Номер группы |
| `about_me` | TEXT | Описание «О себе» |
| `photo_path` | VARCHAR(500) | Путь к фото (`/uploads/...`) |
| `created_at` | TIMESTAMP | Дата создания профиля |

**Связи:**
- `student` → `user` (Many-to-One)
- `student` ← `student_disciplines` (One-to-Many, CASCADE)

#### Таблица `disciplines` — Учебные дисциплины

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `name` | VARCHAR(200) | Название дисциплины (unique, index) |

**Связи:**
- `discipline` ← `student_disciplines` (One-to-Many, CASCADE)

#### Таблица `student_disciplines` — Дисциплины студентов с оценками

| Колонка | Тип | Описание |
|---------|-----|----------|
| `student_id` | INTEGER (PK, FK) | Ссылка на `students.id` (CASCADE) |
| `discipline_id` | INTEGER (PK, FK) | Ссылка на `disciplines.id` (CASCADE) |
| `grade` | INTEGER | Оценка: 3, 4 или 5 |

**Composite PK**: (`student_id`, `discipline_id`)

#### Таблица `vacancies` — Вакансии с hh.ru

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `hh_id` | VARCHAR(50) | ID вакансии на hh.ru (unique, index) |
| `url` | VARCHAR(500) | URL вакансии |
| `title` | VARCHAR(500) | Название вакансии |
| `salary_from` | INTEGER | Зарплата от (nullable) |
| `salary_to` | INTEGER | Зарплата до (nullable) |
| `salary_currency` | VARCHAR(10) | Валюта (RUR, USD, EUR) |
| `experience` | VARCHAR(50) | Опыт работы (index): `noExperience`, `between1And3`, `between3And6`, `moreThan6` |
| `search_query` | VARCHAR(200) | Запрос, по которому найдена (index) |
| `created_at` | TIMESTAMP | Дата парсинга |

**Связи:**
- `vacancy` ← `vacancy_tag` (Many-to-Many через промежуточную таблицу)

#### Таблица `tags` — Навыки (ключевые навыки из вакансий)

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `name` | VARCHAR(200) | Название навыка (unique, index) |

**Связи:**
- `tag` ← `vacancy_tag` (Many-to-Many)

#### Таблица `vacancy_tag` — Связь вакансий и тегов (Many-to-Many)

| Колонка | Тип | Описание |
|---------|-----|----------|
| `vacancy_id` | INTEGER (PK, FK) | Ссылка на `vacancies.id` (CASCADE) |
| `tag_id` | INTEGER (PK, FK) | Ссылка на `tags.id` (CASCADE) |

**Composite PK**: (`vacancy_id`, `tag_id`)

#### Таблица `employer_profiles` — Профили работодателей

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `user_id` | INTEGER (FK) | Ссылка на `users.id` (unique, CASCADE) |
| `company_name` | VARCHAR(200) | Название компании |
| `position` | VARCHAR(200) | Должность |
| `created_at` | TIMESTAMP | Дата создания профиля |

**Связи:**
- `employer_profile` → `user` (Many-to-One)

#### Таблица `contact_requests` — Запросы на контакт

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `employer_id` | INTEGER (FK, index) | Ссылка на `users.id` (работодатель, CASCADE) |
| `student_id` | INTEGER (FK, index) | Ссылка на `students.id` (студент, CASCADE) |
| `status` | ENUM | Статус: `pending`, `accepted`, `rejected` |
| `created_at` | TIMESTAMP | Дата создания запроса |
| `responded_at` | TIMESTAMP | Дата ответа (nullable) |

**Связи:**
- `contact_request` → `user` (employer)
- `contact_request` → `student`
- `contact_request` ← `messages` (One-to-Many, CASCADE)

#### Таблица `messages` — Сообщения в чате

| Колонка | Тип | Описание |
|---------|-----|----------|
| `id` | INTEGER (PK) | Уникальный идентификатор |
| `contact_request_id` | INTEGER (FK, index) | Ссылка на `contact_requests.id` (CASCADE) |
| `sender_id` | INTEGER (FK) | Ссылка на `users.id` (отправитель, CASCADE) |
| `text` | TEXT | Текст сообщения |
| `is_read` | BOOLEAN | Прочитано ли сообщение |
| `created_at` | TIMESTAMP | Дата отправки |

**Связи:**
- `message` → `contact_request` (Many-to-One)
- `message` → `user` (sender)

### Миграции

**Текущая реализация**: Создание таблиц происходит через `Base.metadata.create_all()` при старте приложения (в `app.main.py`).

**Для production**: Рекомендуется использовать Alembic для версионирования миграций:
```bash
# Инициализация Alembic
alembic init alembic

# Создание миграции
alembic revision --autogenerate -m "Initial migration"

# Применение миграций
alembic upgrade head
```

---

## Векторная база данных (Qdrant)

### Коллекция `hh_skills`

Qdrant хранит векторные представления всех навыков (тегов) из вакансий hh.ru.

**Параметры коллекции:**
- **Vector size**: 768 (размерность nomic-embed-text)
- **Distance metric**: Cosine (косинусное расстояние, от 0 до 2, чем меньше — тем ближе)
- **Payload**: `{"tag_name": str, "tag_id": int}`

### Процесс индексации

1. Парсинг вакансий извлекает теги (навыки)
2. Для каждого нового тега генерируется эмбеддинг через Ollama
3. Вектор и payload загружаются в Qdrant через `upsert()`

**Пример кода** (из `app.vector_store.py`):
```python
async def upsert_tag_embedding(tag_id: int, tag_name: str, embedding: list[float]):
    client.upsert(
        collection_name="hh_skills",
        points=[{
            "id": tag_id,
            "vector": embedding,
            "payload": {"tag_name": tag_name, "tag_id": tag_id}
        }]
    )
```

### Семантический поиск

Когда студенту нужно найти навыки по дисциплине:
1. Генерируется эмбеддинг дисциплины (например, "Программирование на Python")
2. Выполняется поиск top-K ближайших векторов в Qdrant
3. Возвращаются навыки с similarity score

**Пример запроса**:
```python
results = client.search(
    collection_name="hh_skills",
    query_vector=discipline_embedding,
    limit=5  # top_k
)
# results = [
#   {score: 0.08, payload: {"tag_name": "Python", "tag_id": 123}},
#   {score: 0.15, payload: {"tag_name": "FastAPI", "tag_id": 456}},
#   ...
# ]
```

**Важно**: Score — это **расстояние** (чем меньше, тем лучше). Для similarity используется `1 - score/2`.

---

## Эмбеддинги (Ollama)

### Модель: nomic-embed-text

**Характеристики:**
- **Размерность**: 768
- **Языки**: Мультиязычная (поддерживает русский и английский)
- **Контекст**: До 8192 токенов
- **Open source**: Бесплатная и локальная

### API

Ollama предоставляет HTTP API для генерации эмбеддингов:

**Endpoint**: `POST http://ollama:11434/api/embeddings`

**Request**:
```json
{
  "model": "nomic-embed-text",
  "prompt": "Программирование на Python"
}
```

**Response**:
```json
{
  "embedding": [0.123, -0.456, 0.789, ...] // 768 чисел
}
```

### Использование в коде

**Из `app.embeddings.py`**:
```python
async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30.0
        )
        return response.json()["embedding"]
```

### Batch embeddings

Для ускорения обработки нескольких дисциплин одновременно используется параллельная генерация:

```python
import asyncio

async def get_batch_embeddings(texts: list[str]) -> list[list[float]]:
    tasks = [get_embedding(text) for text in texts]
    return await asyncio.gather(*tasks)
```

---

## Алгоритм оценки стоимости студента

### Обзор

Алгоритм рассчитывает потенциальную зарплату студента на основе его дисциплин. Процесс состоит из нескольких этапов:

1. **Фильтрация вакансий** — по специальности и опыту
2. **Семантический поиск навыков** — для каждой дисциплины
3. **Расчёт зарплаты** — взвешенная сумма с учётом similarity, популярности, оценки
4. **Confidence score** — уверенность в оценке

### Детальное описание

#### Шаг 1: Фильтрация вакансий по специальности

**Входные данные:**
- `specialty` — специальность (например, "Python разработчик")
- `experience` — фильтр опыта (`noExperience`, `between1And3`, etc.)

**Процесс:**
1. Генерируется эмбеддинг специальности через Ollama
2. В Qdrant ищутся вакансии с похожими `search_query`
3. Из PostgreSQL загружаются только релевантные вакансии

**SQL-запрос** (упрощённо):
```sql
SELECT * FROM vacancies
WHERE id IN (relevant_vacancy_ids)
  AND (experience = 'noExperience' OR experience IS NULL);
```

#### Шаг 2: Семантический поиск навыков для каждой дисциплины

**Для каждой дисциплины студента:**
1. Загрузить название и оценку (grade) из БД
2. Сгенерировать эмбеддинг дисциплины через Ollama
3. Найти top-K ближайших навыков в Qdrant

**Пример**:
```
Дисциплина: "Программирование на Python" (grade: 5)
  → Эмбеддинг: [0.123, -0.456, ...]
  → Top-5 навыков из Qdrant:
     1. Python (distance: 0.08, similarity: 0.96)
     2. FastAPI (distance: 0.15, similarity: 0.925)
     3. Django (distance: 0.18, similarity: 0.91)
     4. SQLAlchemy (distance: 0.22, similarity: 0.89)
     5. Pytest (distance: 0.25, similarity: 0.875)
```

#### Шаг 3: Расчёт средней зарплаты для каждого навыка

Для каждого найденного навыка:
1. Найти все релевантные вакансии с этим тегом
2. Вычислить среднюю зарплату

**SQL-запрос**:
```sql
SELECT AVG((v.salary_from + v.salary_to) / 2.0) as avg_salary,
       COUNT(*) as vacancy_count
FROM vacancies v
JOIN vacancy_tag vt ON v.id = vt.vacancy_id
JOIN tags t ON vt.tag_id = t.id
WHERE t.name = 'Python'
  AND v.id IN (relevant_vacancy_ids)
  AND v.salary_from IS NOT NULL
  AND v.salary_to IS NOT NULL;
```

**Пример результата**:
```
Python: avg_salary = 200,000, vacancy_count = 450
FastAPI: avg_salary = 180,000, vacancy_count = 120
```

#### Шаг 4: Взвешенный расчёт итоговой зарплаты

**Формула**:
```
weighted_salary = Σ (similarity × log1p(vacancy_count) × grade_coefficient × avg_salary)
total_weight = Σ (similarity × log1p(vacancy_count) × grade_coefficient)
estimated_salary = weighted_salary / total_weight
```

**Компоненты:**
- `similarity` — семантическая близость (0.0–1.0)
- `log1p(vacancy_count)` — логарифм популярности навыка (избегает доминирования супер-популярных навыков)
- `grade_coefficient` — коэффициент оценки: {3: 0.8, 4: 0.9, 5: 1.0}
- `avg_salary` — средняя зарплата по навыку

**Пример расчёта**:
```python
# Дисциплина "Программирование на Python" с оценкой 5
skills = [
    {"name": "Python", "similarity": 0.96, "salary": 200_000, "count": 450},
    {"name": "FastAPI", "similarity": 0.925, "salary": 180_000, "count": 120},
]

grade_coef = 1.0  # оценка 5
weighted = 0
total_weight = 0

for skill in skills:
    weight = skill["similarity"] * log1p(skill["count"]) * grade_coef
    weighted += weight * skill["salary"]
    total_weight += weight

estimated_salary = weighted / total_weight
# ≈ 195,000 рублей
```

#### Шаг 5: Confidence Score

**Confidence** показывает, насколько можно доверять оценке. Зависит от количества найденных навыков:

```python
confidence = 1 - exp(-total_matches / 20)
```

- `total_matches = 5` → confidence ≈ 0.22 (низкая)
- `total_matches = 20` → confidence ≈ 0.63 (средняя)
- `total_matches = 50` → confidence ≈ 0.92 (высокая)

### Исключение навыков

Параметр `excluded_skills` позволяет исключить нерелевантные навыки из расчёта:

```
POST /api/v1/evaluation/evaluate?excluded_skills=Django&excluded_skills=Flask
```

Эти навыки будут найдены и показаны, но не войдут в итоговый расчёт зарплаты.

### Полный пример

**Запрос:**
```
POST /api/v1/evaluation/evaluate?student_id=5&specialty=Python&top_k=5
```

**Ответ:**
```json
{
  "estimated_salary": 185000,
  "confidence": 0.89,
  "currency": "RUR",
  "skills": [
    {
      "skill": "Python",
      "similarity": 0.96,
      "avg_salary": 200000,
      "vacancy_count": 450,
      "from_discipline": "Программирование на Python",
      "grade": 5,
      "excluded": false
    },
    {
      "skill": "FastAPI",
      "similarity": 0.925,
      "avg_salary": 180000,
      "vacancy_count": 120,
      "from_discipline": "Программирование на Python",
      "grade": 5,
      "excluded": false
    },
    ...
  ]
}
```

---

## JWT-аутентификация и роли

### JWT Tokens

Система использует два типа токенов:
- **Access token** — короткая жизнь (15 минут), используется для доступа к API
- **Refresh token** — длинная жизнь (7 дней), используется для обновления access token

**Формат токена** (JWT payload):
```json
{
  "sub": "user_email@example.com",
  "user_id": 123,
  "role": "student",
  "exp": 1234567890  // Unix timestamp
}
```

### Password Security

- **Hashing**: bcrypt через `passlib`
- **Rounds**: 12 (по умолчанию)
- **Проверка**: `pwd_context.verify(plain_password, hashed_password)`

### Роли пользователей

| Роль | Описание | Доступные функции |
|------|----------|-------------------|
| **admin** | Администратор системы | CRUD студентов, парсинг вакансий, статистика |
| **student** | Студент | Редактирование профиля, просмотр запросов, чат |
| **employer** | Работодатель | Поиск студентов, отправка запросов, чат |

### Role-Based Access Control

**Защита эндпоинтов** через dependency injection:

```python
# app/auth.py
def require_role(*allowed_roles: str):
    async def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Access forbidden")
        return user
    return role_checker

# Использование в роутере
@router.get("/admin-only")
async def admin_route(user: User = Depends(require_role("admin"))):
    return {"message": "Only for admins"}
```

### Процесс аутентификации

#### 1. Регистрация

**Запрос:**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "student@example.com",
  "password": "securepass123",
  "role": "student"
}
```

**Процесс:**
1. Проверка уникальности email
2. Хеширование пароля через bcrypt
3. Создание пользователя в БД
4. Создание профиля (student или employer) в зависимости от роли
5. Генерация access + refresh токенов
6. Возврат токенов

**Ответ:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 123,
    "email": "student@example.com",
    "role": "student"
  }
}
```

#### 2. Вход

**Запрос:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "student@example.com",
  "password": "securepass123"
}
```

**Процесс:**
1. Поиск пользователя по email
2. Проверка пароля через `pwd_context.verify()`
3. Проверка `is_active`
4. Генерация access + refresh токенов
5. Возврат токенов

#### 3. Обновление токена

**Запрос:**
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

**Процесс:**
1. Декодирование refresh token
2. Проверка срока действия
3. Загрузка пользователя из БД
4. Генерация нового access token
5. Возврат нового access token

#### 4. Получение текущего пользователя

**Запрос:**
```http
GET /api/v1/auth/me
Authorization: Bearer eyJ...
```

**Ответ:**
```json
{
  "id": 123,
  "email": "student@example.com",
  "role": "student",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

### WebSocket Authentication

WebSocket не поддерживает HTTP-заголовки из браузера, поэтому токен передаётся в query parameter:

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/chat/42?token=${access_token}`);
```

**Проверка на сервере:**
```python
async def websocket_endpoint(
    websocket: WebSocket,
    request_id: int,
    token: str = Query(...),
):
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001)
        return
    # ...
```

---

## API-эндпоинты

### 1. Аутентификация (`/api/v1/auth/`)

#### POST `/api/v1/auth/register` — Регистрация

**Request:**
```json
{
  "email": "student@example.com",
  "password": "securepass123",
  "role": "student"  // "admin", "student", "employer"
}
```

**Response** (201):
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "student@example.com",
    "role": "student"
  }
}
```

#### POST `/api/v1/auth/login` — Вход

**Request:**
```json
{
  "email": "student@example.com",
  "password": "securepass123"
}
```

**Response** (200):
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": { ... }
}
```

**Errors:**
- `401 Unauthorized` — неверный email или пароль
- `403 Forbidden` — пользователь не активен

#### POST `/api/v1/auth/refresh` — Обновление токена

**Request:**
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response** (200):
```json
{
  "access_token": "new_access_token...",
  "token_type": "bearer"
}
```

#### GET `/api/v1/auth/me` — Текущий пользователь

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response** (200):
```json
{
  "id": 1,
  "email": "student@example.com",
  "role": "student",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

### 2. Студенты — Admin CRUD (`/api/v1/students/`)

**Доступ**: Только `admin`

#### GET `/api/v1/students/` — Список студентов

**Query params:**
- `skip` (int, default: 0) — пропустить N записей
- `limit` (int, default: 100) — вернуть N записей

**Response** (200):
```json
[
  {
    "id": 1,
    "user_id": 5,
    "full_name": "Иванов Иван Иванович",
    "group_name": "CS-101",
    "about_me": "Интересуюсь ML",
    "photo_path": "/uploads/5_1234567890.jpg",
    "disciplines": [
      {"id": 1, "name": "Программирование на Python", "grade": 5},
      {"id": 2, "name": "Базы данных", "grade": 4}
    ]
  },
  ...
]
```

#### POST `/api/v1/students/` — Создание студента

**Request:**
```json
{
  "full_name": "Петров Пётр",
  "group_name": "CS-102",
  "disciplines": [
    {"name": "Python", "grade": 5},
    {"name": "SQL", "grade": 4}
  ]
}
```

**Response** (201):
```json
{
  "id": 2,
  "full_name": "Петров Пётр",
  "group_name": "CS-102",
  "disciplines": [...]
}
```

#### GET `/api/v1/students/{id}` — Детали студента

**Response** (200):
```json
{
  "id": 1,
  "full_name": "Иванов Иван",
  "group_name": "CS-101",
  "about_me": "...",
  "photo_path": "...",
  "disciplines": [...]
}
```

#### PUT `/api/v1/students/{id}` — Редактирование студента

**Request:**
```json
{
  "full_name": "Иванов Иван Петрович",
  "group_name": "CS-101",
  "about_me": "Обновлённое описание"
}
```

**Response** (200): Обновлённый студент

#### DELETE `/api/v1/students/{id}` — Удаление студента

**Response** (204): No Content

#### POST `/api/v1/students/{id}/disciplines` — Добавление дисциплин

**Request:**
```json
{
  "disciplines": [
    {"name": "Docker", "grade": 5},
    {"name": "Kubernetes", "grade": 4}
  ]
}
```

**Response** (200): Обновлённый список дисциплин

---

### 3. Профиль студента — Self-service (`/api/v1/profile/student/`)

**Доступ**: Только `student`

#### GET `/api/v1/profile/student/me` — Мой профиль

**Response** (200):
```json
{
  "id": 1,
  "user_id": 5,
  "full_name": "Иванов Иван",
  "group_name": "CS-101",
  "about_me": "...",
  "photo_path": "/uploads/...",
  "disciplines": [...]
}
```

#### PUT `/api/v1/profile/student/me` — Редактировать профиль

**Request:**
```json
{
  "full_name": "Иванов Иван Петрович",
  "group_name": "CS-101",
  "about_me": "Обновлённое описание"
}
```

**Response** (200): Обновлённый профиль

#### POST `/api/v1/profile/student/me/photo` — Загрузить фото

**Request:**
```http
POST /api/v1/profile/student/me/photo
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <image file>
```

**Response** (200):
```json
{
  "photo_url": "/uploads/5_1234567890.jpg"
}
```

**Ограничения:**
- Максимальный размер: 5 MB
- Форматы: `.jpg`, `.jpeg`, `.png`, `.gif`

#### POST `/api/v1/profile/student/me/disciplines` — Добавить дисциплины

**Request:**
```json
{
  "disciplines": [
    {"name": "React", "grade": 5},
    {"name": "TypeScript", "grade": 4}
  ]
}
```

**Response** (200): Обновлённый список дисциплин

#### DELETE `/api/v1/profile/student/me/disciplines/{discipline_id}` — Удалить дисциплину

**Response** (204): No Content

#### GET `/api/v1/profile/student/me/contact-requests` — Мои запросы на контакт

**Response** (200):
```json
[
  {
    "id": 1,
    "employer": {
      "id": 10,
      "email": "hr@company.com",
      "employer_profile": {
        "company_name": "TechCorp",
        "position": "HR Manager"
      }
    },
    "status": "pending",
    "created_at": "2025-01-15T10:00:00Z",
    "responded_at": null
  },
  ...
]
```

#### POST `/api/v1/profile/student/me/contact-requests/{id}/accept` — Принять запрос

**Response** (200):
```json
{
  "id": 1,
  "status": "accepted",
  "responded_at": "2025-01-15T10:30:00Z"
}
```

#### POST `/api/v1/profile/student/me/contact-requests/{id}/reject` — Отклонить запрос

**Response** (200):
```json
{
  "id": 1,
  "status": "rejected",
  "responded_at": "2025-01-15T10:30:00Z"
}
```

---

### 4. Профиль работодателя (`/api/v1/profile/employer/`)

**Доступ**: Только `employer`

#### GET `/api/v1/profile/employer/me` — Мой профиль

**Response** (200):
```json
{
  "id": 1,
  "user_id": 10,
  "company_name": "TechCorp",
  "position": "HR Manager",
  "created_at": "2025-01-10T12:00:00Z"
}
```

#### PUT `/api/v1/profile/employer/me` — Редактировать профиль

**Request:**
```json
{
  "company_name": "TechCorp Inc.",
  "position": "Senior HR Manager"
}
```

**Response** (200): Обновлённый профиль

---

### 5. Работодатель — Поиск и контакты (`/api/v1/employer/`)

**Доступ**: Только `employer`

#### GET `/api/v1/employer/students` — Поиск студентов (анонимно)

**Query params:**
- `search` (str, optional) — поиск по дисциплинам или ФИО
- `limit` (int, default: 20) — количество результатов

**Response** (200):
```json
[
  {
    "id": 1,
    "anonymized_name": "Студент #1",
    "group_name": "CS-101",
    "matched_disciplines": ["Python", "SQL"]
  },
  {
    "id": 2,
    "anonymized_name": "Студент #2",
    "group_name": "CS-102",
    "matched_disciplines": ["React", "TypeScript"]
  },
  ...
]
```

#### GET `/api/v1/employer/students/{id}` — Полный профиль студента

**Response** (200):
```json
{
  "id": 1,
  "full_name": "Иванов Иван Иванович",
  "group_name": "CS-101",
  "about_me": "Интересуюсь ML",
  "photo_path": "/uploads/5_1234567890.jpg",
  "disciplines": [
    {"id": 1, "name": "Python", "grade": 5},
    {"id": 2, "name": "SQL", "grade": 4}
  ]
}
```

#### POST `/api/v1/employer/contact-requests` — Отправить запрос на контакт

**Request:**
```json
{
  "student_id": 1,
  "message": "Добрый день! Хотим предложить стажировку в нашей компании."
}
```

**Response** (201):
```json
{
  "id": 1,
  "employer_id": 10,
  "student_id": 1,
  "status": "pending",
  "created_at": "2025-01-15T10:00:00Z"
}
```

#### GET `/api/v1/employer/contact-requests` — Мои запросы

**Response** (200):
```json
[
  {
    "id": 1,
    "student": {
      "id": 1,
      "full_name": "Иванов Иван",
      "group_name": "CS-101"
    },
    "status": "accepted",
    "created_at": "2025-01-15T10:00:00Z",
    "responded_at": "2025-01-15T10:30:00Z"
  },
  ...
]
```

---

### 6. Вакансии (`/api/v1/vacancies/`)

#### POST `/api/v1/vacancies/parse` — Парсинг вакансий с hh.ru

**Доступ**: Только `admin`

**Request:**
```json
{
  "query": "Python разработчик",
  "count": 50
}
```

**Response** (200):
```json
{
  "total_parsed": 50,
  "tags": [
    {"name": "Python", "count": 45},
    {"name": "Django", "count": 30},
    {"name": "SQL", "count": 28}
  ],
  "average_salary": 185000
}
```

**Процесс:**
1. Запрос к hh.ru API (`GET /vacancies?text={query}&per_page={count}`)
2. Извлечение данных: hh_id, title, url, salary, experience, key_skills
3. Сохранение в PostgreSQL (vacancies, tags через M2M)
4. Генерация эмбеддингов для новых тегов (Ollama)
5. Загрузка эмбеддингов в Qdrant

#### GET `/api/v1/vacancies/` — Список вакансий

**Доступ**: Все аутентифицированные

**Query params:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `search_query` (str, optional) — фильтр по search_query

**Response** (200):
```json
[
  {
    "id": 1,
    "hh_id": "123456",
    "title": "Python разработчик",
    "url": "https://hh.ru/vacancy/123456",
    "salary_from": 150000,
    "salary_to": 200000,
    "salary_currency": "RUR",
    "experience": "between1And3",
    "search_query": "Python",
    "tags": [
      {"id": 1, "name": "Python"},
      {"id": 2, "name": "Django"}
    ],
    "created_at": "2025-01-15T10:00:00Z"
  },
  ...
]
```

#### GET `/api/v1/vacancies/tags` — Статистика тегов

**Доступ**: Все аутентифицированные

**Query params:**
- `limit` (int, default: 50) — топ N тегов

**Response** (200):
```json
[
  {"name": "Python", "vacancy_count": 450},
  {"name": "SQL", "vacancy_count": 380},
  {"name": "Django", "vacancy_count": 250},
  ...
]
```

---

### 7. Оценка рыночной стоимости (`/api/v1/evaluation/`)

**Доступ**: Все аутентифицированные

#### POST `/api/v1/evaluation/evaluate` — Оценка стоимости студента

**Query params:**
- `student_id` (int, required) — ID студента
- `specialty` (str, required) — специальность для фильтрации вакансий
- `top_k` (int, default: 5, range: 1–20) — количество навыков на дисциплину
- `experience` (str, optional) — фильтр опыта: `noExperience`, `between1And3`, `between3And6`, `moreThan6`
- `excluded_skills` (list[str], optional) — навыки для исключения

**Пример:**
```http
POST /api/v1/evaluation/evaluate?student_id=1&specialty=Python%20разработчик&top_k=5&experience=noExperience&excluded_skills=Django&excluded_skills=Flask
```

**Response** (200):
```json
{
  "estimated_salary": 185000,
  "confidence": 0.89,
  "currency": "RUR",
  "skills": [
    {
      "skill": "Python",
      "similarity": 0.96,
      "avg_salary": 200000,
      "vacancy_count": 450,
      "from_discipline": "Программирование на Python",
      "grade": 5,
      "excluded": false
    },
    {
      "skill": "Django",
      "similarity": 0.87,
      "avg_salary": 190000,
      "vacancy_count": 250,
      "from_discipline": "Веб-разработка",
      "grade": 4,
      "excluded": true  // Исключён из расчёта
    },
    ...
  ]
}
```

**Errors:**
- `404 Not Found` — студент не найден
- `400 Bad Request` — некорректные параметры

#### GET `/api/v1/evaluation/skills` — Навыки студента в терминах hh.ru

**Query params:**
- `student_id` (int, required)
- `top_k` (int, default: 3, range: 1–10)

**Response** (200):
```json
{
  "student_id": 1,
  "disciplines_skills": [
    {
      "discipline": "Программирование на Python",
      "grade": 5,
      "skills": [
        {"skill": "Python", "similarity": 0.96},
        {"skill": "FastAPI", "similarity": 0.92},
        {"skill": "Django", "similarity": 0.87}
      ]
    },
    ...
  ]
}
```

---

### 8. Чат (`/api/v1/chat/` и `/ws/chat/{request_id}`)

**Доступ**: Student или Employer (участники запроса)

#### GET `/api/v1/chat/{request_id}/messages` — История сообщений

**Query params:**
- `skip` (int, default: 0)
- `limit` (int, default: 50)

**Response** (200):
```json
[
  {
    "id": 1,
    "contact_request_id": 42,
    "sender_id": 10,
    "text": "Здравствуйте! Хотим предложить стажировку.",
    "is_read": true,
    "created_at": "2025-01-15T10:00:00Z"
  },
  {
    "id": 2,
    "sender_id": 5,
    "text": "Добрый день! Интересно, расскажите подробнее.",
    "is_read": false,
    "created_at": "2025-01-15T10:05:00Z"
  },
  ...
]
```

#### POST `/api/v1/chat/{request_id}/mark-read` — Отметить сообщения как прочитанные

**Response** (200):
```json
{
  "marked_count": 5
}
```

#### WebSocket `/ws/chat/{request_id}?token=<jwt>` — Real-time чат

**Подключение:**
```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/ws/chat/42?token=${token}`);

ws.onopen = () => {
  console.log('Connected to chat');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('New message:', message);
  // { id: 3, sender_id: 10, text: "...", created_at: "..." }
};

// Отправка сообщения
ws.send(JSON.stringify({ text: "Привет!" }));
```

**Серверная логика:**
1. Проверка JWT токена
2. Проверка, что пользователь — участник чата (студент или работодатель)
3. Добавление соединения в `active_connections[request_id]`
4. При получении сообщения:
   - Сохранение в БД (таблица `messages`)
   - Broadcast всем активным соединениям в чате

---

## WebSocket чат

### Архитектура

WebSocket-чат реализован в `app/routers/chat.py` через FastAPI WebSocket endpoint:

```python
active_connections: dict[int, list[WebSocket]] = {}

@router.websocket("/ws/chat/{request_id}")
async def websocket_chat(
    websocket: WebSocket,
    request_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    # 1. Аутентификация через JWT
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=4001)
        return
    
    # 2. Проверка доступа к чату
    contact_request = await db.get(ContactRequest, request_id)
    if not is_participant(user, contact_request):
        await websocket.close(code=4003)
        return
    
    # 3. Подключение
    await websocket.accept()
    if request_id not in active_connections:
        active_connections[request_id] = []
    active_connections[request_id].append(websocket)
    
    try:
        while True:
            # 4. Получение сообщения от клиента
            data = await websocket.receive_json()
            text = data.get("text")
            
            # 5. Сохранение в БД
            message = Message(
                contact_request_id=request_id,
                sender_id=user.id,
                text=text,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(message)
            await db.commit()
            await db.refresh(message)
            
            # 6. Broadcast всем участникам чата
            for connection in active_connections[request_id]:
                await connection.send_json({
                    "id": message.id,
                    "sender_id": message.sender_id,
                    "text": message.text,
                    "created_at": message.created_at.isoformat()
                })
    
    except WebSocketDisconnect:
        # 7. Отключение
        active_connections[request_id].remove(websocket)
        if not active_connections[request_id]:
            del active_connections[request_id]
```

### Клиентская реализация (React)

**Custom hook** `frontend/src/hooks/useWebSocket.ts`:

```typescript
import { useEffect, useRef, useState } from 'react';

interface Message {
  id: number;
  sender_id: number;
  text: string;
  created_at: string;
}

export const useWebSocket = (requestId: number, token: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `ws://localhost:8000/ws/chat/${requestId}?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      const message: Message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    return () => {
      ws.current?.close();
    };
  }, [requestId, token]);

  const sendMessage = (text: string) => {
    if (ws.current && isConnected) {
      ws.current.send(JSON.stringify({ text }));
    }
  };

  return { messages, isConnected, sendMessage };
};
```

**Использование в компоненте**:

```typescript
import { useWebSocket } from '../hooks/useWebSocket';

const ChatWindow = ({ requestId }: { requestId: number }) => {
  const token = localStorage.getItem('access_token') || '';
  const { messages, isConnected, sendMessage } = useWebSocket(requestId, token);
  const [inputText, setInputText] = useState('');

  const handleSend = () => {
    if (inputText.trim()) {
      sendMessage(inputText);
      setInputText('');
    }
  };

  return (
    <div>
      <div className="status">
        {isConnected ? '🟢 Подключено' : '🔴 Отключено'}
      </div>
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id} className="message">
            <strong>User {msg.sender_id}:</strong> {msg.text}
          </div>
        ))}
      </div>
      <input
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
      />
      <button onClick={handleSend}>Отправить</button>
    </div>
  );
};
```

### Ограничения текущей реализации

1. **In-memory connections** — при рестарте сервера все WebSocket соединения разрываются
2. **Single instance** — не работает с несколькими инстансами FastAPI (нужен Redis Pub/Sub)
3. **Отсутствие reconnect logic** — клиенту нужно вручную переподключаться

### Пути улучшения

1. **Redis Pub/Sub** для broadcast между инстансами:
   ```python
   # При получении сообщения
   await redis_client.publish(f"chat:{request_id}", json.dumps(message_data))
   
   # В фоновом таске
   async def redis_listener(request_id):
       pubsub = redis_client.pubsub()
       await pubsub.subscribe(f"chat:{request_id}")
       async for message in pubsub.listen():
           # Broadcast локальным WebSocket соединениям
           for ws in active_connections[request_id]:
               await ws.send_json(message["data"])
   ```

2. **Reconnect logic на клиенте**:
   ```typescript
   useEffect(() => {
     const connect = () => {
       ws.current = new WebSocket(wsUrl);
       ws.current.onclose = () => {
         setTimeout(connect, 3000);  // Переподключение через 3 сек
       };
     };
     connect();
   }, []);
   ```

3. **Heartbeat ping/pong** для проверки активности соединения

---

## Фронтенд (React SPA)

### Технологии

- **React 18** — UI-библиотека с hooks
- **TypeScript** — статическая типизация
- **Vite** — сверхбыстрый сборщик (HMR, tree-shaking)
- **React Router v6** — клиентский роутинг
- **Zustand** — легковесный state management (альтернатива Redux)
- **Axios** — HTTP-клиент для API

### Структура проекта

```
frontend/
├── src/
│   ├── pages/              # Страницы (роуты)
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── StudentPanel.tsx
│   │   └── EmployerPanel.tsx
│   │
│   ├── components/         # Переиспользуемые компоненты
│   │   ├── Header.tsx
│   │   ├── ChatWindow.tsx
│   │   ├── StudentCard.tsx
│   │   └── ...
│   │
│   ├── store/              # Zustand stores
│   │   ├── authStore.ts    # Управление аутентификацией
│   │   └── chatStore.ts    # Управление чатами
│   │
│   ├── hooks/              # Custom React hooks
│   │   ├── useAuth.ts
│   │   └── useWebSocket.ts
│   │
│   ├── api/                # API-клиенты (axios)
│   │   ├── auth.ts
│   │   ├── students.ts
│   │   ├── employer.ts
│   │   └── chat.ts
│   │
│   ├── styles/             # CSS/SCSS файлы
│   │   └── main.css
│   │
│   ├── App.tsx             # Главный компонент с роутингом
│   └── main.tsx            # Entry point
│
├── public/                 # Публичные файлы
│   └── favicon.ico
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### Роутинг

**Файл**: `frontend/src/App.tsx`

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import Login from './pages/Login';
import Register from './pages/Register';
import StudentPanel from './pages/StudentPanel';
import EmployerPanel from './pages/EmployerPanel';

const App = () => {
  const { user, isAuthenticated } = useAuthStore();

  return (
    <BrowserRouter>
      <Routes>
        {/* Публичные роуты */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Защищённые роуты */}
        {/* Admin перенаправляется на standalone HTML панель /admin */}
        <Route
          path="/student"
          element={
            isAuthenticated && user?.role === 'student' ? (
              <StudentPanel />
            ) : (
              <Navigate to="/login" />
            )
          }
        />
        <Route
          path="/employer"
          element={
            isAuthenticated && user?.role === 'employer' ? (
              <EmployerPanel />
            ) : (
              <Navigate to="/login" />
            )
          }
        />

        {/* Редирект с главной */}
        <Route path="/" element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
```

### State Management (Zustand)

**Файл**: `frontend/src/store/authStore.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  role: 'admin' | 'student' | 'employer';
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  
  login: (user: User, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  updateToken: (accessToken: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),

      logout: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false }),

      updateToken: (accessToken) =>
        set({ accessToken }),
    }),
    {
      name: 'auth-storage',  // localStorage key
    }
  )
);
```

### API клиенты

**Файл**: `frontend/src/api/auth.ts`

```typescript
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

export const authApi = {
  register: async (email: string, password: string, role: string) => {
    const response = await axios.post(`${API_URL}/auth/register`, {
      email,
      password,
      role,
    });
    return response.data;
  },

  login: async (email: string, password: string) => {
    const response = await axios.post(`${API_URL}/auth/login`, {
      email,
      password,
    });
    return response.data;
  },

  refresh: async (refreshToken: string) => {
    const response = await axios.post(`${API_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  me: async (accessToken: string) => {
    const response = await axios.get(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    return response.data;
  },
};
```

### Сборка и деплой

**Development**:
```bash
cd frontend
npm run dev
# Запускается на http://localhost:5173
```

**Production build**:
```bash
cd frontend
npm run build
# Результат в frontend/dist/
```

**Backend serving** (app/main.py):
```python
# Раздача статики фронтенда
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

# Fallback для SPA (все неизвестные роуты → index.html)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("frontend/dist/index.html")
```

---

## Админ-панель (standalone HTML)

### Описание

Админ-панель — это standalone HTML-страница с JavaScript для доступа администраторов к основным функциям системы. Панель работает независимо от React SPA и имеет собственную JWT-аутентификацию.

**Путь**: `app/static/admin.html`  
**URL**: http://localhost:8000/admin

### Возможности

Админ-панель имеет 4 основные вкладки:

1. **Оценка студента** — расчёт рыночной стоимости студента по его дисциплинам
2. **Студенты** — CRUD операции: просмотр списка, добавление, редактирование, удаление
3. **Парсинг вакансий** — форма для парсинга вакансий с hh.ru
4. **Навыки и теги** — статистика по навыкам с визуализацией (Chart.js)

### Аутентификация

- JWT-аутентификация с email и паролем
- Токен сохраняется в localStorage
- После входа все 4 вкладки становятся доступны (исправлена ошибка отображения)

### Технологии

- **Vanilla JavaScript** — без фреймворков
- **Chart.js** — визуализация данных
- **CSS Grid/Flexbox** — адаптивная вёрстка
- **localStorage** — хранение JWT токена

### Структура страницы

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Admin Panel</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    /* Тёмная тема */
    body {
      background: #1a1a2e;
      color: #eee;
      font-family: 'Segoe UI', sans-serif;
    }
    /* ... */
  </style>
</head>
<body>
  <!-- Форма входа -->
  <div id="login-form">
    <h2>Вход в админ-панель</h2>
    <input type="email" id="email" placeholder="Email">
    <input type="password" id="password" placeholder="Пароль">
    <button onclick="login()">Войти</button>
  </div>

  <!-- Главная панель (скрыта до входа) -->
  <div id="main-panel" style="display:none;">
    <header>
      <h1>Админ-панель HH.ru Student Evaluator</h1>
      <button onclick="logout()">Выйти</button>
    </header>

    <nav>
      <button onclick="showSection('students')">Студенты</button>
      <button onclick="showSection('parsing')">Парсинг</button>
      <button onclick="showSection('tags')">Теги</button>
      <button onclick="showSection('evaluation')">Оценка</button>
    </nav>

    <main id="content">
      <!-- Динамический контент -->
    </main>
  </div>

  <script>
    const API_URL = '/api/v1';
    let accessToken = localStorage.getItem('admin_token');

    // Проверка токена при загрузке
    if (accessToken) {
      checkAuth();
    }

    async function login() {
      const email = document.getElementById('email').value;
      const password = document.getElementById('password').value;

      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (response.ok) {
        const data = await response.json();
        accessToken = data.access_token;
        localStorage.setItem('admin_token', accessToken);
        showMainPanel();
      } else {
        alert('Ошибка входа');
      }
    }

    async function checkAuth() {
      const response = await fetch(`${API_URL}/auth/me`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });

      if (response.ok) {
        const user = await response.json();
        if (user.role === 'admin') {
          showMainPanel();
        } else {
          logout();
        }
      } else {
        logout();
      }
    }

    function logout() {
      localStorage.removeItem('admin_token');
      accessToken = null;
      document.getElementById('login-form').style.display = 'block';
      document.getElementById('main-panel').style.display = 'none';
    }

    function showMainPanel() {
      document.getElementById('login-form').style.display = 'none';
      document.getElementById('main-panel').style.display = 'block';
      showSection('students');
    }

    async function showSection(section) {
      const content = document.getElementById('content');
      
      if (section === 'students') {
        const response = await fetch(`${API_URL}/students/`, {
          headers: { 'Authorization': `Bearer ${accessToken}` }
        });
        const students = await response.json();
        
        content.innerHTML = '<h2>Студенты</h2>';
        students.forEach(s => {
          content.innerHTML += `<div>${s.full_name} — ${s.group_name}</div>`;
        });
      }
      
      // Аналогично для других секций...
    }

    // Парсинг вакансий
    async function parseVacancies() {
      const query = document.getElementById('parse-query').value;
      const count = document.getElementById('parse-count').value;

      const response = await fetch(`${API_URL}/vacancies/parse`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ query, count: parseInt(count) })
      });

      const result = await response.json();
      alert(`Спарсено: ${result.total_parsed}`);
    }

    // Статистика тегов с Chart.js
    async function showTags() {
      const response = await fetch(`${API_URL}/vacancies/tags?limit=20`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      const tags = await response.json();

      const labels = tags.map(t => t.name);
      const data = tags.map(t => t.vacancy_count);

      const ctx = document.getElementById('tagsChart').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Количество вакансий',
            data: data,
            backgroundColor: 'rgba(75, 192, 192, 0.6)'
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: { beginAtZero: true }
          }
        }
      });
    }
  </script>
</body>
</html>
```

### Доступ

1. Открыть http://localhost:8000/admin
2. Ввести email и пароль администратора
3. После входа доступны все 4 вкладки

### Роутинг админов

Пользователи с ролью `admin` **не имеют React-роута** в `App.tsx`. При входе они автоматически перенаправляются на `/admin`, где работает standalone HTML-панель с собственной JWT-аутентификацией.

### Преимущества

✅ Быстрая загрузка (нет React-бандла)  
✅ Независимость от фронтенд-билда  
✅ Простота модификации (один HTML-файл)  
✅ Все функции администратора в одном месте  
✅ Подходит для быстрых административных задач

### Технические детали

При загрузке панели функция `showApp()` корректно очищает inline стили `display` для всех вкладок, что устраняет проблему с отображением только одной вкладки после входа.

---

## Парсинг вакансий с hh.ru

### API hh.ru

**Документация**: https://github.com/hhru/api

**Endpoint**: `GET https://api.hh.ru/vacancies`

**Параметры:**
- `text` — поисковый запрос
- `per_page` — количество результатов (max: 100)
- `page` — номер страницы (для пагинации)
- `area` — регион (113 = Россия)

**Пример запроса:**
```
GET https://api.hh.ru/vacancies?text=Python%20разработчик&per_page=50&page=0&area=113
```

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "123456",
      "name": "Python разработчик",
      "alternate_url": "https://hh.ru/vacancy/123456",
      "salary": {
        "from": 150000,
        "to": 200000,
        "currency": "RUR"
      },
      "experience": {
        "id": "between1And3"
      },
      "key_skills": [
        {"name": "Python"},
        {"name": "Django"},
        {"name": "PostgreSQL"}
      ]
    },
    ...
  ]
}
```

### Реализация парсера

**Файл**: `app/parser.py`

```python
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Vacancy, Tag, vacancy_tag_association
from app.embeddings import get_embedding
from app.vector_store import upsert_tag_embedding

async def parse_vacancies(
    query: str,
    count: int,
    db: AsyncSession
) -> dict:
    """
    Парсит вакансии с hh.ru и сохраняет в БД.
    
    Args:
        query: Поисковый запрос
        count: Количество вакансий (до 100 за раз)
        db: AsyncSession для БД
    
    Returns:
        {"total_parsed": int, "tags": list, "average_salary": float}
    """
    
    # 1. Запрос к hh.ru API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.hh.ru/vacancies",
            params={
                "text": query,
                "per_page": min(count, 100),
                "page": 0,
                "area": 113  # Россия
            },
            timeout=30.0
        )
        data = response.json()
    
    vacancies_data = data.get("items", [])
    total_parsed = 0
    all_tags = {}
    salaries = []
    
    for item in vacancies_data:
        # 2. Извлечение данных
        hh_id = item["id"]
        title = item["name"]
        url = item["alternate_url"]
        
        salary_data = item.get("salary") or {}
        salary_from = salary_data.get("from")
        salary_to = salary_data.get("to")
        salary_currency = salary_data.get("currency")
        
        experience = item.get("experience", {}).get("id")
        
        key_skills = [skill["name"] for skill in item.get("key_skills", [])]
        
        # 3. Проверка, существует ли вакансия
        existing = await db.execute(
            select(Vacancy).where(Vacancy.hh_id == hh_id)
        )
        if existing.scalar_one_or_none():
            continue  # Пропускаем дубликаты
        
        # 4. Создание вакансии
        vacancy = Vacancy(
            hh_id=hh_id,
            title=title,
            url=url,
            salary_from=salary_from,
            salary_to=salary_to,
            salary_currency=salary_currency,
            experience=experience,
            search_query=query
        )
        db.add(vacancy)
        await db.flush()  # Получаем vacancy.id
        
        # 5. Обработка тегов
        for skill_name in key_skills:
            # Ищем или создаём тег
            tag_result = await db.execute(
                select(Tag).where(Tag.name == skill_name)
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=skill_name)
                db.add(tag)
                await db.flush()
                
                # Генерация эмбеддинга для нового тега
                embedding = await get_embedding(skill_name)
                await upsert_tag_embedding(tag.id, skill_name, embedding)
            
            # Связь M2M
            await db.execute(
                vacancy_tag_association.insert().values(
                    vacancy_id=vacancy.id,
                    tag_id=tag.id
                )
            )
            
            # Статистика
            all_tags[skill_name] = all_tags.get(skill_name, 0) + 1
        
        # 6. Статистика зарплат
        if salary_from and salary_to:
            avg_salary = (salary_from + salary_to) / 2
            # Конвертация в RUR (если нужно)
            if salary_currency == "USD":
                avg_salary *= 90  # Примерный курс
            elif salary_currency == "EUR":
                avg_salary *= 100
            salaries.append(avg_salary)
        
        total_parsed += 1
    
    await db.commit()
    
    # 7. Результат
    tags_list = [{"name": k, "count": v} for k, v in all_tags.items()]
    tags_list.sort(key=lambda x: x["count"], reverse=True)
    
    average_salary = sum(salaries) / len(salaries) if salaries else 0
    
    return {
        "total_parsed": total_parsed,
        "tags": tags_list[:20],  # Топ-20
        "average_salary": int(average_salary)
    }
```

### Использование

**REST API:**
```http
POST /api/v1/vacancies/parse
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "query": "Python разработчик",
  "count": 50
}
```

**Response:**
```json
{
  "total_parsed": 50,
  "tags": [
    {"name": "Python", "count": 45},
    {"name": "Django", "count": 30},
    {"name": "SQL", "count": 28}
  ],
  "average_salary": 185000
}
```

### Ограничения hh.ru API

1. **Rate limiting**: Рекомендуется не более 10 запросов/сек
2. **Пагинация**: Максимум 100 результатов за запрос, нужна пагинация для больших наборов
3. **Без key_skills в списке**: Полная информация о навыках требует дополнительного запроса к `/vacancies/{id}`

### Пути улучшения

1. **Background tasks** (Celery): Парсинг в фоновом режиме для больших объёмов
2. **Детальные запросы**: Получать полную информацию о вакансии через `/vacancies/{id}`
3. **Периодический парсинг** (cron): Автоматическое обновление базы вакансий

---

## Профили пользователей

### Профиль студента

**Поля:**
- `full_name` — ФИО
- `group_name` — номер группы
- `about_me` — текстовое описание (textarea)
- `photo_path` — путь к фото (загрузка через multipart/form-data)
- `disciplines` — список дисциплин с оценками (3/4/5)

**Self-service эндпоинты:**
- `GET /api/v1/profile/student/me` — просмотр
- `PUT /api/v1/profile/student/me` — редактирование
- `POST /api/v1/profile/student/me/photo` — загрузка фото
- `POST /api/v1/profile/student/me/disciplines` — добавление дисциплин
- `DELETE /api/v1/profile/student/me/disciplines/{id}` — удаление дисциплины

**Пример использования:**

```typescript
// Редактирование профиля
const updateProfile = async () => {
  await axios.put(
    '/api/v1/profile/student/me',
    {
      full_name: 'Иванов Иван Петрович',
      group_name: 'CS-101',
      about_me: 'Увлекаюсь ML и Data Science'
    },
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
};

// Загрузка фото
const uploadPhoto = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(
    '/api/v1/profile/student/me/photo',
    formData,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    }
  );

  return response.data.photo_url;
};

// Добавление дисциплин
const addDisciplines = async () => {
  await axios.post(
    '/api/v1/profile/student/me/disciplines',
    {
      disciplines: [
        { name: 'React', grade: 5 },
        { name: 'TypeScript', grade: 4 }
      ]
    },
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
};
```

### Профиль работодателя

**Поля:**
- `company_name` — название компании
- `position` — должность

**Self-service эндпоинты:**
- `GET /api/v1/profile/employer/me` — просмотр
- `PUT /api/v1/profile/employer/me` — редактирование

**Пример использования:**

```typescript
const updateEmployerProfile = async () => {
  await axios.put(
    '/api/v1/profile/employer/me',
    {
      company_name: 'TechCorp Inc.',
      position: 'Senior HR Manager'
    },
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  );
};
```

---

## Система контактов

### Жизненный цикл запроса

1. **Создание** — работодатель отправляет запрос студенту
2. **Pending** — студент видит запрос в своём списке
3. **Accepted/Rejected** — студент принимает или отклоняет
4. **Chat opens** — при принятии открывается WebSocket-чат

### Схема потока

```
Employer                          Student
   │                                  │
   ├─ POST /employer/contact-requests │
   │  (student_id, message)           │
   │                                  │
   │      ┌──────────────────┐        │
   │      │ ContactRequest   │        │
   │      │ status: pending  │        │
   │      └──────────────────┘        │
   │                                  │
   │                   ┌──────────────┤
   │                   │ GET /profile/student/me/contact-requests
   │                   │              │
   │                   │  [{ id: 1, status: 'pending', ... }]
   │                   │              │
   │                   │    ┌─────────┤
   │                   │    │ POST /profile/student/me/contact-requests/1/accept
   │                   │    │         │
   │      ┌──────────────────┐        │
   │      │ ContactRequest   │        │
   │      │ status: accepted │        │
   │      └──────────────────┘        │
   │                                  │
   ├─ WebSocket /ws/chat/1            │
   │                                  ├─ WebSocket /ws/chat/1
   │                                  │
   ├────────────────────────────────> │
   │  { text: "Здравствуйте!" }      │
   │                                  │
   │ <────────────────────────────────┤
   │  { text: "Добрый день!" }        │
```

### API эндпоинты

**Работодатель:**
```typescript
// Отправка запроса
await axios.post(
  '/api/v1/employer/contact-requests',
  { student_id: 5, message: 'Предлагаем стажировку' },
  { headers: { Authorization: `Bearer ${token}` } }
);

// Просмотр своих запросов
const { data } = await axios.get('/api/v1/employer/contact-requests', {
  headers: { Authorization: `Bearer ${token}` }
});
// data = [{ id: 1, student: {...}, status: 'accepted', ... }]
```

**Студент:**
```typescript
// Просмотр входящих запросов
const { data } = await axios.get('/api/v1/profile/student/me/contact-requests', {
  headers: { Authorization: `Bearer ${token}` }
});
// data = [{ id: 1, employer: {...}, status: 'pending', ... }]

// Принятие запроса
await axios.post(
  '/api/v1/profile/student/me/contact-requests/1/accept',
  {},
  { headers: { Authorization: `Bearer ${token}` } }
);

// Отклонение запроса
await axios.post(
  '/api/v1/profile/student/me/contact-requests/1/reject',
  {},
  { headers: { Authorization: `Bearer ${token}` } }
);
```

---

## Инфраструктура (Docker)

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/hh_parser
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_URL=http://ollama:11434
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
    depends_on:
      - db
      - qdrant
      - ollama
    volumes:
      - ./app/static/uploads:/app/static/uploads  # Персистентность фото

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: hh_parser
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  qdrant:
    image: qdrant/qdrant:v1.13.2
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    command: serve

volumes:
  postgres_data:
  qdrant_data:
  ollama_data:
```

### Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app

# Установка uv
RUN pip install uv

# Копирование зависимостей
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Копирование кода
COPY app/ ./app/

# Копирование frontend dist
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Создание директории для загрузок
RUN mkdir -p /app/static/uploads

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Экспозиция порта
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Запуск

```powershell
# Сборка и запуск всех сервисов
docker-compose up --build -d

# Просмотр логов
docker-compose logs -f app

# Остановка
docker-compose down

# Полная очистка (с удалением volumes)
docker-compose down -v
```

### Инициализация Ollama

После первого запуска нужно скачать модель эмбеддингов:

```powershell
# Войти в контейнер ollama
docker exec -it test_antigravity_ollama_1 bash

# Скачать модель
ollama pull nomic-embed-text

# Выйти
exit
```

---

## Тестирование

### Структура тестов

**64 теста**, организованных по модулям:

```
tests/
├── conftest.py              # Fixtures (async_client, test users, auth headers)
├── test_auth.py             # Аутентификация (register, login, refresh, me)
├── test_students.py         # Admin CRUD студентов
├── test_student_profile.py  # Self-service профиля студента
├── test_employer.py         # Функции работодателя (search, contact requests)
└── test_chat.py             # WebSocket чат
```

### Конфигурация pytest

**Файл**: `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Fixtures (conftest.py)

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.main import app
from app.database import Base, get_db
from app.models import User, Student, EmployerProfile
from app.auth import get_password_hash, create_access_token

# Тестовая БД в памяти (SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def async_client():
    """Async HTTP client для тестирования FastAPI."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async def override_get_db():
        async with AsyncSession(engine) as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
async def test_user_admin(async_client):
    """Тестовый пользователь с ролью admin."""
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("adminpass"),
        role="admin",
        is_active=True
    )
    # Сохранение в БД...
    return user

@pytest.fixture
async def test_user_student(async_client):
    """Тестовый пользователь с ролью student + профиль."""
    user = User(
        email="student@test.com",
        password_hash=get_password_hash("studentpass"),
        role="student",
        is_active=True
    )
    # Сохранение в БД...
    
    student = Student(
        user_id=user.id,
        full_name="Тестовый Студент",
        group_name="CS-101"
    )
    # Сохранение в БД...
    
    return user, student

@pytest.fixture
def auth_headers_admin(test_user_admin):
    """JWT-заголовки для admin."""
    token = create_access_token(data={"sub": test_user_admin.email})
    return {"Authorization": f"Bearer {token}"}
```

### Примеры тестов

**test_auth.py**:
```python
import pytest

@pytest.mark.asyncio
async def test_register(async_client):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "securepass123",
            "role": "student"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@test.com"

@pytest.mark.asyncio
async def test_login(async_client, test_user_student):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "student@test.com",
            "password": "studentpass"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_login_wrong_password(async_client, test_user_student):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": "student@test.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
```

**test_students.py**:
```python
@pytest.mark.asyncio
async def test_create_student_as_admin(async_client, auth_headers_admin):
    response = await async_client.post(
        "/api/v1/students/",
        json={
            "full_name": "Новый Студент",
            "group_name": "CS-102",
            "disciplines": [
                {"name": "Python", "grade": 5}
            ]
        },
        headers=auth_headers_admin
    )
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Новый Студент"
    assert len(data["disciplines"]) == 1

@pytest.mark.asyncio
async def test_create_student_as_student_forbidden(async_client, auth_headers_student):
    response = await async_client.post(
        "/api/v1/students/",
        json={"full_name": "Test", "group_name": "CS-101"},
        headers=auth_headers_student
    )
    assert response.status_code == 403
```

**test_chat.py**:
```python
from fastapi.websockets import WebSocketDisconnect

@pytest.mark.asyncio
async def test_websocket_chat(async_client, test_contact_request, auth_token_student):
    async with async_client.websocket_connect(
        f"/ws/chat/{test_contact_request.id}?token={auth_token_student}"
    ) as websocket:
        # Отправка сообщения
        await websocket.send_json({"text": "Hello from test!"})
        
        # Получение ответа
        data = await websocket.receive_json()
        assert data["text"] == "Hello from test!"
        assert "id" in data
        assert "created_at" in data
```

### Запуск тестов

```powershell
# Все тесты
uv run pytest tests\ -v

# Конкретный файл
uv run pytest tests\test_auth.py -v

# С coverage
uv run pytest tests\ --cov=app --cov-report=html

# Только помеченные тесты (если используются markers)
uv run pytest tests\ -m "auth" -v
```

---

## Развёртывание

### Production checklist

1. **Переменные окружения**:
   ```env
   SECRET_KEY=<strong-random-key>
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
   QDRANT_URL=http://qdrant:6333
   OLLAMA_URL=http://ollama:11434
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

2. **HTTPS** — настроить Nginx с Let's Encrypt:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;
       
       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /ws/ {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

3. **Database migrations** — использовать Alembic:
   ```bash
   alembic upgrade head
   ```

4. **Monitoring** — Prometheus + Grafana для метрик

5. **Logging** — централизованное логирование (ELK Stack)

6. **Backup** — регулярное резервное копирование PostgreSQL и Qdrant

7. **Rate limiting** — защита от DDoS (Nginx limit_req)

8. **Security headers** — CSP, X-Frame-Options, etc.

### Рекомендуемая инфраструктура

```
Internet
   │
   ├─ Cloudflare CDN (DDoS protection, SSL)
   │
   ├─ Nginx (reverse proxy, load balancer)
   │
   ├─ FastAPI (3 instances за load balancer)
   │
   ├─ PostgreSQL (master-slave replication)
   │
   ├─ Qdrant (standalone или кластер)
   │
   ├─ Ollama (GPU-сервер для эмбеддингов)
   │
   └─ Redis (кэш + WebSocket Pub/Sub)
```

---

## Заключение

**HH.ru Student Evaluator** — это полнофункциональная платформа с современной архитектурой, включающая:

✅ Семантический анализ навыков через Qdrant + Ollama  
✅ JWT-аутентификацию с тремя ролями  
✅ Self-service профили студентов и работодателей  
✅ Real-time чат через WebSocket  
✅ React SPA + legacy admin panel  
✅ Comprehensive test suite (64 теста)  
✅ Docker-based инфраструктура  

Система готова к дальнейшему развитию и масштабированию.

**Полезные ссылки:**
- [README.md](README.md) — быстрый старт
- [ARCHITECTURE.md](ARCHITECTURE.md) — подробная архитектура
- [HOW_VALUATION_WORKS.md](HOW_VALUATION_WORKS.md) — как работает оценка
- [HOW_TAGS_WORK.md](HOW_TAGS_WORK.md) — как работают теги

---

**Версия документации**: 2.0  
**Дата обновления**: 2025-01-16  
**Автор**: HH.ru Student Evaluator Team
