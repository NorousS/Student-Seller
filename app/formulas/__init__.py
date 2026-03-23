"""
Модуль формул расчёта веса навыков для оценки студентов.

Каждая формула определяет как рассчитывается вес навыка
на основе similarity, vacancy_count и grade_coeff.
"""

from app.formulas.base import BaseFormula
from app.formulas.f1_baseline import BaselineFormula
from app.formulas.f2_linear import LinearFormula
from app.formulas.f3_quadratic import QuadraticFormula
from app.formulas.f4_exponential import ExponentialFormula
from app.formulas.f5_tfidf import TFIDFFormula
from app.formulas.f6_matrix import MatrixFormula


class FormulaRegistry:
    """
    Реестр формул для получения по имени.
    
    Usage:
        formula = FormulaRegistry.get_formula("baseline")
        weight = formula.calculate_weight(0.9, 100, 1.0)
    """
    
    _formulas: dict[str, type[BaseFormula]] = {
        "baseline": BaselineFormula,
        "linear": LinearFormula,
        "quadratic": QuadraticFormula,
        "exponential": ExponentialFormula,
        "tfidf": TFIDFFormula,
        "matrix": MatrixFormula,
    }
    
    @classmethod
    def get_formula(cls, name: str, **kwargs) -> BaseFormula:
        """
        Получить экземпляр формулы по имени.
        
        Args:
            name: Имя формулы (baseline, linear, quadratic, exponential, tfidf, matrix)
            **kwargs: Дополнительные параметры для конструктора формулы
            
        Returns:
            Экземпляр формулы
            
        Raises:
            ValueError: Если формула не найдена
        """
        formula_class = cls._formulas.get(name.lower())
        if formula_class is None:
            available = ", ".join(cls._formulas.keys())
            raise ValueError(f"Unknown formula '{name}'. Available: {available}")
        
        return formula_class(**kwargs)
    
    @classmethod
    def list_formulas(cls) -> list[str]:
        """Получить список доступных формул."""
        return list(cls._formulas.keys())
    
    @classmethod
    def get_all_formulas(cls) -> list[BaseFormula]:
        """Получить экземпляры всех формул."""
        return [formula_class() for formula_class in cls._formulas.values()]


__all__ = [
    "BaseFormula",
    "BaselineFormula",
    "LinearFormula",
    "QuadraticFormula",
    "ExponentialFormula",
    "TFIDFFormula",
    "MatrixFormula",
    "FormulaRegistry",
]
