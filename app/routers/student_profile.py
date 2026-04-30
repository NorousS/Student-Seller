"""
Роутер профиля студента.
Эндпоинты для самообслуживания: профиль, фото, дисциплины, запросы на контакт.
"""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_role
from app.database import get_db
from app.config import settings
from app.discipline_groups import display_discipline_category
from app.models import Student, Discipline, StudentDiscipline, User, UserRole, ContactRequest, ContactRequestStatus, EmployerProfile
from app.schemas import (
    AddDisciplinesRequest,
    ContactRequestRespondRequest,
    ContactRequestResponse,
    DisciplineResponse,
    StudentProfileResponse,
    StudentResponse,
    EvaluationResponse,
    ExperienceLevel,
    SkillMatchResponse,
)
from app.routers.students import build_student_response, get_or_create_discipline
from app.valuation import evaluate_student, DisciplineWithGrade

router = APIRouter(
    prefix="/api/v1/profile/student",
    tags=["student-profile"],
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_PHOTO_SIZE = settings.max_photo_size_mb * 1024 * 1024  # bytes


async def _get_student_for_user(db: AsyncSession, user: User) -> Student:
    """Получить Student по user_id. Если нет — 404."""
    stmt = (
        select(Student)
        .options(selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline))
        .where(Student.user_id == user.id)
    )
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return student


def _build_profile_response(student: Student) -> dict:
    """Построить ответ профиля с about_me и photo_url."""
    base = build_student_response(student)
    photo_url = student.photo_path if student.photo_path else None
    return {**base.model_dump(), "about_me": student.about_me, "photo_url": photo_url}


