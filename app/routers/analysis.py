"""
Роутер для сравнения формул и группировки навыков.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_db
from app.models import Student, UserRole
from app.valuation import evaluate_student, DisciplineWithGrade
from app.formulas import FormulaRegistry
from app.grouping import SkillClusterer, DisciplineClusterer

router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["analysis"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


# === Schemas ===

class FormulaInfo(BaseModel):
    """Информация о формуле."""
    name: str
    description: str


class FormulaComparisonResult(BaseModel):
    """Результат оценки одной формулой."""
    formula_name: str
    estimated_salary: float | None
    confidence: float


class FormulaComparisonResponse(BaseModel):
    """Сравнение результатов всех формул."""
    student_id: int
    student_name: str
    specialty: str
    results: list[FormulaComparisonResult]


class SkillClusterResponse(BaseModel):
    """Кластер навыков."""
    category: str
    skills: list[str]
    confidence: float


class SkillClusteringResponse(BaseModel):
    """Результат кластеризации навыков."""
    student_id: int
    student_name: str
    clusters: list[SkillClusterResponse]
    uncategorized: list[str]


class DisciplineClusterResponse(BaseModel):
    """Кластер дисциплин."""
    cluster_name: str
    disciplines: list[str]


class DisciplineClusteringResponse(BaseModel):
    """Результат кластеризации дисциплин."""
    student_id: int
    student_name: str
    clusters: list[DisciplineClusterResponse]


# === Endpoints ===

@router.get("/formulas", response_model=list[FormulaInfo])
async def list_formulas() -> list[FormulaInfo]:
    """Список доступных формул."""
    formulas = FormulaRegistry.get_all_formulas()
    return [
        FormulaInfo(name=f.get_name(), description=f.get_description())
        for f in formulas
    ]


@router.post("/compare/{student_id}", response_model=FormulaComparisonResponse)
async def compare_formulas(
    student_id: int,
    specialty: str = Query(..., min_length=1, description="Специальность"),
    experience: str | None = Query(None, description="Опыт работы"),
    top_k: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> FormulaComparisonResponse:
    """
    Сравнивает результаты оценки студента всеми формулами.
    
    Возвращает estimated_salary и confidence для каждой формулы.
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
    
    results = []
    for formula_name in FormulaRegistry.list_formulas():
        valuation = await evaluate_student(
            db, disciplines, specialty=specialty,
            experience=experience, top_k=top_k,
            formula_name=formula_name,
        )
        results.append(FormulaComparisonResult(
            formula_name=formula_name,
            estimated_salary=valuation.estimated_salary,
            confidence=valuation.confidence,
        ))
    
    return FormulaComparisonResponse(
        student_id=student.id,
        student_name=student.full_name,
        specialty=specialty,
        results=results,
    )


@router.get("/cluster-skills/{student_id}", response_model=SkillClusteringResponse)
async def cluster_student_skills(
    student_id: int,
    top_k: int = Query(default=5, ge=1, le=20, description="Навыков на дисциплину"),
    db: AsyncSession = Depends(get_db),
) -> SkillClusteringResponse:
    """
    Группирует навыки студента по категориям.
    
    Для каждой дисциплины находит релевантные навыки hh.ru,
    затем группирует их по семантическим категориям.
    """
    from app.vector_store import vector_store
    
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    
    # Собираем все навыки из дисциплин
    all_skills: set[str] = set()
    for sd in student.student_disciplines:
        similar = await vector_store.search_similar_skills(
            text=sd.discipline.name,
            top_k=top_k,
        )
        for s in similar:
            all_skills.add(s["name"])
    
    if not all_skills:
        return SkillClusteringResponse(
            student_id=student.id,
            student_name=student.full_name,
            clusters=[],
            uncategorized=[],
        )
    
    # Кластеризуем
    clusterer = SkillClusterer()
    cluster_result = await clusterer.cluster(list(all_skills))
    
    clusters = [
        SkillClusterResponse(
            category=c.category,
            skills=c.skills,
            confidence=round(c.confidence, 4),
        )
        for c in cluster_result.clusters
    ]
    
    return SkillClusteringResponse(
        student_id=student.id,
        student_name=student.full_name,
        clusters=clusters,
        uncategorized=cluster_result.uncategorized,
    )


@router.get("/cluster-disciplines/{student_id}", response_model=DisciplineClusteringResponse)
async def cluster_student_disciplines(
    student_id: int,
    n_clusters: int | None = Query(None, ge=2, le=10, description="Количество кластеров (авто если не указано)"),
    db: AsyncSession = Depends(get_db),
) -> DisciplineClusteringResponse:
    """
    Группирует дисциплины студента по семантическим категориям.
    """
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    
    discipline_names = [sd.discipline.name for sd in student.student_disciplines]
    if not discipline_names:
        return DisciplineClusteringResponse(
            student_id=student.id,
            student_name=student.full_name,
            clusters=[],
        )
    
    clusterer = DisciplineClusterer()
    cluster_result = await clusterer.cluster(discipline_names, n_clusters=n_clusters)
    
    clusters = [
        DisciplineClusterResponse(
            cluster_name=c.cluster_name,
            disciplines=c.disciplines,
        )
        for c in cluster_result.clusters
    ]
    
    return DisciplineClusteringResponse(
        student_id=student.id,
        student_name=student.full_name,
        clusters=clusters,
    )
