"""
F6: Matrix формула с учётом корреляций между навыками.

weight = similarity × correlation_boost × log1p(vacancy_count) × grade_coeff

correlation_boost = 1 + avg(cosine_similarity с другими найденными навыками)

Усиливает навыки которые семантически связаны с другими навыками студента.
"""

import math
from typing import Optional

import numpy as np

from app.formulas.base import BaseFormula


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Вычислить косинусное сходство двух векторов."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot / (norm_a * norm_b))


class MatrixFormula(BaseFormula):
    """
    Матричная формула с учётом корреляций.
    
    Если студент знает Python и Django, то навык "FastAPI"
    получит boost потому что он семантически близок к обоим.
    
    Это поощряет "кластеры" связанных навыков.
    """
    
    def __init__(
        self,
        skill_embeddings: Optional[dict[str, list[float]]] = None,
        current_skill: Optional[str] = None,
        boost_scale: float = 0.5,
    ):
        """
        Args:
            skill_embeddings: Словарь {skill_name: embedding} всех найденных навыков
            current_skill: Имя текущего навыка для которого считаем вес
            boost_scale: Масштаб буста (0.5 = макс +50% к весу)
        """
        self.skill_embeddings = skill_embeddings or {}
        self.current_skill = current_skill
        self.boost_scale = boost_scale
        self._correlation_cache: dict[str, float] = {}
    
    def set_context(
        self,
        skill_embeddings: dict[str, list[float]],
        current_skill: str,
    ) -> None:
        """Установить контекст для расчёта корреляции."""
        self.skill_embeddings = skill_embeddings
        self.current_skill = current_skill
        self._correlation_cache.clear()
    
    def _calculate_correlation_boost(self) -> float:
        """Вычислить boost на основе корреляции с другими навыками."""
        if not self.skill_embeddings or not self.current_skill:
            return 1.0
        
        if self.current_skill in self._correlation_cache:
            return self._correlation_cache[self.current_skill]
        
        current_emb = self.skill_embeddings.get(self.current_skill)
        if current_emb is None:
            return 1.0
        
        # Считаем среднее сходство с другими навыками
        similarities = []
        for skill_name, emb in self.skill_embeddings.items():
            if skill_name != self.current_skill:
                sim = cosine_similarity(current_emb, emb)
                similarities.append(sim)
        
        if not similarities:
            return 1.0
        
        avg_sim = sum(similarities) / len(similarities)
        boost = 1.0 + (avg_sim * self.boost_scale)
        
        self._correlation_cache[self.current_skill] = boost
        return boost
    
    def calculate_weight(
        self,
        similarity: float,
        vacancy_count: int,
        grade_coeff: float,
    ) -> float:
        """weight = similarity × correlation_boost × log1p(count) × grade"""
        correlation_boost = self._calculate_correlation_boost()
        return similarity * correlation_boost * math.log1p(vacancy_count) * grade_coeff
    
    def get_name(self) -> str:
        return "matrix"
    
    def get_description(self) -> str:
        return "Матричная: similarity × correlation_boost × log1p(count) × grade"
