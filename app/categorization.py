"""
Сервис категоризации дисциплин через эмбеддинги Ollama.
Сопоставляет дисциплину с ближайшим блоком компетенций по косинусному сходству.
"""

import math
import logging

from app.embeddings import embedding_service

logger = logging.getLogger(__name__)

# Предопределённые категории (блоки компетенций)
DEFAULT_CATEGORIES: list[str] = [
    "Программирование",
    "Базы данных",
    "Математика",
    "Машинное обучение",
    "Сети и безопасность",
    "Проектирование ПО",
    "Общие компетенции",
]

FALLBACK_CATEGORY = "Общие компетенции"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Вычисляет косинусное сходство двух векторов."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def categorize_disciplines(
    discipline_names: list[str],
    categories: list[str] | None = None,
) -> dict[str, str]:
    """
    Категоризирует дисциплины по блокам компетенций через косинусное сходство эмбеддингов.

    Args:
        discipline_names: Список названий дисциплин
        categories: Список категорий (по умолчанию DEFAULT_CATEGORIES)

    Returns:
        Словарь {название_дисциплины: категория}
    """
    if not discipline_names:
        return {}

    cats = categories or DEFAULT_CATEGORIES

    try:
        # Получаем эмбеддинги категорий
        category_embeddings = await embedding_service.get_embeddings_batch(cats)
        # Получаем эмбеддинги дисциплин
        discipline_embeddings = await embedding_service.get_embeddings_batch(discipline_names)
    except Exception as e:
        logger.warning("Ollama недоступен, fallback на '%s': %s", FALLBACK_CATEGORY, e)
        return {name: FALLBACK_CATEGORY for name in discipline_names}

    result: dict[str, str] = {}
    for name, d_emb in zip(discipline_names, discipline_embeddings):
        best_cat = FALLBACK_CATEGORY
        best_sim = -1.0
        for cat, c_emb in zip(cats, category_embeddings):
            sim = _cosine_similarity(d_emb, c_emb)
            if sim > best_sim:
                best_sim = sim
                best_cat = cat
        result[name] = best_cat

    return result
