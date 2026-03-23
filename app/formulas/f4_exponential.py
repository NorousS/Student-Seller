"""
F4: Exponential формула.

weight = exp(similarity - 0.5) × log1p(vacancy_count) × grade_coeff

Экспоненциально усиливает высокие similarity.
"""

import math

from app.formulas.base import BaseFormula


class ExponentialFormula(BaseFormula):
    """
    Экспоненциальная формула — резко усиливает точные совпадения.
    
    similarity=0.5 даёт множитель 1.0
    similarity=0.8 даёт множитель 1.35
    similarity=0.95 даёт множитель 1.57
    """
    
    def __init__(self, center: float = 0.5):
        """
        Args:
            center: Значение similarity при котором exp даёт 1.0
        """
        self.center = center
    
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """weight = exp(similarity - center) × log1p(vacancy_count) × grade_coeff"""
        return math.exp(similarity - self.center) * math.log1p(vacancy_count) * grade_coeff
    
    def get_name(self) -> str:
        return "exponential"
    
    def get_description(self) -> str:
        return f"Экспоненциальная: exp(similarity-{self.center}) × log1p(count) × grade"
