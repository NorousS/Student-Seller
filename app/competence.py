"""
Сервис агрегации дисциплин в блоки компетенций.
Группирует дисциплины по категории и рассчитывает метрики блока.
"""

from dataclasses import dataclass

from app.schemas import CompetenceBlockResponse


@dataclass
class DisciplineData:
    """Данные дисциплины для агрегации."""
    name: str
    grade: int
    category: str | None
    skill_tags: list[str]
    market_value: float | None


def aggregate_by_competence(disciplines: list[DisciplineData]) -> list[CompetenceBlockResponse]:
    """
    Группирует дисциплины по category и рассчитывает метрики:
    - avg_grade: средний балл блока
    - market_value: суммарная рыночная ценность
    - strong_points: число дисциплин с оценкой 5
    - top_tags: топ-3 тега по частоте
    - achievements_summary: текстовая сводка
    """
    # Group by category
    blocks: dict[str, list[DisciplineData]] = {}
    for d in disciplines:
        cat = d.category or "Другое"
        blocks.setdefault(cat, []).append(d)

    results = []
    for block_name, disc_list in blocks.items():
        # Average grade
        avg_grade = sum(d.grade for d in disc_list) / len(disc_list) if disc_list else 0

        # Market value sum
        market_values = [d.market_value for d in disc_list if d.market_value]
        total_market_value = sum(market_values) if market_values else None

        # Strong points: count of grade 5
        strong_points = sum(1 for d in disc_list if d.grade == 5)

        # Top tags by frequency
        tag_counts: dict[str, int] = {}
        for d in disc_list:
            for tag in d.skill_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:3]

        # Achievement summary
        parts = [f"{len(disc_list)} дисциплин"]
        if strong_points:
            parts.append(f"{strong_points} на отлично")
        achievements_summary = ", ".join(parts)

        results.append(CompetenceBlockResponse(
            block_name=block_name,
            avg_grade=round(avg_grade, 2),
            market_value=round(total_market_value, 2) if total_market_value else None,
            strong_points=strong_points,
            top_tags=top_tags,
            achievements_summary=achievements_summary,
        ))

    # Sort by market value descending
    results.sort(key=lambda b: b.market_value or 0, reverse=True)
    return results
