"""
Роутер для оценки стоимости студентов.
Эндпоинты: evaluate (оценка ЗП) и skills (маппинг дисциплин → навыки hh).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Student
from app.valuation import evaluate_student, DisciplineWithGrade
from app.vector_store import vector_store
from app.schemas import (
    EvaluationResponse,
    ExperienceLevel,
    SkillMatchResponse,
    StudentSkillsResponse,
)

router = APIRouter(prefix="/api/v1/students", tags=["evaluation"])


@router.post("/{student_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_student_endpoint(
    student_id: int,
    specialty: str = Query(..., min_length=1, description="Специальность для оценки"),
    experience: ExperienceLevel | None = Query(None, description="Фильтр по опыту работы"),
    top_k: int = 5,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """
    Оценивает потенциальную рыночную стоимость студента.

    Сопоставляет дисциплины студента с навыками hh.ru через семантический поиск.
    Фильтрует вакансии по специальности и опыту работы.
    """
    # Получаем студента с дисциплинами
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    # Собираем дисциплины с оценками
    disciplines = [
        DisciplineWithGrade(name=sd.discipline.name, grade=sd.grade)
        for sd in student.student_disciplines
    ]
    if not disciplines:
        raise HTTPException(
            status_code=400,
            detail="У студента нет пройденных дисциплин",
        )

    # Оцениваем
    experience_value = experience.value if experience else None
    valuation = await evaluate_student(
        db, disciplines, specialty=specialty,
        experience=experience_value, top_k=top_k,
    )

    # Формируем ответ
    skill_matches = [
        SkillMatchResponse(
            discipline=m.discipline,
            skill_name=m.skill_name,
            similarity=round(m.similarity, 4),
            avg_salary=m.avg_salary,
            vacancy_count=m.vacancy_count,
            grade=m.grade,
            grade_coeff=m.grade_coeff,
        )
        for m in valuation.skill_matches
    ]

    return EvaluationResponse(
        student_id=student.id,
        student_name=student.full_name,
        specialty=specialty,
        experience_filter=experience_value,
        estimated_salary=valuation.estimated_salary,
        confidence=valuation.confidence,
        total_disciplines=valuation.total_disciplines,
        matched_disciplines=valuation.matched_disciplines,
        skill_matches=skill_matches,
    )


@router.get("/{student_id}/skills", response_model=StudentSkillsResponse)
async def get_student_skills(
    student_id: int,
    top_k: int = 3,
    db: AsyncSession = Depends(get_db),
) -> StudentSkillsResponse:
    """
    Возвращает навыки студента в терминах hh.ru с оценками сходства.

    Для каждой дисциплины показывает top-K наиболее похожих навыков hh.ru.
    """
    result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    discipline_names = [sd.discipline.name for sd in student.student_disciplines]
    if not discipline_names:
        return StudentSkillsResponse(
            student_id=student.id,
            student_name=student.full_name,
            skills_by_discipline={},
        )

    # Для каждой дисциплины ищем похожие навыки
    skills_map: dict[str, list[SkillMatchResponse]] = {}
    for discipline in discipline_names:
        similar = await vector_store.search_similar_skills(
            text=discipline,
            top_k=top_k,
        )
        skills_map[discipline] = [
            SkillMatchResponse(
                discipline=discipline,
                skill_name=s["name"],
                similarity=round(s["score"], 4),
                avg_salary=None,
                vacancy_count=0,
            )
            for s in similar
        ]

    return StudentSkillsResponse(
        student_id=student.id,
        student_name=student.full_name,
        skills_by_discipline=skills_map,
    )
