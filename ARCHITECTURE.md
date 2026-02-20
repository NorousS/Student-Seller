# Архитектура системы HH.ru Student Evaluator

## Обзор

**HH.ru Student Evaluator** — полнофункциональная платформа для взаимодействия студентов и работодателей с оценкой рыночной стоимости на основе семантического анализа навыков. Система объединяет:

- **hh.ru API** — парсинг вакансий с зарплатами и требуемыми навыками
- **Университетские дисциплины** — академические знания студентов с оценками
- **Семантический поиск (Qdrant + Ollama)** — интеллектуальное сопоставление дисциплин с навыками рынка
- **Профильная система** — JWT-аутентификация с тремя ролями (admin, student, employer)
- **Real-time коммуникация** — WebSocket-чат между студентами и работодателями
- **Современный UI** — React SPA + legacy admin panel

---

## Высокоуровневая архитектура

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

---

## Компоненты системы

### 1. Frontend Layer

#### React SPA (frontend\\src)
- **Технологии**: React 18, TypeScript, Vite, React Router v6
- **State Management**: Zustand (легковесная альтернатива Redux)
- **Структура**:
  - `pages\\` — Login, Register, AdminDashboard, StudentPanel, EmployerPanel
  - `components\\` — переиспользуемые компоненты (Header, ChatWindow, StudentCard)
  - `store\\` — глобальное состояние (authStore, chatStore)
  - `api\\` — клиенты для взаимодействия с backend API
  - `hooks\\` — custom React hooks (useAuth, useWebSocket)

#### Legacy Admin Panel (app\\static\\admin.html)
- **Технология**: Standalone HTML + Vanilla JS + Chart.js
- **Аутентификация**: JWT token в localStorage
- **Функции**: Управление студентами, парсинг вакансий, статистика тегов
- **Доступ**: http://localhost:8000/admin-panel

### 2. Backend Layer (FastAPI)

#### API Routers (app\\routers)

| Роутер | Префикс | Назначение | Доступ |
|--------|---------|------------|--------|
| `auth.py` | `/api/v1/auth/` | Регистрация, вход, обновление токенов | Публичный |
| `students.py` | `/api/v1/students/` | CRUD студентов | Admin только |
| `student_profile.py` | `/api/v1/profile/student/` | Self-service профиля студента | Student только |
| `employer.py` | `/api/v1/employer/` | Поиск студентов, запросы | Employer только |
| `vacancies.py` | `/api/v1/vacancies/` | Парсинг, просмотр вакансий | Парсинг — Admin, просмотр — все |
| `evaluation.py` | `/api/v1/evaluation/` | Оценка стоимости студента | Аутентифицированные |
| `chat.py` | `/api/v1/chat/` | История сообщений | Student/Employer |

#### WebSocket Handler
- **Эндпоинт**: `/ws/chat/{request_id}?token=<jwt>`
- **Протокол**: WebSocket с JWT-аутентификацией через query parameter
- **Назначение**: Real-time двусторонний чат между студентом и работодателем
- **Формат сообщений**: JSON `{"text": "...", "sender_id": 123}`
- **Broadcast**: Сообщения отправляются всем участникам чата

#### Core Services

**auth.py**
- JWT-токены (access + refresh)
- Password hashing (passlib с bcrypt)
- Role-based access control (RBAC)
- Dependency injection для проверки ролей

**parser.py**
- Асинхронные HTTP-запросы к hh.ru API (httpx)
- Извлечение навыков из вакансий
- Нормализация зарплат (RUR, USD, EUR → RUR)
- Batch-обработка вакансий

**valuation.py**
- Семантическое сопоставление дисциплин с навыками
- Взвешенный расчёт зарплаты с учётом:
  - Similarity score (косинусное расстояние)
  - Vacancy count (популярность навыка)
  - Grade coefficient (оценка студента 3/4/5)
- Исключение нерелевантных навыков
- Confidence score (уверенность оценки)

**embeddings.py**
- Интеграция с Ollama API
- Модель: `nomic-embed-text` (768-dim, мультиязычная)
- Async batch embeddings
- Error handling и retry logic

**vector_store.py**
- Интеграция с Qdrant
- Коллекция: `hh_skills` (cosine distance)
- Batch upsert векторов
- Semantic search (top-k с фильтрами)

### 3. Data Layer

#### PostgreSQL (База данных)

**Модели (app\\models.py)**

