"""Shared student matching and discipline group response helpers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.discipline_groups import (
    display_discipline_group_label,
    infer_discipline_group_semantic,
    normalize_discipline_group_key,
)
from app.models import Student, StudentDiscipline
from app.schemas import (
    AnonymizedStudentResult,
    DisciplineGroupItem,
    DisciplineGroupResponse,
    DisciplineResponse,
    SkillMatchResponse,
)
from app.valuation import DisciplineWithGrade, evaluate_student


async def ensure_discipline_group_key(db: AsyncSession, link: StudentDiscipline) -> str:
    category = link.discipline.category
    if category is None:
        try:
            category = await infer_discipline_group_semantic(link.discipline.name)
        except Exception:
            category = "OTHER"
        link.discipline.category = category
        await db.flush()
    return normalize_discipline_group_key(category)


async def build_disciplines_response(student: Student, db: AsyncSession) -> list[DisciplineResponse]:
    disciplines: list[DisciplineResponse] = []
    for link in student.student_disciplines:
        group_key = await ensure_discipline_group_key(db, link)
        disciplines.append(
            DisciplineResponse(
                id=link.discipline.id,
                name=link.discipline.name,
                grade=link.grade,
                category=display_discipline_group_label(group_key),
            )
        )
    return disciplines


async def build_discipline_groups(student: Student, db: AsyncSession) -> list[DisciplineGroupResponse]:
    grouped: dict[str, list[StudentDiscipline]] = {}
    for link in student.student_disciplines:
        group_key = await ensure_discipline_group_key(db, link)
        grouped.setdefault(group_key, []).append(link)

    order = ["PROGRAMMING", "FOREIGN_LANGUAGES", "SOFT_SKILLS", "EXACT_SCIENCES", "OTHER"]
    ordered_keys = sorted(grouped, key=lambda key: (order.index(key) if key in order else len(order), key))

    response: list[DisciplineGroupResponse] = []
    for key in ordered_keys:
        links = sorted(grouped[key], key=lambda item: (-item.grade, item.discipline.name))
        response.append(
            DisciplineGroupResponse(
                key=key,
                label=display_discipline_group_label(key),
                disciplines=[
                    DisciplineGroupItem(id=link.discipline.id, name=link.discipline.name, grade=link.grade)
                    for link in links
                ],
                avg_grade=round(sum(link.grade for link in links) / len(links), 2),
                count=len(links),
            )
        )
    return response


async def search_matching_students(
    db: AsyncSession,
    job_title: str,
    experience: str | None = None,
    top_k: int = 5,
    limit: int | None = None,
) -> list[AnonymizedStudentResult]:
    stmt = select(Student).options(
        selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline)
    )
    result = await db.execute(stmt)
    students = result.scalars().all()

    matches: list[AnonymizedStudentResult] = []
    for student in students:
        if not student.student_disciplines:
            continue

        disciplines = [
            DisciplineWithGrade(name=link.discipline.name, grade=link.grade)
            for link in student.student_disciplines
        ]

        try:
            valuation = await evaluate_student(
                db,
                disciplines,
                specialty=job_title,
                experience=experience,
                top_k=top_k,
            )
        except Exception:
            continue

        skill_matches = [
            SkillMatchResponse(
                discipline=match.discipline,
                skill_name=match.skill_name,
                similarity=match.similarity,
                avg_salary=match.avg_salary,
                vacancy_count=match.vacancy_count,
                grade=match.grade,
                grade_coeff=match.grade_coeff,
                excluded=match.excluded,
            )
            for match in valuation.skill_matches
        ]

        matches.append(
            AnonymizedStudentResult(
                student_id=student.id,
                photo_url=student.photo_path,
                disciplines=await build_disciplines_response(student, db),
                discipline_groups=await build_discipline_groups(student, db),
                estimated_salary=valuation.estimated_salary,
                confidence=valuation.confidence,
                matched_disciplines=valuation.matched_disciplines,
                total_disciplines=valuation.total_disciplines,
                skill_matches=skill_matches,
            )
        )

    matches.sort(key=lambda item: (item.confidence, item.estimated_salary or 0), reverse=True)
    return matches[:limit] if limit is not None else matches
