"""
F2: Linear формула без логарифма.

weight = similarity × (vacancy_count / max_count) × grade_coeff

Линейная зависимость от частоты навыка.
"""

from app.formulas.base import BaseFormula


class LinearFormula(BaseFormula):
    """
    Линейная формула с нормализацией по максимуму.
    
    Не сглаживает популярные навыки — они получают пропорционально больший вес.
    """
    
    def __init__(self, max_count: int = 1000):
        """
        Args:
            max_count: Максимальное количество вакансий для нормализации
        """
        self.max_count = max_count
    
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """weight = similarity × (count / max_count) × grade_coeff"""
        normalized_count = min(vacancy_count / self.max_count, 1.0)
        return similarity * normalized_count * grade_coeff
    
    def get_name(self) -> str:
        return "linear"
    
    def get_description(self) -> str:
        return f"Линейная: similarity × (count/{self.max_count}) × grade"