```
users                    employer_profiles         students
├─ id (PK)              ├─ id (PK)                ├─ id (PK)
├─ email (unique)       ├─ user_id (FK → users)  ├─ user_id (FK → users)
├─ password_hash        ├─ company_name          ├─ full_name
├─ role (enum)          ├─ position              ├─ group_name
├─ is_active            └─ created_at            ├─ about_me
└─ created_at                                     ├─ photo_path
                                                  └─ created_at

student_disciplines      disciplines               vacancies
├─ student_id (PK, FK)  ├─ id (PK)               ├─ id (PK)
├─ discipline_id (PK,FK)├─ name (unique)         ├─ hh_id (unique)
└─ grade (3/4/5)        └─ students (M2M)        ├─ url
                                                  ├─ title
                                                  ├─ salary_from/to
tags                     vacancy_tag (M2M)        ├─ salary_currency
├─ id (PK)              ├─ vacancy_id            ├─ experience
├─ name (unique)        └─ tag_id                ├─ search_query
└─ vacancies (M2M)                               └─ created_at

contact_requests         messages
├─ id (PK)              ├─ id (PK)
├─ employer_id (FK)     ├─ contact_request_id (FK)
├─ student_id (FK)      ├─ sender_id (FK → users)
├─ status (enum)        ├─ text
├─ created_at           ├─ is_read
└─ responded_at         └─ created_at
```

**Индексы**:
- `users.email` (unique), `users.role` (index)
- `vacancies.hh_id` (unique), `vacancies.experience` (index), `vacancies.search_query` (index)
- `tags.name` (unique index)
- `students.full_name` (index)

#### Qdrant (Векторная БД)

**Коллекция**: `hh_skills`
- **Vectors**: 768-dim (nomic-embed-text)
- **Distance**: Cosine (от 0 до 2, чем меньше — тем ближе)
- **Payload**: `{"tag_name": "Python", "tag_id": 123}`
- **Use case**: Семантический поиск навыков по дисциплинам студента

#### Ollama (Embeddings Service)

**Модель**: `nomic-embed-text`
- **Размерность**: 768
- **Языки**: Мультиязычная (включая русский)
- **Endpoint**: `http://ollama:11434/api/embeddings`
- **Формат**: JSON `{"model": "nomic-embed-text", "prompt": "..."}`

---

## Потоки данных

### 1. Регистрация и аутентификация

```
Frontend (Login)
    ↓ POST /api/v1/auth/register { email, password, role }
FastAPI (auth router)
    ↓ Хеширование пароля (passlib bcrypt)
PostgreSQL (users)
    → Сохранение пользователя
    ↓
FastAPI → JWT access token (15 мин) + refresh token (7 дней)
    ↓
Frontend → Сохранение токена в localStorage → Редирект по роли
```

### 2. Парсинг вакансий (Admin)

```
Frontend (/admin) → POST /api/v1/vacancies/parse { query, count }
    ↓
FastAPI (vacancies router) — JWT проверка (require_role("admin"))
    ↓
parser.py → hh.ru API (GET /vacancies?text={query})
    ↓ Извлечение: hh_id, title, salary, experience, key_skills
    ↓
PostgreSQL
    ├─ Vacancy (bulk insert)
    └─ Tag (unique insert, M2M связь)
    ↓
Для каждого нового тега:
    Ollama → Эмбеддинг тега (768-dim вектор)
    ↓
    Qdrant → Upsert вектора в коллекцию hh_skills
    ↓
Frontend ← { total_parsed, tags, average_salary }
```

### 3. Студент редактирует профиль

```
Frontend (/student) → PUT /api/v1/profile/student/me
    { full_name, group_name, about_me }
    ↓
FastAPI (student_profile router) — JWT проверка (require_role("student"))
    ↓ get_current_user → user_id
    ↓
PostgreSQL (students) → UPDATE WHERE user_id = ...
    ↓
Frontend ← 200 OK { updated student profile }

Загрузка фото:
Frontend → POST /api/v1/profile/student/me/photo (multipart/form-data)
    ↓
FastAPI → Сохранение в static\\uploads\\{user_id}_{timestamp}.jpg
    ↓
PostgreSQL (students.photo_path) → UPDATE
    ↓
Frontend ← { photo_url: "/uploads/..." }
```

### 4. Добавление дисциплин студенту

