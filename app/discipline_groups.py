<<<<<<< HEAD
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
=======
"""
Группировка учебных дисциплин по смыслу (семантически через эмбеддинги).

Каждой дисциплине присваивается одна из канонических групп на основе
косинусного сходства с предварительно вычисленными центроидами групп.
Если максимальное сходство ниже SIMILARITY_THRESHOLD — группа "Другое".

Для синхронных контекстов (UI-отображение) сохранён keyword-based fallback.
"""

from __future__ import annotations

import asyncio
import math
import re
from collections.abc import Iterable

# ─── Canonical group labels ───────────────────────────────────────────────────

PROGRAMMING = "Программирование"
FOREIGN_LANGUAGES = "Иностранные языки"
SOFT_SKILLS = "Soft skills"
EXACT_SCIENCES = "Точные науки"
OTHER = "Другое"

CANONICAL_DISCIPLINE_GROUPS = [
    PROGRAMMING,
    FOREIGN_LANGUAGES,
    SOFT_SKILLS,
    EXACT_SCIENCES,
]

GROUP_ORDER = [*CANONICAL_DISCIPLINE_GROUPS, OTHER]

# ─── Seed disciplines per group (used to compute centroids) ──────────────────

GROUP_SEEDS: dict[str, list[str]] = {
    PROGRAMMING: [
        "Python", "Java", "JavaScript", "C++", "C#",
        "Алгоритмы и структуры данных", "Базы данных", "ООП",
        "Веб-разработка", "Программирование", "Разработка программного обеспечения",
        "SQL", "Docker", "Компьютерные сети", "Операционные системы",
    ],
    FOREIGN_LANGUAGES: [
        "Английский язык", "Немецкий язык", "Французский язык",
        "Иностранный язык", "Деловой английский", "Профессиональный английский язык",
    ],
    SOFT_SKILLS: [
        "Soft skills в IT", "Управление проектами", "Lean менеджмент",
        "Коммуникативные навыки", "Лидерство", "Командная работа",
        "Предпринимательство", "Тайм-менеджмент", "Бережливое производство",
    ],
    EXACT_SCIENCES: [
        "Линейная алгебра", "Математический анализ", "Математическая статистика",
        "Физика", "Дискретная математика", "Теория вероятностей",
        "Численные методы", "Вычислительная математика",
        "Теория вероятностей и математическая статистика",
    ],
}

# Cosine similarity threshold — below this → OTHER
SIMILARITY_THRESHOLD = 0.50

# ─── Module-level centroid cache ─────────────────────────────────────────────

_centroids: dict[str, list[float]] | None = None
_centroids_lock = asyncio.Lock()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Быстрое косинусное сходство двух векторов."""
>>>>>>> github/main
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


<<<<<<< HEAD
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
=======
async def reload_centroids() -> bool:
    """
    Пересчитывает центроиды групп через эмбеддинги Ollama.
    Вызывается из /admin/reindex-skills и при первом обращении.
    Возвращает True если успешно.
    """
    global _centroids
    # Import here to avoid circular imports at module load time
    from app.embeddings import embedding_service  # noqa: PLC0415

    async with _centroids_lock:
        new_centroids: dict[str, list[float]] = {}
        for group_key, seeds in GROUP_SEEDS.items():
            try:
                embeddings = await embedding_service.get_embeddings_batch(seeds)
                if embeddings:
                    dim = len(embeddings[0])
                    centroid = [
                        sum(e[i] for e in embeddings) / len(embeddings)
                        for i in range(dim)
                    ]
                    new_centroids[group_key] = centroid
            except Exception:
                pass  # keep going; this group will fall back to keywords
        if new_centroids:
            _centroids = new_centroids
            return True
        return False


async def infer_discipline_group_semantic(name: str) -> str:
    """
    Семантически определяет группу дисциплины.
    При недоступных эмбеддингах или сходстве < 50% → keyword fallback → OTHER.
    """
    global _centroids
    if _centroids is None:
        await reload_centroids()

    if not _centroids:
        # Ollama unavailable — use keyword rules
        return infer_discipline_group(name)

    try:
        from app.embeddings import embedding_service  # noqa: PLC0415
        embedding = await embedding_service.get_embedding(name)
    except Exception:
        return infer_discipline_group(name)

    best_group = OTHER
    best_sim = 0.0
    for group_key, centroid in _centroids.items():
        sim = _cosine_similarity(embedding, centroid)
        if sim > best_sim:
            best_sim = sim
            best_group = group_key

    return best_group if best_sim >= SIMILARITY_THRESHOLD else OTHER


# ─── Keyword-based fallback (synchronous, used for display & tests) ───────────

_KEYWORDS: dict[str, tuple[str, ...]] = {
    PROGRAMMING: (
        "python", "java", "javascript", "typescript", "c++", "c#",
        "sql", "docker", "kubernetes", "алгоритм", "структур",
        "программ", "разработ", "ооп", "backend", "frontend",
        "веб", "баз данных", "базы данных",
    ),
    FOREIGN_LANGUAGES: (
        "англий", "немец", "француз", "испан", "китай",
        "иностран", "foreign", "english", "german",
    ),
    SOFT_SKILLS: (
        "soft skill", "софт", "lean", "бережлив", "менеджмент",
        "психолог", "управление", "проект", "коммуникац",
        "команд", "лидер", "предприним",
    ),
    EXACT_SCIENCES: (
        "информат", "вычислительн", "линал", "линейн", "матан",
        "математ", "матстат", "статист", "физик", "дискрет",
        "теория вероят", "численн",
    ),
}


def normalize_discipline_name(name: str) -> str:
    """Нормализует название дисциплины для keyword-сопоставления."""
    normalized = name.lower().replace("ё", "е")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def infer_discipline_group(name: str) -> str:
    """Keyword-based группировка (синхронная). Используется как fallback."""
    normalized = normalize_discipline_name(name)
    for group in GROUP_ORDER:
        for keyword in _KEYWORDS.get(group, ()):
            if keyword in normalized:
                return group
    return OTHER


def display_discipline_category(name: str, stored_category: str | None) -> str:
    """Категория для UI: сохранённое значение или keyword-based fallback."""
    return stored_category or infer_discipline_group(name)


def ordered_group_names(names: Iterable[str]) -> list[str]:
    """Стабильный порядок групп: канонические первыми, затем прочие по алфавиту."""
    unique = set(names)
    ordered = [group for group in GROUP_ORDER if group in unique]
    rest = sorted(unique.difference(GROUP_ORDER))
    return [*ordered, *rest]
>>>>>>> github/main
