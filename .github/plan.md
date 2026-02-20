# План: Улучшение оценки студентов

## Проблема

Текущая оценка студента не учитывает:
- Специальность (направление) — теги берутся из всех вакансий без фильтрации
- Опыт работы — зарплата зависит от уровня, но сейчас всё смешивается
- Оценки по дисциплинам — студент с «5» и «3» оцениваются одинаково
- Выбросы от редких тегов — тег из 1 вакансии может исказить оценку

## Подход

Разделение на два параллельных агента:
- **Агент 1** — Backend (модели, логика, API)
- **Агент 2** — Frontend (UI, формы, отображение)

---

## Агент 1 — Backend

### Файлы для изменения

| Файл | Что меняется |
|------|-------------|
| `app/models.py` | + `experience` в Vacancy, + `grade` в StudentDiscipline |
| `app/schemas.py` | + grade в студент-схемах, + specialty/experience в evaluation |
| `app/parser.py` | Сохранять experience из API hh.ru в ParsedVacancy |
| `app/routers/vacancies.py` | Сохранять experience при создании Vacancy |
| `app/routers/students.py` | Поддержка grade при добавлении дисциплин |
| `app/routers/evaluation.py` | Новые параметры: specialty, experience |
| `app/valuation.py` | Новый алгоритм: фильтр по specialty, experience, grade-коэфф., мин. 3 тега |
| `app/vector_store.py` | Без изменений (семантический поиск переиспользуется) |
| `tests/test_students.py` | Обновить тесты под новые поля |

### Задачи

- [ ] **1.1 Модель Vacancy: добавить поле `experience`**
  - Файл: `app/models.py`
  - Добавить `experience: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)`
  - Значения: `noExperience`, `between1And3`, `between3And6`, `moreThan6` (из API hh.ru)

- [ ] **1.2 Модель StudentDiscipline: добавить поле `grade`**
  - Файл: `app/models.py`
  - Добавить `grade: Mapped[int] = mapped_column(Integer, default=5)`
  - Допустимые значения: 3, 4, 5

- [ ] **1.3 Парсер: извлекать experience из API hh.ru**
  - Файл: `app/parser.py`
  - Добавить поле `experience: str | None` в `ParsedVacancy`
  - В `_fetch_vacancy_details`: извлекать `data["experience"]["id"]` из ответа API
  - В `search_vacancies`: передавать experience в ParsedVacancy

- [ ] **1.4 Роутер вакансий: сохранять experience**
  - Файл: `app/routers/vacancies.py`
  - При создании `Vacancy` передавать `experience=parsed.experience`

- [ ] **1.5 Схемы: обновить Pydantic-модели**
  - Файл: `app/schemas.py`
  - `StudentCreate` и добавление дисциплин: `disciplines` → `list[DisciplineWithGrade]` где `DisciplineWithGrade = {name: str, grade: int}`
  - `EvaluationResponse`: добавить `specialty: str`, `experience_filter: str | None`
  - Новые query-параметры для evaluate: `specialty: str`, `experience: ExperienceLevel | None`
  - `DisciplineResponse`: добавить `grade: int`

- [ ] **1.6 Роутер студентов: поддержка grade**
  - Файл: `app/routers/students.py`
  - `create_student`: при создании StudentDiscipline передавать grade
  - `add_disciplines_to_student`: аналогично принимать grade
  - Ответ: возвращать grade для каждой дисциплины

- [ ] **1.7 Алгоритм оценки: переписать `valuation.py`**
  - Файл: `app/valuation.py`
  - Новая сигнатура: `evaluate_student(db, disciplines_with_grades, specialty, experience, top_k)`
  - **Фильтрация по specialty**: семантическое сравнение `specialty` с `Vacancy.search_query`
    - Через Ollama: получить эмбеддинг specialty → сравнить с эмбеддингами search_query
    - Или проще: через ILIKE/полнотекст на уровне SQL (проще и быстрее)
    - **Решение**: использовать `ILIKE '%specialty%'` на `Vacancy.search_query` — проще, БД пересоздаётся
    - UPD: пользователь выбрал семантическое — нужно: получить эмбеддинг specialty, получить эмбеддинги всех уникальных search_query из БД, отфильтровать с порогом сходства >= 0.7, затем использовать только вакансии с подходящими search_query
  - **Фильтрация по experience**: `Vacancy.experience == experience` (если указан)
  - **Фильтр мин. 3 тега**: тег учитывается только если `vacancy_count >= 3` (в отфильтрованной выборке)
  - **Grade-коэффициент**: `weight = similarity * log1p(vacancy_count) * grade_coeff`
    - grade 3 → 0.75, grade 4 → 0.85, grade 5 → 1.0
  - **Сигнатура get_tag_salary_stats**: добавить фильтры `search_queries: list[str]`, `experience: str | None`