```
Frontend → POST /api/v1/profile/student/me/disciplines
    { disciplines: [{ name: "Python", grade: 5 }, ...] }
    ↓
FastAPI (student_profile router)
    ↓
PostgreSQL
    ├─ disciplines → INSERT IF NOT EXISTS (по name)
    └─ student_disciplines → INSERT (student_id, discipline_id, grade)
    ↓
Frontend ← { updated disciplines list }
```

### 5. Оценка рыночной стоимости студента

```
Frontend → POST /api/v1/evaluation/evaluate
    ?student_id=5&specialty=Python&top_k=5&experience=noExperience
    ↓
FastAPI (evaluation router)
    ↓
valuation.py
    ├─ Шаг 1: Загрузка дисциплин студента (PostgreSQL)
    │         SELECT * FROM student_disciplines WHERE student_id = 5
    │
    ├─ Шаг 2: Семантический фильтр вакансий по специальности
    │         Ollama → Эмбеддинг "Python разработчик"
    │         Qdrant → Поиск похожих search_query
    │         PostgreSQL → WHERE id IN (relevant_vacancy_ids)
    │
    ├─ Шаг 3: Для каждой дисциплины студента
    │   ├─ Ollama → Эмбеддинг дисциплины "Программирование на Python"
    │   ├─ Qdrant → Top-5 ближайших навыков (similarity score)
    │   │         Результат: [("Python", 0.92), ("FastAPI", 0.78), ...]
    │   │
    │   └─ PostgreSQL → Средняя зарплата по каждому навыку
    │             SELECT AVG((salary_from + salary_to)/2)
    │             FROM vacancies v
    │             JOIN vacancy_tag vt ON v.id = vt.vacancy_id
    │             JOIN tags t ON vt.tag_id = t.id
    │             WHERE t.name = 'Python'
    │               AND v.id IN (relevant_vacancy_ids)
    │
    ├─ Шаг 4: Взвешенный расчёт
    │         weighted_salary = Σ (similarity × log1p(vacancy_count) × grade_coef × salary)
    │         confidence = 1 - exp(-total_matches / 20)
    │
    └─ Возврат результата
        {
          "estimated_salary": 185000,
          "confidence": 0.89,
          "skills": [
            {
              "skill": "Python",
              "similarity": 0.92,
              "avg_salary": 200000,
              "vacancy_count": 450,
              "from_discipline": "Программирование на Python"
            },
            ...
          ]
        }
```

### 6. Работодатель ищет студентов

```
Frontend (/employer) → GET /api/v1/employer/students?search=Python&limit=20
    ↓
FastAPI (employer router) — JWT проверка (require_role("employer"))
    ↓
PostgreSQL
    SELECT s.id, s.full_name (анонимизировано), s.group_name
    FROM students s
    JOIN student_disciplines sd ON s.id = sd.student_id
    JOIN disciplines d ON sd.discipline_id = d.id
    WHERE d.name ILIKE '%Python%'
    LIMIT 20
    ↓
Frontend ← { students: [{ id, anonymized_name: "Студент #123", group_name }, ...] }

Просмотр полного профиля:
Frontend → GET /api/v1/employer/students/5
    ↓
FastAPI → PostgreSQL (полная информация: ФИО, фото, дисциплины, about_me)
    ↓
Frontend ← { full student profile }
```

### 7. Отправка запроса на контакт

```
Frontend (/employer) → POST /api/v1/employer/contact-requests
    { student_id: 5, message: "Хотим предложить стажировку" }
    ↓
FastAPI (employer router) — get_current_user (employer)
    ↓
PostgreSQL (contact_requests)
    INSERT (employer_id, student_id, status='pending', created_at=now())
    ↓
Frontend ← { request_id: 42, status: "pending" }
```

### 8. Студент принимает запрос и открывается чат

```
Frontend (/student) → GET /api/v1/profile/student/me/contact-requests
    ↓
FastAPI → PostgreSQL
    SELECT * FROM contact_requests
    WHERE student_id = (current_user.student.id)
    ↓
Frontend ← [{ id: 42, employer: {...}, status: "pending", message: "..." }]

Принятие:
Frontend → POST /api/v1/profile/student/me/contact-requests/42/accept
    ↓
FastAPI → PostgreSQL
    UPDATE contact_requests SET status='accepted', responded_at=now()
    WHERE id=42
    ↓
Frontend → Редирект на /student/chat/42
```

### 9. Real-time чат (WebSocket)

