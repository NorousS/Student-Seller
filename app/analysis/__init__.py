"""
Модуль статистического анализа формул.
"""

from app.analysis.metrics import (
    FormulaMetrics,
    calculate_stability,
    calculate_consistency,
    calculate_coverage,
    calculate_discrimination,
    evaluate_formula_quality,
)
from app.analysis.test_data import (
    TestStudentProfile,
    generate_test_students,
    get_all_discipline_sets,
    get_weak_students,
    get_strong_students,
    SAMPLE_DISCIPLINES,
)

__all__ = [
    "FormulaMetrics",
    "calculate_stability",
    "calculate_consistency",
    "calculate_coverage",
    "calculate_discrimination",
    "evaluate_formula_quality",
    "TestStudentProfile",
    "generate_test_students",
    "get_all_discipline_sets",
    "get_weak_students",
    "get_strong_students",
    "SAMPLE_DISCIPLINES",
]
