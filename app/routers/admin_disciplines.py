"""
Роутер администрирования дисциплин.
Admin-only эндпоинт для категоризации дисциплин через LLM-эмбеддинги.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.categorization import categorize_disciplines
from app.database import get_db
from app.models import Discipline, UserRole

router = APIRouter(prefix="/api/v1/admin/disciplines", tags=["admin-disciplines"])


class CategorizeRequest(BaseModel):
    """Запрос на категоризацию дисциплин."""
    discipline_ids: list[int] | None = None


class CategorizeResponse(BaseModel):
    """Ответ с результатами категоризации."""
    updated_count: int
    mapping: dict[str, str]


@router.post(
    "/categorize",
    response_model=CategorizeResponse,
    dependencies=[Depends(require_role(UserRole.admin))],
)
async def categorize_disciplines_endpoint(
    body: CategorizeRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Категоризировать дисциплины через эмбеддинги Ollama.
    Если discipline_ids не указаны — категоризируются все дисциплины без категории.
    """
    data = body or CategorizeRequest()

    if data.discipline_ids:
        query = select(Discipline).where(Discipline.id.in_(data.discipline_ids))
    else:
        query = select(Discipline).where(Discipline.category.is_(None))

    result = await db.execute(query)
    disciplines = list(result.scalars().all())

    if not disciplines:
        return CategorizeResponse(updated_count=0, mapping={})

    names = [d.name for d in disciplines]
    mapping = await categorize_disciplines(names)

    for disc in disciplines:
        disc.category = mapping.get(disc.name)

    await db.flush()

    return CategorizeResponse(updated_count=len(disciplines), mapping=mapping)