```
Frontend → Подключение WebSocket
    ws://localhost:8000/ws/chat/42?token=<jwt_access_token>
    ↓
FastAPI (WebSocket handler)
    ├─ Проверка JWT токена
    ├─ Проверка, что пользователь — участник contact_request #42
    ├─ Добавление соединения в active_connections[42]
    └─ Ожидание сообщений
    
Отправка сообщения:
Frontend → WebSocket.send(JSON.stringify({ text: "Привет!" }))
    ↓
FastAPI → PostgreSQL
    INSERT INTO messages (contact_request_id=42, sender_id=user_id, text="Привет!")
    ↓
FastAPI → Broadcast всем активным соединениям в чате 42
    ws.send_json({ id: 999, sender_id: 3, text: "Привет!", created_at: "..." })
    ↓
Frontend (оба участника) → Отображение сообщения в чате
```

---

## Сервисы Docker Compose

| Сервис | Образ | Порт | Назначение | Зависимости |
|--------|-------|------|------------|-------------|
| **app** | Dockerfile (multi-stage) | 8000 | FastAPI + React SPA | db, qdrant, ollama |
| **db** | postgres:16-alpine | 5432 | PostgreSQL | — |
| **qdrant** | qdrant/qdrant:v1.13.2 | 6333, 6334 | Векторная БД | — |
| **ollama** | ollama/ollama:latest | 11434 | Embeddings сервис | — |

**Dockerfile (multi-stage build)**:
1. Stage 1 (Node.js): Сборка React-фронтенда (`npm run build`)
2. Stage 2 (Python 3.12): Копирование dist + установка Python-зависимостей (uv)

**Volumes**:
- `postgres_data` — персистентность БД
- `qdrant_data` — персистентность векторов
- `ollama_data` — кэш моделей

---

## Стек технологий

### Backend
| Технология | Версия | Назначение |
|------------|--------|------------|
| Python | 3.12 | Язык программирования |
| FastAPI | latest | Асинхронный веб-фреймворк |
| SQLAlchemy | 2.0+ | ORM (async mode) |
| Pydantic | v2 | Валидация схем |
| asyncpg | latest | Async PostgreSQL driver |
| passlib | latest | Password hashing (bcrypt) |
| PyJWT | latest | JWT токены |
| httpx | latest | Async HTTP client |
| qdrant-client | latest | Qdrant Python SDK |
| pytest | latest | Тестирование (asyncio_mode=auto) |
| uv | latest | Менеджер пакетов |

### Frontend
| Технология | Версия | Назначение |
|------------|--------|------------|
| React | 18 | UI-библиотека |
| TypeScript | 5.x | Типизация |
| Vite | 5.x | Сборщик и dev-сервер |
| React Router | 6.x | Маршрутизация |
| Zustand | latest | State management |
| Axios | latest | HTTP-клиент |

### Инфраструктура
| Технология | Версия | Назначение |
|------------|--------|------------|
| PostgreSQL | 16 | Реляционная БД |
| Qdrant | 1.13.2 | Векторная БД |
| Ollama | latest | LLM и embeddings |
| Docker | latest | Контейнеризация |
| Docker Compose | latest | Оркестрация |

---

## Безопасность

### JWT Authentication
- **Access token**: 15 минут (короткая жизнь для безопасности)
- **Refresh token**: 7 дней (для обновления access token без повторного входа)
- **Algorithm**: HS256
- **Secret key**: Загружается из переменных окружения

### Password Security
- **Hashing**: bcrypt через passlib
- **Rounds**: 12 (по умолчанию)
- **Пароли не хранятся в открытом виде**

### Role-Based Access Control (RBAC)
```python
# Пример защиты эндпоинта
@router.get("/admin-only")
async def admin_route(user: User = Depends(require_role("admin"))):
    return {"message": "Только для admin"}
```

### WebSocket Security
- JWT передаётся в query parameter `?token=<jwt>`
- Проверка принадлежности пользователя к чату
- Защита от межсайтовых атак (CORS настроен)

### File Upload Security
- Ограничение размера файла (5 MB)
- Проверка MIME-типов (только изображения)
- Уникальные имена файлов (`{user_id}_{timestamp}.jpg`)

---

## Масштабируемость

### Текущие ограничения
- **Single-instance**: Один контейнер FastAPI
- **WebSocket**: In-memory connections (не переживут рестарт)
- **File storage**: Локальная файловая система

