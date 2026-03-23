"""
F1: Baseline формула (текущая).

weight = similarity × log1p(vacancy_count) × grade_coeff

Это текущая формула из valuation.py.
"""

import math

from app.formulas.base import BaseFormula


class BaselineFormula(BaseFormula):
    """
    Базовая формула с логарифмическим сглаживанием.
    
    Логарифм предотвращает чрезмерное влияние очень популярных навыков.
    """
    
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """weight = similarity × log1p(vacancy_count) × grade_coeff"""
        return similarity * math.log1p(vacancy_count) * grade_coeff
    
    def get_name(self) -> str:
        return "baseline"
    
    def get_description(self) -> str:
        return "Базовая формула: similarity × log1p(count) × grade"
