"""
Роутер лендинга и воронки работодателя.
Публичный API для первого экрана, paywall, и управления приглашениями.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_role, get_current_user
from app.database import get_db
from app.models import (
    ContactRequest,
    ContactRequestStatus,
    EmployerProfile,
    FunnelEvent,
    FunnelEventType,
    PartnershipStatus,
    Student,
    StudentDiscipline,
    User,
    UserRole,
)
from app.schemas import (
    ContactRequestCreate,
    PaywallOption,
    TopStudentCard,
)

router = APIRouter(prefix="/api/v1/landing", tags=["landing"])


async def _log_funnel_event(
    db: AsyncSession,
    event_type: FunnelEventType,
    actor_id: int | None = None,
    student_id: int | None = None,
    employer_id: int | None = None,
    payload: dict | None = None,
):
    """Логирование события воронки. Ошибка записи не прерывает основной сценарий."""
    try:
        event = FunnelEvent(
            event_type=event_type,
            actor_id=actor_id,
            student_id=student_id,
            employer_id=employer_id,
            payload_json=json.dumps(payload) if payload else None,
        )
        db.add(event)
        await db.flush()
    except Exception as e:
        print(f"Funnel event logging error: {e}")


@router.get("/top-students", response_model=list[TopStudentCard])
async def get_top_students(
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает до 10 лучших студентов для первого экрана лендинга.
    Анонимизированные данные без контактов.
    Сортировка: сначала студенты с известной estimated_salary (desc), затем по скору.
    """
    # Get students with most disciplines as proxy for "best" profiles
    stmt = (
        select(Student)
        .options(selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline))
        .limit(40)  # Get more than needed, then sort
    )
    result = await db.execute(stmt)
    students = result.scalars().all()

    # Sort: known salary first (desc), then by grade*discipline_count
    def sort_key(s: Student):
        if not s.student_disciplines:
            return (1, 0, 0)
        avg_grade = sum(sd.grade for sd in s.student_disciplines) / len(s.student_disciplines)
        sc = avg_grade * len(s.student_disciplines)
        # (has_no_salary, -salary_if_any, -score)
        has_no_salary = 0 if s.estimated_salary else 1
        salary = s.estimated_salary or 0
        return (has_no_salary, -salary, -sc)

    students_sorted = sorted(students, key=sort_key)[:10]

    cards = []
    for student in students_sorted:
        if not student.student_disciplines:
            continue
        # Build competency summary from discipline names
        top_disciplines = sorted(student.student_disciplines, key=lambda sd: sd.grade, reverse=True)[:3]
        summary_parts = [sd.discipline.name for sd in top_disciplines]
        summary = ", ".join(summary_parts)

        cards.append(TopStudentCard(
            student_id=student.id,
            photo_url=student.photo_path,
            estimated_salary=student.estimated_salary,
            competency_summary=summary,
        ))

    return cards


@router.post("/invite/{student_id}")
async def invite_student(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """
    Пригласить студента на собеседование.
    Для партнеров — создает запрос.
    Для непартнеров — возвращает paywall_required.
    """
    # Get employer profile
    emp_result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    )
    emp_profile = emp_result.scalar_one_or_none()
    if not emp_profile:
        raise HTTPException(status_code=404, detail="Employer profile not found")

    # Log click_invite event
    await _log_funnel_event(
        db, FunnelEventType.click_invite,
        actor_id=current_user.id, student_id=student_id, employer_id=emp_profile.id,
    )

    # Check student exists
    student = await db.execute(select(Student).where(Student.id == student_id))
    if not student.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")

    # Check partnership status
    if emp_profile.partnership_status != PartnershipStatus.partner:
        # Log paywall event
        await _log_funnel_event(
            db, FunnelEventType.paywall_open,
            actor_id=current_user.id, student_id=student_id, employer_id=emp_profile.id,
        )
        await db.commit()
        return {
            "status": "paywall_required",
            "reason": "non_partner",
            "message": "Для приглашения необходимо оплатить доступ или заключить договор с вузом",
        }

    # Partner flow: check no existing request
    existing = await db.execute(
        select(ContactRequest).where(
            ContactRequest.employer_id == current_user.id,
            ContactRequest.student_id == student_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Contact request already exists")

    # Create contact request
    cr = ContactRequest(
        employer_id=current_user.id,
        student_id=student_id,
        status=ContactRequestStatus.pending,
    )
    db.add(cr)

    # Log invite_created
    await _log_funnel_event(
        db, FunnelEventType.invite_created,
        actor_id=current_user.id, student_id=student_id, employer_id=emp_profile.id,
    )

    await db.commit()
    await db.refresh(cr)

    return {
        "status": "invite_created",
        "contact_request": ContactRequestCreate(
            id=cr.id,
            employer_id=cr.employer_id,
            student_id=cr.student_id,
            status=cr.status.value,
            created_at=cr.created_at.isoformat(),
        ).model_dump(),
    }


@router.get("/paywall-options", response_model=list[PaywallOption])
async def get_paywall_options(
    current_user: User = Depends(require_role(UserRole.employer)),
):
    """Возвращает варианты доступа для непартнерского работодателя."""
    return [
        PaywallOption(
            id="pay_access",
            title="Оплатить доступ",
            description="Разовый доступ к профилю и возможность пригласить студента на собеседование",
            action_url="/api/v1/landing/pay",
        ),
        PaywallOption(
            id="university_contract",
            title="Заключить договор с вузом",
            description="Получите полный доступ ко всем профилям студентов как партнер вуза",
            action_url="/api/v1/landing/contract",
        ),
    ]


@router.get("/student/{student_id}/contacts")
async def get_student_contacts(
    student_id: int,
    current_user: User = Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить контакты студента.
    Доступно ТОЛЬКО если есть accepted приглашение от этого работодателя.
    """
    # Check for accepted contact request from this employer
    cr_result = await db.execute(
        select(ContactRequest).where(
            ContactRequest.employer_id == current_user.id,
            ContactRequest.student_id == student_id,
            ContactRequest.status == ContactRequestStatus.accepted,
        )
    )
    contact_request = cr_result.scalar_one_or_none()
    if not contact_request:
        raise HTTPException(
            status_code=403,
            detail="Contacts are only available after student accepts the invitation",
        )

    # Get student with user info
    stmt = select(Student).where(Student.id == student_id)
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get student's user email if linked
    email = None
    if student.user_id:
        user_result = await db.execute(select(User).where(User.id == student.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            email = user.email

    return {
        "student_id": student.id,
        "full_name": student.full_name,
        "email": email,
        "about_me": student.about_me,
    }
