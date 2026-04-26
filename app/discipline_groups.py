"""Правила группировки учебных дисциплин в понятные работодателю блоки."""

from __future__ import annotations

import re
from collections.abc import Iterable

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

_KEYWORDS: dict[str, tuple[str, ...]] = {
    PROGRAMMING: (
        "python",
        "java",
        "javascript",
        "typescript",
        "c++",
        "c#",
        "sql",
        "docker",
        "kubernetes",
        "алгоритм",
        "структур",
        "программ",
        "разработ",
        "ооп",
        "backend",
        "frontend",
        "веб",
        "баз данных",
        "базы данных",
    ),
    FOREIGN_LANGUAGES: (
        "англий",
        "немец",
        "француз",
        "испан",
        "китай",
        "иностран",
        "foreign",
        "english",
        "german",
    ),
    SOFT_SKILLS: (
        "soft skill",
        "софт",
        "lean",
        "бережлив",
        "менеджмент",
        "психолог",
        "управление",
        "проект",
        "коммуникац",
        "команд",
        "лидер",
        "предприним",
    ),
    EXACT_SCIENCES: (
        "информат",
        "вычислительн",
        "линал",
        "линейн",
        "матан",
        "математ",
        "матстат",
        "статист",
        "физик",
        "дискрет",
        "теория вероят",
        "численн",
    ),
}


def normalize_discipline_name(name: str) -> str:
    """Нормализует название дисциплины для rule-based сопоставления."""
    normalized = name.lower().replace("ё", "е")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def infer_discipline_group(name: str) -> str:
    """Возвращает каноническую группу дисциплины по keyword rules."""
    normalized = normalize_discipline_name(name)
    for group in GROUP_ORDER:
        for keyword in _KEYWORDS.get(group, ()):
            if keyword in normalized:
                return group
    return OTHER


def display_discipline_category(name: str, stored_category: str | None) -> str:
    """Категория для UI: сохранённая override-категория или rule-based fallback."""
    return stored_category or infer_discipline_group(name)


def ordered_group_names(names: Iterable[str]) -> list[str]:
    """Стабильный порядок групп: канонические первыми, затем прочие по алфавиту."""
    unique = set(names)
    ordered = [group for group in GROUP_ORDER if group in unique]
    rest = sorted(unique.difference(GROUP_ORDER))
    return [*ordered, *rest]
