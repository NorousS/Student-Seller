"""
SQLAlchemy модели для хранения вакансий, тегов, пользователей и чатов.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Table, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """Роли пользователей."""
    admin = "admin"
    student = "student"
    employer = "employer"


class PartnershipStatus(str, enum.Enum):
    partner = "partner"
    non_partner = "non_partner"


class ContactRequestStatus(str, enum.Enum):
    """Статусы запросов на контакт."""
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class User(Base):
    """Модель пользователя (аутентификация и авторизация)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связи
    student: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    employer_profile: Mapped["EmployerProfile | None"] = relationship(back_populates="user", uselist=False)


class EmployerProfile(Base):
    """Профиль работодателя."""
    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[str | None] = mapped_column(String(200))
    contact_info: Mapped[str | None] = mapped_column(Text, default=None)
    about_company: Mapped[str | None] = mapped_column(Text, default=None)
    website_url: Mapped[str | None] = mapped_column(String(500), default=None)
    partnership_status: Mapped[PartnershipStatus] = mapped_column(
        Enum(PartnershipStatus), default=PartnershipStatus.non_partner
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="employer_profile")


# Таблица связи Many-to-Many между вакансиями и тегами
vacancy_tag_association = Table(
    "vacancy_tag",
    Base.metadata,
    Column("vacancy_id", Integer, ForeignKey("vacancies.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Vacancy(Base):
    """
    Модель вакансии с hh.ru.
    Хранит основную информацию о вакансии и связь с тегами.
    """
    __tablename__ = "vacancies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    hh_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # ID на hh.ru
    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    
    # Зарплата (может быть не указана)
    salary_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    
    # Уровень опыта (noExperience, between1And3, between3And6, moreThan6)
    experience: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    
    # Какой запрос использовался для поиска
    search_query: Mapped[str] = mapped_column(String(200), index=True)
    
    # Время парсинга
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow
    )
    
    # Связь с тегами через промежуточную таблицу
    tags: Mapped[list["Tag"]] = relationship(
        secondary=vacancy_tag_association,
        back_populates="vacancies",
        lazy="selectin",  # Загружаем теги сразу
    )


class Tag(Base):
    """
    Модель тега (ключевого навыка).
    Уникальное название, связь с вакансиями M2M.
    """
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    
    # Обратная связь с вакансиями
    vacancies: Mapped[list["Vacancy"]] = relationship(
        secondary=vacancy_tag_association,
        back_populates="tags",
        lazy="selectin",
    )


class StudentDiscipline(Base):
    """
    Связь студента с дисциплиной.
    Может быть расширена оценкой, семестром и т.д.
    """
    __tablename__ = "student_disciplines"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"), primary_key=True)
    grade: Mapped[int] = mapped_column(Integer, default=5)  # 3, 4, 5
    
    student: Mapped["Student"] = relationship(back_populates="student_disciplines")
    discipline: Mapped["Discipline"] = relationship(back_populates="student_disciplines", lazy="selectin")


class Student(Base):
    """
    Модель студента.
    """
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    group_name: Mapped[str | None] = mapped_column(String(50)) # Номер группы
    about_me: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    work_ready_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User | None"] = relationship(back_populates="student")
    
    # Связь с дисциплинами через модель-ассоциацию
    student_disciplines: Mapped[list["StudentDiscipline"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Удобный доступ к списку дисциплин (read-only)
    disciplines: Mapped[list["Discipline"]] = relationship(
        secondary="student_disciplines",
        viewonly=True,
        lazy="selectin"
    )


class Discipline(Base):
    """
    Учебная дисциплина.
    """
    __tablename__ = "disciplines"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    student_disciplines: Mapped[list["StudentDiscipline"]] = relationship(
        back_populates="discipline",
        cascade="all, delete-orphan"
    )
    
    students: Mapped[list["Student"]] = relationship(
        secondary="student_disciplines",
        viewonly=True
    )


class ContactRequest(Base):
    """Запрос работодателя на контакт со студентом."""
    __tablename__ = "contact_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    status: Mapped[ContactRequestStatus] = mapped_column(
        Enum(ContactRequestStatus), default=ContactRequestStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    employer: Mapped["User"] = relationship(foreign_keys=[employer_id])
    student: Mapped["Student"] = relationship(foreign_keys=[student_id])
    messages: Mapped[list["Message"]] = relationship(back_populates="contact_request", cascade="all, delete-orphan")


class Message(Base):
    """Сообщение в чате между работодателем и студентом."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    contact_request_id: Mapped[int] = mapped_column(ForeignKey("contact_requests.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contact_request: Mapped["ContactRequest"] = relationship(back_populates="messages")
    sender: Mapped["User"] = relationship(foreign_keys=[sender_id])


class EmployerPartnershipAudit(Base):
    """Аудит изменений статуса партнерства."""
    __tablename__ = "employer_partnership_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[str] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class FunnelEventType(str, enum.Enum):
    view_card = "view_card"
    click_invite = "click_invite"
    paywall_open = "paywall_open"
    invite_created = "invite_created"


class FunnelEvent(Base):
    """Событие воронки работодателя."""
    __tablename__ = "funnel_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[FunnelEventType] = mapped_column(Enum(FunnelEventType), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    employer_id: Mapped[int | None] = mapped_column(ForeignKey("employer_profiles.id", ondelete="SET NULL"), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CompetenceBlock(Base):
    """Блок компетенций (группировка дисциплин)."""
    __tablename__ = "competence_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
