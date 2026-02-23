"""
Pydantic схемы для валидации запросов и ответов API.
"""

from enum import Enum

from pydantic import BaseModel, Field


# --- Auth ---

class UserRoleEnum(str, Enum):
    """Роли пользователей для API."""
    admin = "admin"
    student = "student"
    employer = "employer"


class RegisterRequest(BaseModel):
    """Запрос на регистрацию."""
    email: str = Field(..., min_length=5, max_length=255, description="Email пользователя")
    password: str = Field(..., min_length=6, max_length=128, description="Пароль")
    role: UserRoleEnum = Field(..., description="Роль: admin, student, employer")
    # Для студента
    full_name: str | None = Field(None, max_length=200, description="ФИО (обязательно для student)")
    group_name: str | None = Field(None, max_length=50, description="Группа (для student)")
    # Для работодателя
    company_name: str | None = Field(None, max_length=200, description="Название компании (для employer)")


class LoginRequest(BaseModel):
    """Запрос на вход."""
    email: str = Field(..., description="Email")
    password: str = Field(..., description="Пароль")


class TokenResponse(BaseModel):
    """Ответ с JWT токенами."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Запрос на обновление токена."""
    refresh_token: str


class UserResponse(BaseModel):
    """Информация о пользователе."""
    id: int
    email: str
    role: UserRoleEnum
    is_active: bool

    class Config:
        from_attributes = True


class ExperienceLevel(str, Enum):
    """
    Уровень опыта для фильтрации вакансий.
    Значения соответствуют API hh.ru.
    """
    NO_EXPERIENCE = "noExperience"      # Нет опыта
    BETWEEN_1_AND_3 = "between1And3"    # От 1 до 3 лет (Junior+)
    BETWEEN_3_AND_6 = "between3And6"    # От 3 до 6 лет (Middle)
    MORE_THAN_6 = "moreThan6"           # Более 6 лет (Senior)


class ParseRequest(BaseModel):
    """Запрос на парсинг вакансий."""
    query: str = Field(..., min_length=1, max_length=200, description="Ключевое слово для поиска")
    count: int = Field(default=50, ge=1, le=100, description="Количество вакансий для парсинга")
    experience: ExperienceLevel | None = Field(
        default=None, 
        description="Фильтр по опыту работы (опционально)"
    )


class TagCount(BaseModel):
    """Информация о теге и его частоте."""
    name: str
    count: int


class ParseResponse(BaseModel):
    """Ответ после парсинга вакансий."""
    total_parsed: int = Field(..., description="Всего распаршено вакансий")
    tags: list[TagCount] = Field(default_factory=list, description="Теги с количеством")
    average_salary: float | None = Field(None, description="Средняя зарплата (если указана)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_parsed": 50,
                "tags": [
                    {"name": "Python", "count": 45},
                    {"name": "SQL", "count": 30},
                    {"name": "Docker", "count": 25},
                ],
                "average_salary": 150000.0
            }
        }


