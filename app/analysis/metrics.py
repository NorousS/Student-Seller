"""
Метрики качества для сравнения формул.

Метрики:
- Stability: насколько стабильна оценка при изменении top_k ±1
- Consistency: насколько похожи оценки для семантически близких студентов
- Coverage: % дисциплин, нашедших релевантные навыки
- Discrimination: способность различать сильных и слабых студентов
"""

import math
import statistics
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.valuation import evaluate_student, DisciplineWithGrade


@dataclass
class FormulaMetrics:
    """Метрики качества формулы."""
    
    formula_name: str
    stability_score: float  # 0..1, выше = стабильнее
    consistency_score: float  # 0..1, выше = консистентнее
    coverage_ratio: float  # 0..1, доля дисциплин с найденными навыками
    discrimination_power: float  # 0..1, способность различать студентов
    avg_confidence: float  # Средняя уверенность оценок
    sample_size: int  # Количество оценок в выборке


async def calculate_stability(
    db: AsyncSession,
    disciplines: list[DisciplineWithGrade],
    specialty: str,
    formula_name: str,
    base_top_k: int = 5,
) -> float:
    """
    Оценивает стабильность формулы при изменении top_k.
    
    Считает, насколько меняется оценка при top_k-1 и top_k+1.
    
    Returns:
        Stability score 0..1 (1 = полностью стабильна)
    """
    results = []
    
    for top_k in [max(1, base_top_k - 1), base_top_k, base_top_k + 1]:
        valuation = await evaluate_student(
            db, disciplines, specialty,
            top_k=top_k, formula_name=formula_name,
        )
        if valuation.estimated_salary:
            results.append(valuation.estimated_salary)
    
    if len(results) < 2:
        return 1.0  # Нет данных для сравнения
    
    # Считаем коэффициент вариации (CV)
    mean = statistics.mean(results)
    if mean == 0:
        return 1.0
    
    std = statistics.stdev(results) if len(results) > 1 else 0
    cv = std / mean
    
    # Преобразуем CV в stability score (0..1)
    # CV = 0 → stability = 1
    # CV = 0.2 (20% вариация) → stability ≈ 0.5
    stability = math.exp(-5 * cv)
    
    return round(min(1.0, max(0.0, stability)), 4)


async def calculate_consistency(
    db: AsyncSession,
    student_groups: list[list[DisciplineWithGrade]],
    specialty: str,
    formula_name: str,
    top_k: int = 5,
) -> float:
    """
    Оценивает консистентность: похожие студенты должны получать похожие оценки.
    
    Args:
        student_groups: Группы семантически близких студентов
        
    Returns:
        Consistency score 0..1 (1 = идеально консистентна)
    """
    if len(student_groups) < 2:
        return 1.0
    
    group_variances = []
    
    for group in student_groups:
        salaries = []
        for disciplines in group:
            valuation = await evaluate_student(
                db, disciplines, specialty,
                top_k=top_k, formula_name=formula_name,
            )
            if valuation.estimated_salary:
                salaries.append(valuation.estimated_salary)
        
        if len(salaries) >= 2:
            mean = statistics.mean(salaries)
            if mean > 0:
                cv = statistics.stdev(salaries) / mean
                group_variances.append(cv)
    
    if not group_variances:
        return 1.0
    
    avg_cv = statistics.mean(group_variances)
    consistency = math.exp(-3 * avg_cv)
    
    return round(min(1.0, max(0.0, consistency)), 4)


async def calculate_coverage(
    db: AsyncSession,
    disciplines: list[DisciplineWithGrade],
    specialty: str,
    formula_name: str,
    top_k: int = 5,
) -> float:
    """
    Считает долю дисциплин, для которых нашлись релевантные навыки.
    
    Returns:
        Coverage ratio 0..1
    """
    valuation = await evaluate_student(
        db, disciplines, specialty,
        top_k=top_k, formula_name=formula_name,
    )
    
    if valuation.total_disciplines == 0:
        return 0.0
    
    return round(valuation.matched_disciplines / valuation.total_disciplines, 4)


