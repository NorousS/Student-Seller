"""Semantic discipline grouping based on embedding centroids."""

import math

from app.embeddings import EmbeddingService

GROUP_SEEDS: dict[str, list[str]] = {
    "PROGRAMMING": ["Python", "Java", "Алгоритмы и структуры данных", "Базы данных", "ООП", "Веб-разработка"],
    "FOREIGN_LANGUAGES": ["Английский язык", "Немецкий язык", "Французский язык", "Иностранный язык"],
    "SOFT_SKILLS": [
        "Soft skills в IT",
        "Управление проектами",
        "Lean менеджмент",
        "Коммуникативные навыки",
        "Лидерство",
    ],
    "EXACT_SCIENCES": [
        "Линейная алгебра",
        "Математический анализ",
        "Математическая статистика",
        "Физика",
        "Дискретная математика",
    ],
}

GROUP_LABELS: dict[str, str] = {
    "PROGRAMMING": "Программирование",
    "FOREIGN_LANGUAGES": "Иностранные языки",
    "SOFT_SKILLS": "Soft skills",
    "EXACT_SCIENCES": "Точные науки",
    "OTHER": "Другое",
}

SIMILARITY_THRESHOLD = 0.5
_LABEL_TO_KEY = {label: key for key, label in GROUP_LABELS.items()}

_centroids: dict[str, list[float]] | None = None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    return [sum(vector[i] for vector in vectors) / len(vectors) for i in range(dim)]


async def _get_centroids() -> dict[str, list[float]]:
    global _centroids
    if _centroids is not None:
        return _centroids

    service = EmbeddingService()
    centroids: dict[str, list[float]] = {}
    for group_key, seeds in GROUP_SEEDS.items():
        embeddings = await service.get_embeddings_batch(seeds)
        centroids[group_key] = _average_vectors(embeddings)

    _centroids = centroids
    return centroids


async def reload_centroids() -> dict[str, list[float]]:
    global _centroids
    _centroids = None
    return await _get_centroids()


async def infer_discipline_group_semantic(name: str) -> str:
    if not name.strip():
        return "OTHER"

    service = EmbeddingService()
    discipline_embedding = await service.get_embedding(name)
    centroids = await _get_centroids()

    best_group = "OTHER"
    best_similarity = -1.0
    for group_key, centroid in centroids.items():
        similarity = _cosine_similarity(discipline_embedding, centroid)
        if similarity > best_similarity:
            best_similarity = similarity
            best_group = group_key

    if best_similarity < SIMILARITY_THRESHOLD:
        return "OTHER"
    return best_group


def normalize_discipline_group_key(group_key_or_label: str | None) -> str:
    if not group_key_or_label:
        return "OTHER"
    if group_key_or_label in GROUP_LABELS:
        return group_key_or_label
    if group_key_or_label in _LABEL_TO_KEY:
        return _LABEL_TO_KEY[group_key_or_label]
    return group_key_or_label


def display_discipline_group_label(group_key: str | None) -> str:
    normalized = normalize_discipline_group_key(group_key)
    return GROUP_LABELS.get(normalized, normalized or GROUP_LABELS["OTHER"])
