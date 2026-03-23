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
from app.analysis import (
    FormulaMetrics,
    evaluate_formula_quality,
    generate_test_students,
    get_all_discipline_sets,
    get_weak_students,
    get_strong_students,
)

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


class FormulaMetricsResponse(BaseModel):
    """Метрики качества формулы."""
    formula_name: str
    stability_score: float = Field(..., description="Стабильность при изменении top_k")
    consistency_score: float = Field(..., description="Консистентность для похожих студентов")
    coverage_ratio: float = Field(..., description="Доля дисциплин с найденными навыками")
    discrimination_power: float = Field(..., description="Способность различать студентов")
    avg_confidence: float = Field(..., description="Средняя уверенность оценок")
    sample_size: int = Field(..., description="Количество оценок в выборке")


class FormulaQualityComparisonResponse(BaseModel):
    """Сравнение качества всех формул."""
    specialty: str
    metrics: list[FormulaMetricsResponse]
    best_formula: str
    recommendation: str


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


@router.post("/evaluate-formulas", response_model=FormulaQualityComparisonResponse)
async def evaluate_all_formulas(
    specialty: str = Query(..., min_length=1, description="Специальность для оценки"),
    sample_size: int = Query(default=5, ge=1, le=20, description="Размер выборки на профиль"),
    top_k: int = Query(default=5, ge=1, le=20),
    seed: int = Query(default=42, description="Seed для воспроизводимости"),
    db: AsyncSession = Depends(get_db),
) -> FormulaQualityComparisonResponse:
    """
    Комплексное сравнение качества всех формул на синтетических данных.
    
    Генерирует тестовых студентов разных профилей (backend, data_science, devops, 
    fullstack, theorist) с разной силой (weak, average, strong) и оценивает
    каждую формулу по метрикам:
    
    - **stability_score**: Стабильность при изменении top_k ±1
    - **consistency_score**: Похожие студенты получают похожие оценки
    - **coverage_ratio**: Доля дисциплин с найденными навыками
    - **discrimination_power**: Способность различать слабых и сильных студентов
    - **avg_confidence**: Средняя уверенность оценок
    """
    # Генерируем тестовых студентов
    test_students = generate_test_students(profiles_per_type=sample_size, seed=seed)
    
    all_disciplines = get_all_discipline_sets(test_students)
    weak = get_weak_students(test_students)
    strong = get_strong_students(test_students)
    
    metrics_list = []
    
    for formula_name in FormulaRegistry.list_formulas():
        metrics = await evaluate_formula_quality(
            db=db,
            formula_name=formula_name,
            test_students=all_disciplines,
            specialty=specialty,
            weak_students=weak,
            strong_students=strong,
            top_k=top_k,
        )
        
        metrics_list.append(FormulaMetricsResponse(
            formula_name=metrics.formula_name,
            stability_score=metrics.stability_score,
            consistency_score=metrics.consistency_score,
            coverage_ratio=metrics.coverage_ratio,
            discrimination_power=metrics.discrimination_power,
            avg_confidence=metrics.avg_confidence,
            sample_size=metrics.sample_size,
        ))
    
    # Выбираем лучшую формулу по комбинированному скору
    def combined_score(m: FormulaMetricsResponse) -> float:
        return (
            m.stability_score * 0.2 +
            m.consistency_score * 0.2 +
            m.coverage_ratio * 0.2 +
            m.discrimination_power * 0.3 +
            m.avg_confidence * 0.1
        )
    
    best = max(metrics_list, key=combined_score)
    
    # Генерируем рекомендацию
    if best.discrimination_power > 0.7:
        recommendation = f"Рекомендуется {best.formula_name}: хорошо различает сильных и слабых студентов"
    elif best.stability_score > 0.8:
        recommendation = f"Рекомендуется {best.formula_name}: стабильные оценки"
    else:
        recommendation = f"Рекомендуется {best.formula_name} как лучший компромисс"
    
    return FormulaQualityComparisonResponse(
        specialty=specialty,
        metrics=metrics_list,
        best_formula=best.formula_name,
        recommendation=recommendation,
    )