async def calculate_discrimination(
    db: AsyncSession,
    weak_students: list[list[DisciplineWithGrade]],
    strong_students: list[list[DisciplineWithGrade]],
    specialty: str,
    formula_name: str,
    top_k: int = 5,
) -> float:
    """
    Оценивает способность формулы различать слабых и сильных студентов.
    
    Args:
        weak_students: Студенты с низкими оценками (3-ки)
        strong_students: Студенты с высокими оценками (5-ки)
        
    Returns:
        Discrimination power 0..1 (1 = идеально различает)
    """
    weak_salaries = []
    strong_salaries = []
    
    for disciplines in weak_students:
        valuation = await evaluate_student(
            db, disciplines, specialty,
            top_k=top_k, formula_name=formula_name,
        )
        if valuation.estimated_salary:
            weak_salaries.append(valuation.estimated_salary)
    
    for disciplines in strong_students:
        valuation = await evaluate_student(
            db, disciplines, specialty,
            top_k=top_k, formula_name=formula_name,
        )
        if valuation.estimated_salary:
            strong_salaries.append(valuation.estimated_salary)
    
    if not weak_salaries or not strong_salaries:
        return 0.5  # Нет данных
    
    weak_mean = statistics.mean(weak_salaries)
    strong_mean = statistics.mean(strong_salaries)
    
    if weak_mean == 0 and strong_mean == 0:
        return 0.5
    
    # Cohen's d — мера размера эффекта
    pooled_std = math.sqrt(
        (statistics.variance(weak_salaries) + statistics.variance(strong_salaries)) / 2
    ) if len(weak_salaries) > 1 and len(strong_salaries) > 1 else 1.0
    
    if pooled_std == 0:
        pooled_std = 1.0
    
    cohens_d = (strong_mean - weak_mean) / pooled_std
    
    # Преобразуем Cohen's d в 0..1
    # d = 0.8 считается большим эффектом → discrimination ≈ 0.8
    discrimination = 1 - math.exp(-0.5 * abs(cohens_d))
    
    # Если strong < weak, это плохо — инвертируем
    if strong_mean < weak_mean:
        discrimination = 1 - discrimination
    
    return round(min(1.0, max(0.0, discrimination)), 4)


async def evaluate_formula_quality(
    db: AsyncSession,
    formula_name: str,
    test_students: list[list[DisciplineWithGrade]],
    specialty: str,
    weak_students: Optional[list[list[DisciplineWithGrade]]] = None,
    strong_students: Optional[list[list[DisciplineWithGrade]]] = None,
    top_k: int = 5,
) -> FormulaMetrics:
    """
    Комплексная оценка качества формулы.
    
    Args:
        test_students: Список наборов дисциплин для тестирования
        weak_students: Студенты с низкими оценками (для discrimination)
        strong_students: Студенты с высокими оценками (для discrimination)
    """
    # Stability — усредняем по всем студентам
    stabilities = []
    coverages = []
    confidences = []
    
    for disciplines in test_students:
        stability = await calculate_stability(
            db, disciplines, specialty, formula_name, top_k
        )
        stabilities.append(stability)
        
        coverage = await calculate_coverage(
            db, disciplines, specialty, formula_name, top_k
        )
        coverages.append(coverage)
        
        valuation = await evaluate_student(
            db, disciplines, specialty,
            top_k=top_k, formula_name=formula_name,
        )
        confidences.append(valuation.confidence)
    
    avg_stability = statistics.mean(stabilities) if stabilities else 0.0
    avg_coverage = statistics.mean(coverages) if coverages else 0.0
    avg_confidence = statistics.mean(confidences) if confidences else 0.0
    
    # Consistency — нужны группы похожих студентов
    # Если не предоставлены, используем все как одну группу
    consistency = await calculate_consistency(
        db, [test_students], specialty, formula_name, top_k
    )
    
    # Discrimination
    discrimination = 0.5
    if weak_students and strong_students:
        discrimination = await calculate_discrimination(
            db, weak_students, strong_students, specialty, formula_name, top_k
        )
    
    return FormulaMetrics(
        formula_name=formula_name,
        stability_score=round(avg_stability, 4),
        consistency_score=round(consistency, 4),
        coverage_ratio=round(avg_coverage, 4),
        discrimination_power=round(discrimination, 4),
        avg_confidence=round(avg_confidence, 4),
        sample_size=len(test_students),
    )
