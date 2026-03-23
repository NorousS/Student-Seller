"""
Базовый абстрактный класс для всех формул расчёта веса навыка.
"""

from abc import ABC, abstractmethod


class BaseFormula(ABC):
    """
    Базовый класс для всех формул расчёта веса навыка.
    
    Формула определяет как комбинируются:
    - similarity: косинусное сходство дисциплины и навыка (0..1)
    - vacancy_count: количество вакансий с этим навыком
    - grade_coeff: коэффициент оценки студента (0.75, 0.85, 1.0)
    """
    
    @abstractmethod
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """
        Рассчитать вес навыка для итоговой оценки.
        
        Args:
            similarity: Косинусное сходство (0..1)
            vacancy_count: Количество вакансий с навыком
            grade_coeff: Коэффициент оценки (0.75, 0.85, 1.0)
            
        Returns:
            Вес навыка для взвешенного среднего зарплат
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Вернуть уникальное имя формулы."""
        pass
    
    def get_description(self) -> str:
        """Вернуть описание формулы (опционально)."""
        return ""
