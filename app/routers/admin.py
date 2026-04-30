"""
Admin API endpoints для управления системой.

Предоставляет административные операции, такие как
переиндексация навыков в Qdrant с диагностикой.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.discipline_groups import infer_discipline_group_semantic, reload_centroids
from app.embedding_diagnostics import detect_anomalies, DiagnosticsResult
from app.embeddings import embedding_service
from app.models import Discipline, Student, StudentDiscipline, Tag, User, UserRole
from app.schemas import AdminStudentUpdate, StudentResponse, DisciplineResponse
from app.valuation_cache import refresh_all_student_valuations
from app.vector_store import vector_store, HH_SKILLS_COLLECTION
from qdrant_client.models import PointStruct


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# --- Схемы данных ---


class ReindexResponse(BaseModel):
    """
    Ответ на запрос переиндексации навыков.
    
    Attributes:
        total_skills: Общее количество навыков в базе данных
        reindexed_count: Количество проиндексированных навыков
        diagnostics: Результаты диагностики аномалий (если выполнена)
    """
    total_skills: int = Field(..., description="Общее количество навыков в БД")
    reindexed_count: int = Field(..., description="Количество проиндексированных навыков")
    diagnostics: DiagnosticsResult | None = Field(
        default=None,
        description="Результаты диагностики аномалий similarity"
    )
    diagnostics_error: str | None = Field(
        default=None,
        description="Текст ошибки диагностики, если проверка не выполнена",
    )
    disciplines_recategorized: int = 0
    valuations_refreshed: int = 0


class RefreshValuationsResponse(BaseModel):
    refreshed_count: int


def _build_student_response(student: Student) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        full_name=student.full_name,
        group_name=student.group_name,
        disciplines=[
            DisciplineResponse(
                id=sd.discipline.id,
                name=sd.discipline.name,
                grade=sd.grade,
                category=sd.discipline.category,
            )
            for sd in student.student_disciplines
        ],
    )


# --- Эндпоинты ---


@router.post(
    "/reindex-skills",
    response_model=ReindexResponse,
    summary="Полная переиндексация навыков",
    description=(
        "Выполняет полную переиндексацию навыков из PostgreSQL в Qdrant. "
        "Перегенерирует эмбеддинги для всех навыков и обновляет точки в коллекции `hh_skills`. "
        "После переиндексации запускает диагностику аномалий similarity. "
        "**Требует роли admin.**"
    ),
)
async def reindex_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReindexResponse:
    """
    Полная переиндексация навыков в Qdrant с диагностикой.
    
    Этапы выполнения:
    1. Получение всех навыков из таблицы Tag
    2. Генерация эмбеддингов для всех навыков
    3. Обновление точек в Qdrant (upsert для дедупликации)
    4. Запуск диагностики аномалий similarity
    
    Args:
        current_user: Текущий аутентифицированный пользователь
        db: Сессия базы данных
        
    Returns:
        ReindexResponse с результатами переиндексации и диагностики
        
    Raises:
        HTTPException 403: Если пользователь не является администратором
        HTTPException 503: Если Ollama или Qdrant недоступны
    """
    # Проверка прав доступа
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль admin.",
        )
    
    # Получаем все навыки из PostgreSQL
    result = await db.execute(select(Tag))
    tags = result.scalars().all()
    
    if not tags:
        # Если навыков нет — возвращаем пустой результат
        return ReindexResponse(
            total_skills=0,
            reindexed_count=0,
            diagnostics=None,
        )
    
    skill_names = [tag.name for tag in tags]
    total_skills = len(skill_names)
    
    try:
        # Генерируем эмбеддинги для всех навыков
        embeddings = await embedding_service.get_embeddings_batch(skill_names)
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Сервис эмбеддингов (Ollama) недоступен: {str(e)}",
        ) from e
    
    try:
        # Создаём точки для Qdrant
        points = [
            PointStruct(
                id=vector_store._skill_id(skill_name),
                vector=embedding,
                payload={"name": skill_name},
            )
            for skill_name, embedding in zip(skill_names, embeddings)
        ]
        
        # Выполняем upsert (создание или обновление точек)
        await vector_store.client.upsert(
            collection_name=HH_SKILLS_COLLECTION,
            points=points,
        )
        
        reindexed_count = len(points)
        
    except (httpx.HTTPError, ConnectionError, TimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ошибка при индексации в Qdrant: {str(e)}",
        ) from e
    
    # Запускаем диагностику аномалий
    diagnostics_result: DiagnosticsResult | None = None
    diagnostics_error: str | None = None
    
    try:
        # Ограничиваем количество терминов для диагностики (max 100)
        # Если навыков больше, берём первые 100
        terms_for_diagnostics = skill_names[:100]
        
        diagnostics_result = await detect_anomalies(
            terms=terms_for_diagnostics,
            threshold=0.99,
        )
        
    except ValueError as e:
        diagnostics_error = f"Диагностика пропущена: {str(e)}"
    except httpx.HTTPError as e:
        diagnostics_error = f"Диагностика недоступна: {str(e)}"

    disciplines_recategorized = 0
    valuations_refreshed = 0
    try:
        await reload_centroids()
        discipline_result = await db.execute(select(Discipline))
        disciplines = discipline_result.scalars().all()
        for discipline in disciplines:
            discipline.category = await infer_discipline_group_semantic(discipline.name)
        disciplines_recategorized = len(disciplines)
        await db.flush()
    except Exception as e:
        diagnostics_error = f"{diagnostics_error or ''} Категоризация пропущена: {str(e)}".strip()

    valuations_refreshed = await refresh_all_student_valuations(db)
    
    return ReindexResponse(
        total_skills=total_skills,
        reindexed_count=reindexed_count,
        diagnostics=diagnostics_result,
        diagnostics_error=diagnostics_error,
        disciplines_recategorized=disciplines_recategorized,
        valuations_refreshed=valuations_refreshed,
    )


@router.patch("/students/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    data: AdminStudentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentResponse:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен. Требуется роль admin.")

    stmt = (
        select(Student)
        .options(selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline))
        .where(Student.id == student_id)
    )
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if data.full_name is not None:
        student.full_name = data.full_name
    if "group_name" in data.model_fields_set:
        student.group_name = data.group_name

    await db.flush()
    await db.refresh(student)
    result = await db.execute(stmt)
    return _build_student_response(result.scalar_one())


@router.post("/refresh-valuations", response_model=RefreshValuationsResponse)
async def refresh_valuations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefreshValuationsResponse:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен. Требуется роль admin.")
    refreshed = await refresh_all_student_valuations(db)
    return RefreshValuationsResponse(refreshed_count=refreshed)