@router.get("/", response_model=StudentProfileResponse)
async def get_my_profile(
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Получить свой профиль студента."""
    student = await _get_student_for_user(db, current_user)
    return _build_profile_response(student)


@router.put("/", response_model=StudentProfileResponse)
async def update_my_profile(
    about_me: str | None = None,
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Обновить поле 'о себе'."""
    student = await _get_student_for_user(db, current_user)
    if about_me is not None:
        student.about_me = about_me
    await db.commit()

    # Reload
    student = await _get_student_for_user(db, current_user)
    return _build_profile_response(student)

@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото профиля."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG are allowed")

    content = await file.read()
    if len(content) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.max_photo_size_mb}MB")

    student = await _get_student_for_user(db, current_user)

    # Ensure upload dir exists
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Save file
    ext = "jpg" if file.content_type == "image/jpeg" else "png"
    filename = f"student_{student.id}.{ext}"
    filepath = os.path.join(settings.upload_dir, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    student.photo_path = f"/static/uploads/{filename}"
    await db.commit()

    return {"photo_url": student.photo_path}


@router.delete("/photo")
async def delete_photo(
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Удалить фото профиля."""
    student = await _get_student_for_user(db, current_user)
    if student.photo_path:
        # Remove file if exists
        filepath = student.photo_path.replace("/static/uploads/", settings.upload_dir + "/")
        if os.path.exists(filepath):
            os.remove(filepath)
        student.photo_path = None
        await db.commit()
    return {"detail": "Photo deleted"}


@router.get("/disciplines", response_model=list[DisciplineResponse])
async def get_my_disciplines(
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Получить свои дисциплины."""
    student = await _get_student_for_user(db, current_user)
    return [
        DisciplineResponse(
            id=sd.discipline.id,
            name=sd.discipline.name,
            grade=sd.grade,
            category=display_discipline_category(sd.discipline.name, sd.discipline.category),
        )
        for sd in student.student_disciplines
    ]


@router.post("/disciplines", response_model=StudentResponse)
async def update_my_disciplines(
    request: AddDisciplinesRequest,
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Самооценка: добавить/обновить свои дисциплины."""
    student = await _get_student_for_user(db, current_user)

    seen_names: set[str] = set()
    for disc in request.disciplines:
        if disc.name in seen_names:
            continue
        seen_names.add(disc.name)

        discipline = await get_or_create_discipline(db, disc.name)

        link_stmt = select(StudentDiscipline).where(
            StudentDiscipline.student_id == student.id,
            StudentDiscipline.discipline_id == discipline.id,
        )
        link_res = await db.execute(link_stmt)
        existing_link = link_res.scalar_one_or_none()

        if existing_link:
            existing_link.grade = disc.grade
        else:
            new_link = StudentDiscipline(
                student_id=student.id, discipline_id=discipline.id, grade=disc.grade
            )
            db.add(new_link)

    await db.flush()
    user_id = current_user.id
    db.expire_all()

    # Reload
    stmt = (
        select(Student)
        .options(selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline))
        .where(Student.user_id == user_id)
    )
    result = await db.execute(stmt)
    student = result.scalar_one()
    return build_student_response(student)


@router.delete("/disciplines/{discipline_id}", status_code=204)
async def delete_my_discipline(
    discipline_id: int,
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Удалить дисциплину из профиля студента."""
    student = await _get_student_for_user(db, current_user)

    stmt = select(StudentDiscipline).where(
        StudentDiscipline.student_id == student.id,
        StudentDiscipline.discipline_id == discipline_id,
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Дисциплина не найдена у студента")

    await db.delete(link)
    await db.flush()


# --- Contact requests (student side) ---


@router.get("/contact-requests", response_model=list[ContactRequestResponse])
async def get_my_contact_requests(
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Получить входящие запросы на контакт."""
    student = await _get_student_for_user(db, current_user)

    result = await db.execute(
        select(ContactRequest).where(ContactRequest.student_id == student.id)
    )
    requests = result.scalars().all()

    responses = []
    for r in requests:
        # Get employer company name
        emp_result = await db.execute(
            select(EmployerProfile).where(EmployerProfile.user_id == r.employer_id)
        )
        emp = emp_result.scalar_one_or_none()

        responses.append(ContactRequestResponse(
            id=r.id,
            employer_id=r.employer_id,
            student_id=r.student_id,
            status=r.status.value,
            created_at=r.created_at.isoformat(),
            responded_at=r.responded_at.isoformat() if r.responded_at else None,
            employer_company=emp.company_name if emp else None,
        ))

    return responses


@router.post("/contact-requests/{request_id}/respond", response_model=ContactRequestResponse)
async def respond_to_contact_request(
    request_id: int,
    body: ContactRequestRespondRequest,
    current_user: User = Depends(require_role(UserRole.student)),
    db: AsyncSession = Depends(get_db),
):
    """Принять или отклонить запрос на контакт."""
    student = await _get_student_for_user(db, current_user)

    result = await db.execute(
        select(ContactRequest).where(
            ContactRequest.id == request_id,
            ContactRequest.student_id == student.id,
        )
    )
    cr = result.scalar_one_or_none()
    if not cr:
        raise HTTPException(status_code=404, detail="Contact request not found")

    if cr.status != ContactRequestStatus.pending:
        raise HTTPException(status_code=400, detail="Request already responded")

    cr.status = ContactRequestStatus.accepted if body.accept else ContactRequestStatus.rejected
    cr.responded_at = datetime.utcnow()
    await db.commit()
    await db.refresh(cr)

    return ContactRequestResponse(
        id=cr.id,
        employer_id=cr.employer_id,
        student_id=cr.student_id,
        status=cr.status.value,
        created_at=cr.created_at.isoformat(),
        responded_at=cr.responded_at.isoformat() if cr.responded_at else None,
    )


# --- Self-evaluation ---


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_self(
    specialty: str = Query(..., min_length=1, description="Специальность для оценки"),
    experience: ExperienceLevel | None = Query(None, description="Фильтр по опыту работы"),
    top_k: int = Query(default=5, ge=1, le=20, description="Кол-во навыков на дисциплину"),
    excluded_skills: list[str] = Query(default=[], description="Навыки для исключения из расчёта"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
) -> EvaluationResponse:
    """Оценить свою рыночную стоимость как студент."""
    # Получаем студента через helper
    student = await _get_student_for_user(db, current_user)
    
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
