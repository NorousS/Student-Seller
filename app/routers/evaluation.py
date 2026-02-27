"""
Роутер для оценки стоимости студентов.
Эндпоинты: evaluate (оценка ЗП) и skills (маппинг дисциплин → навыки hh).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.competence import aggregate_by_competence, DisciplineData
from app.database import get_db
from app.models import Student, User, UserRole
from app.valuation import evaluate_student, DisciplineWithGrade
from app.vector_store import vector_store
from app.schemas import (
    CompetenceBlockResponse,
    EnhancedEvaluationResponse,
    EvaluationResponse,
    ExperienceLevel,
    FactorBreakdown,
    SkillMatchResponse,
    StudentSkillsResponse,
)

router = APIRouter(
    prefix="/api/v1/students",
    tags=["evaluation"],
    dependencies=[Depends(require_role(UserRole.admin, UserRole.employer))],
)


@router.post("/{student_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_student_endpoint(
    student_id: int,
    specialty: str = Query(..., min_length=1, description="Специальность для оценки"),
    experience: ExperienceLevel | None = Query(None, description="Фильтр по опыту работы"),
    top_k: int = Query(default=5, ge=1, le=20, description="Кол-во навыков на дисциплину"),
    excluded_skills: list[str] = Query(default=[], description="Навыки для исключения из расчёта"),
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
        excluded_skills=excluded_skills if excluded_skills else None,
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
            excluded=m.excluded,
        )
        for m in valuation.skill_matches
    ]

    return EvaluationResponse(
        student_id=student.id,
        student_name=student.full_name,
        specialty=specialty,
        experience_filter=experience_value,
        top_k=top_k,
        excluded_skills=excluded_skills or [],
        estimated_salary=valuation.estimated_salary,
        confidence=valuation.confidence,
        total_disciplines=valuation.total_disciplines,
        matched_disciplines=valuation.matched_disciplines,
        skill_matches=skill_matches,
    )


@router.get("/{student_id}/skills", response_model=StudentSkillsResponse)
async def get_student_skills(
    student_id: int,
    top_k: int = Query(default=3, ge=1, le=20),
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


@router.post("/{student_id}/evaluate-enhanced", response_model=EnhancedEvaluationResponse)
async def evaluate_student_enhanced(
    student_id: int,
    specialty: str = Query(..., min_length=1, description="Специальность для оценки"),
    experience: ExperienceLevel | None = Query(None, description="Фильтр по опыту"),
    top_k: int = Query(default=5, ge=1, le=20, description="Навыков на дисциплину"),
    excluded_skills: list[str] = Query(default=[], description="Навыки для исключения"),
    db: AsyncSession = Depends(get_db),
) -> EnhancedEvaluationResponse:
    """
    Расширенная оценка с разбивкой по факторам и блокам компетенций.
    """
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    disciplines = [
        DisciplineWithGrade(name=sd.discipline.name, grade=sd.grade)
        for sd in student.student_disciplines
    ]
    if not disciplines:
        raise HTTPException(status_code=400, detail="У студента нет дисциплин")

    experience_value = experience.value if experience else None
    valuation = await evaluate_student(
        db, disciplines, specialty=specialty,
        experience=experience_value, top_k=top_k,
        excluded_skills=excluded_skills if excluded_skills else None,
    )

    # Build skill matches response
    skill_matches = [
        SkillMatchResponse(
            discipline=m.discipline, skill_name=m.skill_name,
            similarity=round(m.similarity, 4), avg_salary=m.avg_salary,
            vacancy_count=m.vacancy_count, grade=m.grade,
            grade_coeff=m.grade_coeff, excluded=m.excluded,
        )
        for m in valuation.skill_matches
    ]

    # Factor breakdown
    factor_breakdown = [
        FactorBreakdown(factor_name=f.factor_name, contribution=f.contribution)
        for f in valuation.factor_breakdown
    ]

    # Build competence blocks
    disc_data_list = []
    for sd in student.student_disciplines:
        disc_skills = [m for m in valuation.skill_matches if m.discipline == sd.discipline.name]
        skill_tags = [m.skill_name for m in disc_skills if not m.excluded]
        market_val = None
        for m in disc_skills:
            if m.avg_salary and not m.excluded:
                if market_val is None:
                    market_val = 0
                market_val += m.avg_salary * m.similarity

        disc_data_list.append(DisciplineData(
            name=sd.discipline.name,
            grade=sd.grade,
            category=sd.discipline.category,
            skill_tags=skill_tags,
            market_value=market_val,
        ))

    competence_blocks = aggregate_by_competence(disc_data_list)

    return EnhancedEvaluationResponse(
        student_id=student.id,
        student_name=student.full_name,
        specialty=specialty,
        experience_filter=experience_value,
        top_k=top_k,
        excluded_skills=excluded_skills or [],
        estimated_salary=valuation.estimated_salary,
        confidence=valuation.confidence,
        total_disciplines=valuation.total_disciplines,
        matched_disciplines=valuation.matched_disciplines,
        skill_matches=skill_matches,
        factor_breakdown=factor_breakdown,
        competence_blocks=competence_blocks,
    )


@router.get("/{student_id}/valuation-export")
async def export_valuation(
    student_id: int,
    specialty: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Экспорт объяснения оценки в JSON."""
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    disciplines = [
        DisciplineWithGrade(name=sd.discipline.name, grade=sd.grade)
        for sd in student.student_disciplines
    ]
    if not disciplines:
        raise HTTPException(status_code=400, detail="У студента нет дисциплин")

    valuation = await evaluate_student(db, disciplines, specialty=specialty)

    return {
        "student_id": student.id,
        "student_name": student.full_name,
        "specialty": specialty,
        "estimated_salary": valuation.estimated_salary,
        "confidence": valuation.confidence,
        "factor_breakdown": [
            {"factor_name": f.factor_name, "contribution": f.contribution}
            for f in valuation.factor_breakdown
        ],
        "top_skill_tags": [
            {"skill": m.skill_name, "similarity": round(m.similarity, 4), "salary": m.avg_salary}
            for m in sorted(valuation.skill_matches, key=lambda x: x.similarity, reverse=True)[:10]
            if not m.excluded
        ],
    }