class VacancyResponse(BaseModel):
    """Информация о вакансии."""
    id: int
    hh_id: str
    url: str
    title: str
    salary_from: int | None
    salary_to: int | None
    salary_currency: str | None
    tags: list[str]
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Ответ эндпоинта проверки здоровья."""
    status: str = "ok"


class VacanciesWithStatsResponse(BaseModel):
    """Ответ GET /vacancies со статистикой."""
    total_count: int = Field(..., description="Общее количество вакансий")
    vacancies: list[VacancyResponse] = Field(default_factory=list, description="Список вакансий")
    tags: list[TagCount] = Field(default_factory=list, description="Теги с количеством упоминаний")
    average_salary: float | None = Field(None, description="Средняя зарплата")


# --- Схемы оценки стоимости студента ---


class SkillMatchResponse(BaseModel):
    """Сопоставление дисциплины с навыком hh.ru."""
    discipline: str = Field(..., description="Название дисциплины студента")
    skill_name: str = Field(..., description="Название навыка hh.ru")
    similarity: float = Field(..., description="Косинусное сходство (0..1)")
    avg_salary: float | None = Field(None, description="Средняя ЗП вакансий с этим навыком")
    vacancy_count: int = Field(0, description="Количество вакансий с этим навыком")
    grade: int = Field(default=5, description="Оценка студента по дисциплине")
    grade_coeff: float = Field(default=1.0, description="Коэффициент оценки")
    excluded: bool = Field(default=False, description="Навык исключён из расчёта пользователем")


class EvaluationResponse(BaseModel):
    """Результат оценки потенциальной стоимости студента."""
    student_id: int
    student_name: str
    specialty: str = Field(..., description="Специальность для оценки")
    experience_filter: str | None = Field(None, description="Фильтр по опыту")
    top_k: int = Field(default=5, description="Кол-во навыков на дисциплину")
    excluded_skills: list[str] = Field(default_factory=list, description="Исключённые навыки")
    estimated_salary: float | None = Field(None, description="Оценочная ЗП (RUB)")
    confidence: float = Field(..., description="Уверенность оценки (0..1)")
    total_disciplines: int = Field(..., description="Всего дисциплин у студента")
    matched_disciplines: int = Field(..., description="Дисциплин с найденными навыками")
    skill_matches: list[SkillMatchResponse] = Field(
        default_factory=list, description="Детальная разбивка по навыкам"
    )


class StudentSkillsResponse(BaseModel):
    """Навыки студента в терминах hh.ru."""
    student_id: int
    student_name: str
    skills_by_discipline: dict[str, list[SkillMatchResponse]] = Field(
        default_factory=dict,
        description="Маппинг: дисциплина → список ближайших навыков hh.ru",
    )


class DisciplineBase(BaseModel):
    """Базовая схема дисциплины."""
    name: str = Field(..., min_length=1, max_length=200, description="Название дисциплины")


class DisciplineCreate(DisciplineBase):
    """Схема для создания дисциплины."""
    pass


class DisciplineWithGrade(BaseModel):
    """Дисциплина с оценкой для создания/добавления."""
    name: str = Field(..., min_length=1, max_length=200, description="Название дисциплины")
    grade: int = Field(default=5, ge=3, le=5, description="Оценка: 3, 4 или 5")


class DisciplineResponse(DisciplineBase):
    """Схема для ответа с данными дисциплины."""
    id: int
    grade: int = Field(default=5, description="Оценка: 3, 4 или 5")
    
    class Config:
        from_attributes = True


class StudentBase(BaseModel):
    """Базовая схема студента."""
    full_name: str = Field(..., min_length=1, max_length=200, description="ФИО студента")
    group_name: str | None = Field(None, max_length=50, description="Номер группы")


class StudentCreate(StudentBase):
    """Схема для создания студента."""
    disciplines: list[DisciplineWithGrade] = Field(default_factory=list, description="Список дисциплин с оценками")


class StudentResponse(StudentBase):
    """Схема для ответа с данными студента."""
    id: int
    disciplines: list[DisciplineResponse] = Field(default_factory=list, description="Список дисциплин")
    
    class Config:
        from_attributes = True


class StudentProfileResponse(StudentResponse):
    """Расширенная схема профиля студента (включает about_me, photo_url)."""
    about_me: str | None = None
    photo_url: str | None = None


class AddDisciplinesRequest(BaseModel):
    """Запрос на добавление дисциплин студенту."""
    disciplines: list[DisciplineWithGrade] = Field(..., description="Список дисциплин с оценками")


# --- Employer schemas ---


class EmployerProfileResponse(BaseModel):
    """Профиль работодателя."""
    id: int
    user_id: int
    company_name: str | None
    position: str | None
    contact_info: str | None = None
    about_company: str | None = None
    website_url: str | None = None

    class Config:
        from_attributes = True


class EmployerProfileUpdate(BaseModel):
    """Обновление профиля работодателя."""
    company_name: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=200)
    contact_info: str | None = Field(None, max_length=2000)
    about_company: str | None = Field(None, max_length=5000)
    website_url: str | None = Field(None, max_length=500)


class EmployerSearchRequest(BaseModel):
    """Запрос на поиск студентов по должности."""
    job_title: str = Field(..., min_length=1, description="Название должности")
    experience: ExperienceLevel | None = Field(None, description="Фильтр по опыту")
    top_k: int = Field(default=5, ge=1, le=20, description="Навыков на дисциплину")


class AnonymizedStudentResult(BaseModel):
    """Анонимизированный результат поиска студента."""
    student_id: int
    photo_url: str | None
    disciplines: list[DisciplineResponse]
    estimated_salary: float | None
    confidence: float
    matched_disciplines: int
    total_disciplines: int
    skill_matches: list[SkillMatchResponse] = Field(
        default_factory=list, description="Детальная разбивка по навыкам"
    )


class AnonymizedStudentProfile(BaseModel):
    """Анонимизированный профиль студента (для работодателя)."""
    student_id: int
    photo_url: str | None
    disciplines: list[DisciplineResponse]
    about_me: str | None = None  # Только если контакт accepted
    contact_status: str | None = None  # pending/accepted/rejected/null


class ContactRequestCreate(BaseModel):
    """Ответ при создании запроса на контакт."""
    id: int
    employer_id: int
    student_id: int
    status: str
    created_at: str

    class Config:
        from_attributes = True


class ContactRequestResponse(BaseModel):
    """Ответ с данными запроса на контакт."""
    id: int
    employer_id: int
    student_id: int
    status: str
    created_at: str
    responded_at: str | None = None
    employer_company: str | None = None

    class Config:
        from_attributes = True


class ContactRequestRespondRequest(BaseModel):
    """Запрос на ответ на запрос контакта."""
    accept: bool = Field(..., description="True = принять, False = отклонить")
