"""
Роутер управления партнерством работодателей.
Admin-only эндпоинты для установки статуса партнерства.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_db
from app.models import (
    EmployerPartnershipAudit,
    EmployerProfile,
    PartnershipStatus,
    User,
    UserRole,
)
from app.schemas import (
    EmployerProfileResponse,
    PartnershipUpdateRequest,
)

router = APIRouter(prefix="/api/v1/admin/partnership", tags=["partnership"])


@router.patch(
    "/employer/{employer_user_id}",
    response_model=EmployerProfileResponse,
    dependencies=[Depends(require_role(UserRole.admin))],
)
async def update_partnership_status(
    employer_user_id: int,
    data: PartnershipUpdateRequest,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Изменить статус партнерства работодателя (admin only)."""
    result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == employer_user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile not found")

    old_status = profile.partnership_status.value
    new_status = data.partnership_status.value

    if old_status == new_status:
        return profile

    # Update status
    profile.partnership_status = PartnershipStatus(new_status)

    # Audit log
    audit = EmployerPartnershipAudit(
        employer_id=profile.id,
        old_status=old_status,
        new_status=new_status,
        changed_by=current_user.id,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get(
    "/audit/{employer_user_id}",
    dependencies=[Depends(require_role(UserRole.admin))],
)
async def get_partnership_audit(
    employer_user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить историю изменений партнерства."""
    result = await db.execute(
        select(EmployerProfile).where(EmployerProfile.user_id == employer_user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Employer profile not found")

    audit_result = await db.execute(
        select(EmployerPartnershipAudit)
        .where(EmployerPartnershipAudit.employer_id == profile.id)
        .order_by(EmployerPartnershipAudit.changed_at.desc())
    )
    audits = audit_result.scalars().all()
    return [
        {
            "id": a.id,
            "old_status": a.old_status,
            "new_status": a.new_status,
            "changed_by": a.changed_by,
            "changed_at": a.changed_at.isoformat(),
        }
        for a in audits
    ]