### Пути масштабирования
1. **Load balancing**: Nginx + несколько инстансов FastAPI
2. **WebSocket**: Redis Pub/Sub для broadcast между инстансами
3. **File storage**: S3-совместимое хранилище (MinIO, AWS S3)
4. **Database**: PostgreSQL replication (master-slave)
5. **Cache**: Redis для кэширования эмбеддингов и результатов поиска
6. **Background tasks**: Celery для асинхронных задач (парсинг, эмбеддинги)

---

## Мониторинг и логирование

### Текущие возможности
- **Health check**: `GET /health` — проверка доступности БД, Qdrant, Ollama
- **API docs**: `GET /docs` (Swagger UI), `GET /redoc` (ReDoc)
- **Console logs**: Логирование запросов и ошибок в stdout

### Рекомендации
- **Prometheus + Grafana**: Метрики FastAPI, PostgreSQL, Qdrant
- **ELK Stack**: Централизованное логирование
- **Sentry**: Трекинг ошибок в production

---

## API Endpoints (полный список)

### Аутентификация
- `POST /api/v1/auth/register` — Регистрация
- `POST /api/v1/auth/login` — Вход
- `POST /api/v1/auth/refresh` — Обновление токена
- `GET /api/v1/auth/me` — Текущий пользователь

### Студенты (Admin CRUD)
- `GET /api/v1/students/` — Список студентов
- `POST /api/v1/students/` — Создание
- `GET /api/v1/students/{id}` — Детали
- `PUT /api/v1/students/{id}` — Редактирование
- `DELETE /api/v1/students/{id}` — Удаление
- `POST /api/v1/students/{id}/disciplines` — Добавление дисциплин

### Профиль студента (Self-service)
- `GET /api/v1/profile/student/me` — Мой профиль
- `PUT /api/v1/profile/student/me` — Редактирование
- `POST /api/v1/profile/student/me/photo` — Загрузка фото
- `POST /api/v1/profile/student/me/disciplines` — Добавление дисциплин
- `DELETE /api/v1/profile/student/me/disciplines/{id}` — Удаление дисциплины
- `GET /api/v1/profile/student/me/contact-requests` — Запросы на контакт
- `POST /api/v1/profile/student/me/contact-requests/{id}/accept` — Принять
- `POST /api/v1/profile/student/me/contact-requests/{id}/reject` — Отклонить

### Профиль работодателя
- `GET /api/v1/profile/employer/me` — Мой профиль
- `PUT /api/v1/profile/employer/me` — Редактирование

### Работодатель (Поиск и контакты)
- `GET /api/v1/employer/students` — Поиск студентов
- `GET /api/v1/employer/students/{id}` — Полный профиль
- `POST /api/v1/employer/contact-requests` — Отправить запрос
- `GET /api/v1/employer/contact-requests` — Мои запросы

### Вакансии
- `POST /api/v1/vacancies/parse` — Парсинг (Admin)
- `GET /api/v1/vacancies/` — Список вакансий
- `GET /api/v1/vacancies/tags` — Статистика тегов

### Оценка
- `POST /api/v1/evaluation/evaluate` — Оценка стоимости
- `GET /api/v1/evaluation/skills` — Навыки студента

### Чат
- `GET /api/v1/chat/{request_id}/messages` — История
- `POST /api/v1/chat/{request_id}/mark-read` — Прочитано
- `WS /ws/chat/{request_id}?token=<jwt>` — WebSocket

---

## Тестирование

**64 теста** (pytest с asyncio_mode=auto):
- `tests\\test_auth.py` — Регистрация, вход, токены
- `tests\\test_students.py` — Admin CRUD
- `tests\\test_student_profile.py` — Self-service профиля
- `tests\\test_employer.py` — Поиск, запросы
- `tests\\test_chat.py` — WebSocket чат

**Fixtures** (conftest.py):
- `async_client` — TestClient для FastAPI
- `test_user_admin`, `test_user_student`, `test_user_employer` — Тестовые пользователи
- `auth_headers_*` — Предзаполненные JWT-заголовки

---

## Заключение

Архитектура HH.ru Student Evaluator построена на современных асинхронных технологиях с чётким разделением ответственности:
- **Frontend** — модульный React SPA с роутингом и state management
- **Backend** — FastAPI с ролевой моделью, WebSocket и REST API
- **Data** — PostgreSQL для реляционных данных, Qdrant для семантического поиска
- **AI** — Ollama для генерации эмбеддингов, взвешенный алгоритм оценки

Система готова к горизонтальному масштабированию и дальнейшему развитию функционала.

