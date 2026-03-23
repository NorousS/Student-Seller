"""
F3: Quadratic формула с квадратом similarity.

weight = similarity² × log1p(vacancy_count) × grade_coeff

Усиливает влияние высокорелевантных навыков.
"""

import math

from app.formulas.base import BaseFormula


class QuadraticFormula(BaseFormula):
    """
    Квадратичная формула — усиливает точные совпадения.
    
    Навыки с similarity 0.9 получат вес в 1.8 раза больше чем с similarity 0.67
    (в baseline разница только в 1.34 раза).
    """
    
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """weight = similarity² × log1p(vacancy_count) × grade_coeff"""
        return (similarity ** 2) * math.log1p(vacancy_count) * grade_coeff
    
    def get_name(self) -> str:
        return "quadratic"
    
    def get_description(self) -> str:
        return "Квадратичная: similarity² × log1p(count) × grade"
