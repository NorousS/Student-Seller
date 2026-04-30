"""Cached student valuation helpers."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Student, StudentDiscipline
from app.valuation import DisciplineWithGrade, evaluate_student


async def refresh_student_valuation(db: AsyncSession, student_id: int) -> float | None:
    """Refresh and store cached estimated salary for a student."""
    stmt = (
        select(Student)
        .options(selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline))
        .where(Student.id == student_id)
    )
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    if not student or not student.student_disciplines:
        return None

    disciplines = [
        DisciplineWithGrade(name=sd.discipline.name, grade=sd.grade)
        for sd in student.student_disciplines
    ]

    try:
        valuation = await evaluate_student(db, disciplines, specialty="", experience=None)
    except Exception:
        return student.estimated_salary

    student.estimated_salary = valuation.estimated_salary
    student.valuation_updated_at = datetime.utcnow()
    await db.flush()
    return student.estimated_salary


async def refresh_all_student_valuations(db: AsyncSession) -> int:
    result = await db.execute(select(Student.id))
    student_ids = [row[0] for row in result.all()]
    refreshed = 0
    for student_id in student_ids:
        before = await refresh_student_valuation(db, student_id)
        if before is not None:
            refreshed += 1
    return refreshed
