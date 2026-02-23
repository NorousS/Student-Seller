"""
Модуль диагностики аномалий similarity в эмбеддингах.

Обнаруживает подозрительно высокие значения косинусного сходства
между различными терминами для выявления потенциальных проблем
с качеством векторных представлений.
"""

import math
from collections.abc import Sequence
from itertools import combinations

from pydantic import BaseModel, Field

from app.embeddings import embedding_service


# --- Константы ---

# Максимальное количество входных терминов для предотвращения перегрузки
MAX_INPUT_TERMS = 100

# Порог similarity для считывания аномалией (>=0.99)
ANOMALY_THRESHOLD = 0.99

# Порог для нормализации текста (считаем идентичными)
NORMALIZATION_SIMILARITY = 1.0


# --- Схемы данных ---


class SimilarityAnomaly(BaseModel):
    """
    Пара терминов с подозрительно высоким similarity.
    
    Attributes:
        term_a: Первый термин
        term_b: Второй термин
        similarity: Косинусное сходство (0..1)
        reason: Описание причины аномалии
    """
    term_a: str = Field(..., description="Первый термин")
    term_b: str = Field(..., description="Второй термин")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Косинусное сходство")
    reason: str = Field(..., description="Причина аномалии")


class DiagnosticsResult(BaseModel):
    """
    Результат диагностики аномалий similarity.
    
    Attributes:
        total_terms: Общее количество проверенных терминов
        total_pairs: Количество проверенных пар
        anomalies: Список обнаруженных аномалий
        max_similarity: Максимальное найденное similarity
        threshold_used: Использованный порог для аномалий
    """
    total_terms: int = Field(..., description="Количество проверенных терминов")
    total_pairs: int = Field(..., description="Количество проверенных пар")
    anomalies: list[SimilarityAnomaly] = Field(
        default_factory=list,
        description="Список обнаруженных аномалий"
    )
    max_similarity: float = Field(..., description="Максимальное найденное similarity")
    threshold_used: float = Field(..., description="Использованный порог аномалий")


class TermEmbedding:
    """Внутренняя структура для хранения термина и его эмбеддинга."""
    def __init__(self, term: str, embedding: Sequence[float]) -> None:
        self.term = term
        self.embedding = embedding


# --- Утилиты ---


def _normalize_term(term: str) -> str:
    """
    Нормализует термин для сравнения.
    
    Args:
        term: Исходный термин
        
    Returns:
        Нормализованная строка (lower, stripped)
    """
    return term.strip().lower()


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """
    Вычисляет косинусное сходство между двумя векторами.
    
    Args:
        vec_a: Первый вектор
        vec_b: Второй вектор
        
    Returns:
        Косинусное сходство (0..1)
    """
    if len(vec_a) != len(vec_b):
        raise ValueError("Векторы должны иметь одинаковую размерность")
    
    # Вычисляем скалярное произведение
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    
    # Вычисляем нормы векторов
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    # Защита от деления на ноль
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    
    # Косинус угла между векторами
    similarity = dot_product / (norm_a * norm_b)
    
    # Ограничиваем диапазон [0, 1] из-за возможных погрешностей вычислений
    return max(0.0, min(1.0, similarity))


# --- Основной функционал ---


async def detect_anomalies(
    terms: list[str],
    threshold: float = ANOMALY_THRESHOLD,
    max_terms: int = MAX_INPUT_TERMS,
) -> DiagnosticsResult:
    """
    Обнаруживает аномалии similarity среди списка терминов.
    
    Генерирует эмбеддинги для всех терминов, вычисляет попарное
    косинусное сходство и выявляет пары с подозрительно высоким
    значением (по умолчанию >= 0.99).
    
    Args:
        terms: Список терминов для проверки
        threshold: Порог similarity для считывания аномалией (default: 0.99)
        max_terms: Максимальное количество входных терминов (default: 100)
        
    Returns:
        DiagnosticsResult с обнаруженными аномалиями
        
    Raises:
        ValueError: Если входной список пуст или превышает max_terms
    """
    # Валидация входных данных
    if not terms:
        raise ValueError("Список терминов не может быть пустым")
    
    if len(terms) > max_terms:
        raise ValueError(
            f"Количество терминов ({len(terms)}) превышает лимит ({max_terms})"
        )
    
    # Дедупликация и нормализация терминов
    unique_terms = list({_normalize_term(t): t for t in terms}.values())
    
    if not unique_terms:
        raise ValueError("После нормализации не осталось уникальных терминов")
    
    # Генерация эмбеддингов
    embeddings_raw = await embedding_service.get_embeddings_batch(unique_terms)
    
    # Создаём объекты с терминами и эмбеддингами
    term_embeddings: list[TermEmbedding] = [
        TermEmbedding(term=term, embedding=emb)
        for term, emb in zip(unique_terms, embeddings_raw)
    ]
    
    # Вычисляем попарные similarity
    anomalies: list[SimilarityAnomaly] = []
    max_similarity = 0.0
    
    # Используем combinations для избежания дублирования пар
    for (te_a, te_b) in combinations(term_embeddings, 2):
        similarity = _cosine_similarity(te_a.embedding, te_b.embedding)
        
        # Обновляем максимальное значение
        max_similarity = max(max_similarity, similarity)
        
        # Проверяем на аномалию
        if similarity >= threshold:
            # Исключаем пары с идентичными после нормализации терминами
            norm_a = _normalize_term(te_a.term)
            norm_b = _normalize_term(te_b.term)
            
            if norm_a == norm_b:
                # Это нормально — одинаковые термины
                continue
            
            # Формируем причину
            if similarity >= NORMALIZATION_SIMILARITY:
                reason = (
                    f"Идентичные эмбеддинги для разных терминов "
                    f"(similarity={similarity:.4f})"
                )
            else:
                reason = (
                    f"Подозрительно высокое сходство "
                    f"(similarity={similarity:.4f}, порог={threshold:.2f})"
                )
            
            anomalies.append(
                SimilarityAnomaly(
                    term_a=te_a.term,
                    term_b=te_b.term,
                    similarity=similarity,
                    reason=reason,
                )
            )
    
    # Количество проверенных пар
    total_pairs = len(unique_terms) * (len(unique_terms) - 1) // 2
    
    return DiagnosticsResult(
        total_terms=len(unique_terms),
        total_pairs=total_pairs,
        anomalies=anomalies,
        max_similarity=max_similarity,
        threshold_used=threshold,
    )


async def detect_duplicate_embeddings(
    terms: list[str],
    max_terms: int = MAX_INPUT_TERMS,
) -> DiagnosticsResult:
    """
    Специализированная версия detect_anomalies для поиска дубликатов.
    
    Ищет термины с идентичными эмбеддингами (similarity = 1.0),
    что может указывать на проблемы с моделью или данными.
    
    Args:
        terms: Список терминов для проверки
        max_terms: Максимальное количество входных терминов
        
    Returns:
        DiagnosticsResult с найденными дубликатами
    """
    return await detect_anomalies(
        terms=terms,
        threshold=NORMALIZATION_SIMILARITY,
        max_terms=max_terms,
    )
