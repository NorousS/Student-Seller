"""
F5: TF-IDF подобная формула.

weight = similarity × log(total_vacancies / vacancy_count) × grade_coeff

Редкие навыки получают больший вес (как IDF в информационном поиске).
"""

import math

from app.formulas.base import BaseFormula


class TFIDFFormula(BaseFormula):
    """
    TF-IDF подобная формула — ценит редкие навыки.
    
    Навык который встречается в 10 вакансиях из 10000 получит 
    больший вес чем навык в 1000 вакансий.
    
    Это противоположность baseline — редкие специализированные
    навыки важнее распространённых.
    """
    
    def __init__(self, total_vacancies: int = 10000):
        """
        Args:
            total_vacancies: Общее количество вакансий в базе
        """
        self.total_vacancies = total_vacancies
    
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """weight = similarity × idf(skill) × grade_coeff"""
        if vacancy_count <= 0:
            return 0.0
        
        # IDF: log(N / n) — чем реже навык, тем выше IDF
        idf = math.log(self.total_vacancies / vacancy_count)
        
        # Ограничиваем снизу чтобы очень частые навыки не обнулились
        idf = max(idf, 0.1)
        
        return similarity * idf * grade_coeff
    
    def get_name(self) -> str:
        return "tfidf"
    
    def get_description(self) -> str:
        return f"TF-IDF: similarity × log({self.total_vacancies}/count) × grade"