- [ ] **1.8 Роутер evaluation: новые параметры**
  - Файл: `app/routers/evaluation.py`
  - `evaluate_student_endpoint`: добавить параметры `specialty: str` (обязательный), `experience: ExperienceLevel | None`
  - Передавать `disciplines_with_grades` вместо просто имён (брать grade из StudentDiscipline)
  - Обновить endpoint `/skills` аналогично

- [ ] **1.9 Обновить тесты**
  - Файл: `tests/test_students.py`
  - Обновить JSON в тестах: `disciplines` теперь список объектов `{name, grade}`
  - Проверить что grade сохраняется и возвращается

- [ ] **1.10 Семантическая фильтрация specialty**
  - Новая функция в `app/valuation.py` или отдельный хелпер
  - `get_matching_search_queries(db, specialty)`:
    1. `SELECT DISTINCT search_query FROM vacancies`
    2. Для каждого уникального search_query → получить эмбеддинг (можно кэшировать)
    3. Получить эмбеддинг specialty
    4. Вычислить cosine similarity
    5. Вернуть search_queries с similarity >= 0.7
  - **Оптимизация**: кэшировать эмбеддинги search_query в памяти (их мало)

---

## Агент 2 — Frontend

### Файлы для изменения

| Файл | Что меняется |
|------|-------------|
| `app/static/index.html` | Вся UI-часть |

### Задачи

- [ ] **2.1 Вкладка «Оценка»: добавить поле «Специальность»**
  - Текстовое поле ввода (input) с placeholder "Например: Python разработчик"
  - Обязательное поле — без него кнопка «Оценить» неактивна
  - Располагается над/рядом с выбором студента

- [ ] **2.2 Вкладка «Оценка»: добавить выбор опыта работы**
  - Dropdown (select) с вариантами:
    - «Без опыта» (noExperience)
    - «1-3 года» (between1And3)
    - «3-6 лет» (between3And6)
    - «6+ лет» (moreThan6)
    - «Любой» (null/пустое — не фильтрует)
  - Рядом с полем специальности

- [ ] **2.3 Вкладка «Оценка»: обновить запрос к API**
  - `evaluateStudent()`: добавить `specialty` и `experience` в query параметры POST `/evaluate`

- [ ] **2.4 Вкладка «Студенты»: оценки при создании**
  - При добавлении дисциплин — рядом с каждой кнопки 3/4/5
  - По умолчанию выбрана «5»
  - Визуально: кнопки-тогглы (одна из трёх нажата)
  - При отправке: `disciplines: [{name: "Python", grade: 5}, {name: "SQL", grade: 4}]`

- [ ] **2.5 Вкладка «Студенты»: оценки при добавлении дисциплин**
  - Аналогично 2.4, но для endpoint POST `/{id}/disciplines`
  - Каждая дисциплина с grade

- [ ] **2.6 Профиль студента: отображение оценок**
  - В списке дисциплин показывать grade (badge/chip рядом с названием)
  - Цветовое кодирование: 5 = зелёный, 4 = жёлтый, 3 = оранжевый

- [ ] **2.7 Результаты оценки: обновить отображение**
  - Показывать использованную специальность и опыт
  - В таблице skill_matches: показывать grade дисциплины
  - Если тег отфильтрован (< 3 вакансий) — показать это визуально

---

## Порядок работы

1. **Агент 1 начинает** с задач 1.1–1.5 (модели и схемы) — это база для всего
2. **Агент 2 начинает** с задач 2.1–2.2 (UI-разметка) параллельно
3. **Агент 1** делает 1.6–1.8 (роутеры и алгоритм)
4. **Агент 2** делает 2.3–2.7 (логика фронтенда) после того как API стабилизируется
5. **Агент 1** делает 1.9–1.10 (тесты и семантика)
6. Финальная проверка: запуск тестов, ручная проверка UI

## Ключевые решения

- **Specialty matching**: семантическое — через Ollama эмбеддинги сравниваем specialty с search_query вакансий (порог 0.7)
- **Experience в Vacancy**: новое поле, БД пересоздаётся — nullable не нужен, но оставим nullable на случай если у вакансии не указан опыт
- **Grade**: обязательный, всегда 3/4/5, хранится в `student_disciplines`
- **Мин. 3 тега**: фильтр применяется ПОСЛЕ фильтрации по specialty и experience
- **Коэффициенты**: 3→0.75, 4→0.85, 5→1.0 (захардкожены, можно вынести в config)

---

## Команды (PowerShell)

```powershell
# Пересоздание БД (после изменения моделей)
docker-compose down -v
docker-compose up db -d
Start-Sleep -Seconds 5

# Установка зависимостей
uv sync

# Запуск приложения для разработки
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/hh_parser"
uv run uvicorn app.main:app --reload

# Запуск тестов (нужен PostgreSQL на localhost)
uv run pytest tests/ -v

# Запуск одного теста
uv run pytest tests/test_students.py::test_create_student_simple -v

# Запуск всех сервисов
docker-compose up --build -d
```
