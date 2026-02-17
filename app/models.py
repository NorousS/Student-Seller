"""
SQLAlchemy модели для хранения вакансий и тегов.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


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
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    group_name: Mapped[str | None] = mapped_column(String(50)) # Номер группы
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
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
    
    student_disciplines: Mapped[list["StudentDiscipline"]] = relationship(
        back_populates="discipline",
        cascade="all, delete-orphan"
    )
    
    students: Mapped[list["Student"]] = relationship(
        secondary="student_disciplines",
        viewonly=True
    )
