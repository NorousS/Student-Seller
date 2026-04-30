"""
Роутер работодателя.
Поиск студентов, анонимизированные профили, запросы на контакт.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_role
from app.database import get_db
from app.discipline_groups import display_discipline_category, ordered_group_names
from app.models import (
    ContactRequest,
    ContactRequestStatus,
    EmployerProfile,
    Student,
    StudentDiscipline,
    User,
    UserRole,
)
from app.schemas import (
    AnonymizedStudentProfile,
    AnonymizedStudentResult,
    ContactRequestCreate,
    ContactRequestResponse,
    DisciplineGroupResponse,
    DisciplineResponse,
    EmployerProfileResponse,
    EmployerProfileUpdate,
    EmployerSearchRequest,
    SkillMatchResponse,
)
from app.valuation import DisciplineWithGrade, evaluate_student

router = APIRouter(prefix="/api/v1/employer", tags=["employer"])


# --- Employer profile ---


@router.get("/profile", response_model=EmployerProfileResponse)
async def get_employer_profile(
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """Получить свой профиль работодателя."""
    result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile not found")
    return profile


@router.put("/profile", response_model=EmployerProfileResponse)
async def update_employer_profile(
    data: EmployerProfileUpdate,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """Обновить профиль работодателя."""
    result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile not found")

    if data.company_name is not None:
        profile.company_name = data.company_name
    if data.position is not None:
        profile.position = data.position
    if data.contact_info is not None:
        profile.contact_info = data.contact_info
    if data.about_company is not None:
        profile.about_company = data.about_company
    if data.website_url is not None:
        profile.website_url = data.website_url
    await db.commit()
    await db.refresh(profile)
    return profile


# --- Student search ---


def _build_disciplines_response(student: Student) -> list[DisciplineResponse]:
    return [
        DisciplineResponse(
            id=sd.discipline.id,
            name=sd.discipline.name,
            grade=sd.grade,
            category=display_discipline_category(sd.discipline.name, sd.discipline.category),
        )
        for sd in student.student_disciplines
    ]


def _build_discipline_groups(disciplines: list[DisciplineResponse]) -> list[DisciplineGroupResponse]:
    groups: dict[str, list[DisciplineResponse]] = {}
    for discipline in disciplines:
        group_name = discipline.category or "Другое"
        groups.setdefault(group_name, []).append(discipline)

    responses: list[DisciplineGroupResponse] = []
    for group_name in ordered_group_names(groups):
        group_disciplines = groups[group_name]
        avg_grade = sum(d.grade for d in group_disciplines) / len(group_disciplines)
        responses.append(
            DisciplineGroupResponse(
                group_name=group_name,
                disciplines=group_disciplines,
                total_count=len(group_disciplines),
                avg_grade=round(avg_grade, 2),
            )
        )
    return responses


@router.post("/search", response_model=list[AnonymizedStudentResult])
async def search_students(
    request: EmployerSearchRequest,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """
    Поиск студентов по названию должности.
    Для каждого студента рассчитывает оценку и сортирует по confidence desc, salary desc.
    Возвращает анонимизированные данные (без ФИО и группы).
    """
    # Get all students with disciplines
    stmt = select(Student).options(
        selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline)
    )
    result = await db.execute(stmt)
    students = result.scalars().all()

    results: list[AnonymizedStudentResult] = []

    for student in students:
        if not student.student_disciplines:
            continue

        disciplines = [
            DisciplineWithGrade(name=sd.discipline.name, grade=sd.grade)
            for sd in student.student_disciplines
        ]

        try:
            valuation = await evaluate_student(
                db,
                disciplines,
                specialty=request.job_title,
                experience=request.experience.value if request.experience else None,
                top_k=request.top_k,
            )
        except Exception:
            continue

        skill_matches = [
            SkillMatchResponse(
                discipline=m.discipline,
                skill_name=m.skill_name,
                similarity=m.similarity,
                avg_salary=m.avg_salary,
                vacancy_count=m.vacancy_count,
                grade=m.grade,
                grade_coeff=m.grade_coeff,
                excluded=m.excluded,
            )
            for m in valuation.skill_matches
        ]

        discipline_responses = _build_disciplines_response(student)
        results.append(AnonymizedStudentResult(
            student_id=student.id,
            photo_url=student.photo_path,
            disciplines=discipline_responses,
            discipline_groups=_build_discipline_groups(discipline_responses),
            estimated_salary=valuation.estimated_salary,
            confidence=valuation.confidence,
            matched_disciplines=valuation.matched_disciplines,
            total_disciplines=valuation.total_disciplines,
            skill_matches=skill_matches,
        ))

    # Sort: confidence desc, then salary desc
    results.sort(key=lambda r: (r.confidence, r.estimated_salary or 0), reverse=True)
    return results


# --- Anonymized student profile ---


@router.get("/students/{student_id}/profile", response_model=AnonymizedStudentProfile)
async def get_anonymized_student_profile(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """
    Анонимизированный профиль студента.
    about_me доступен только если есть accepted запрос на контакт.
    """
    stmt = (
        select(Student)
        .options(selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline))
        .where(Student.id == student_id)
    )
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check contact request status
    cr_result = await db.execute(
        select(ContactRequest).where(
            ContactRequest.employer_id == current_user.id,
            ContactRequest.student_id == student_id,
        )
    )
    contact_req = cr_result.scalar_one_or_none()

    contact_status = contact_req.status.value if contact_req else None
    show_about_me = contact_req and contact_req.status == ContactRequestStatus.accepted

    # Get employer profile for partnership status
    emp_result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    emp_profile = emp_result.scalar_one_or_none()
    partnership = emp_profile.partnership_status.value if emp_profile else None

    discipline_responses = _build_disciplines_response(student)
    return AnonymizedStudentProfile(
        student_id=student.id,
        photo_url=student.photo_path,
        disciplines=discipline_responses,
        discipline_groups=_build_discipline_groups(discipline_responses),
        about_me=student.about_me if show_about_me else None,
        contact_status=contact_status,
        partnership_status=partnership,
        work_ready_date=student.work_ready_date.isoformat() if student.work_ready_date else None,
    )


# --- Contact requests ---


@router.post("/students/{student_id}/request-contact", response_model=ContactRequestCreate)
async def request_contact(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """Отправить запрос на контакт студенту."""
    # Check student exists
    student = await db.execute(select(Student).where(Student.id == student_id))
    if not student.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")

    # Check no existing request
    existing = await db.execute(
        select(ContactRequest).where(
            ContactRequest.employer_id == current_user.id,
            ContactRequest.student_id == student_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Contact request already exists")

    cr = ContactRequest(
        employer_id=current_user.id,
        student_id=student_id,
        status=ContactRequestStatus.pending,
    )
    db.add(cr)
    await db.commit()
    await db.refresh(cr)

    return ContactRequestCreate(
        id=cr.id,
        employer_id=cr.employer_id,
        student_id=cr.student_id,
        status=cr.status.value,
        created_at=cr.created_at.isoformat(),
    )


@router.get("/contact-requests", response_model=list[ContactRequestResponse])
async def get_employer_contact_requests(
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """Получить свои запросы на контакт (для работодателя)."""
    result = await db.execute(
        select(ContactRequest).where(ContactRequest.employer_id == current_user.id)
    )
    requests = result.scalars().all()

    return [
        ContactRequestResponse(
            id=r.id,
            employer_id=r.employer_id,
            student_id=r.student_id,
            status=r.status.value,
            created_at=r.created_at.isoformat(),
            responded_at=r.responded_at.isoformat() if r.responded_at else None,
        )
        for r in requests
    ]
