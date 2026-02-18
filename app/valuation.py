"""
Сервис оценки потенциальной рыночной стоимости студента.

Алгоритм:
1. Фильтруем вакансии по специальности (семантическое сопоставление search_query)
   и опыту работы
2. Для каждой дисциплины студента → семантический поиск ближайших навыков hh.ru
3. Отсеиваем теги с < MIN_TAG_COUNT вакансий (выбросы)
4. Для каждого навыка → средняя ЗП из отфильтрованных вакансий
5. Взвешенная оценка: similarity × log1p(count) × grade_coeff
"""

import math
from dataclasses import dataclass

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tag, Vacancy, vacancy_tag_association
from app.vector_store import vector_store
from app.embeddings import embedding_service
from app.config import settings

# Минимальное количество вакансий для тега, чтобы он учитывался
MIN_TAG_COUNT = 3

# Порог сходства для семантического сопоставления specialty → search_query
SPECIALTY_SIMILARITY_THRESHOLD = 0.7

# Коэффициенты оценок
GRADE_COEFFICIENTS = {3: 0.75, 4: 0.85, 5: 1.0}


@dataclass
class DisciplineWithGrade:
    """Дисциплина с оценкой студента."""
    name: str
    grade: int  # 3, 4, 5


@dataclass
class SkillMatch:
    """Результат сопоставления дисциплины с навыком hh.ru."""
    discipline: str
    skill_name: str
    similarity: float
    avg_salary: float | None
    vacancy_count: int
    grade: int
    grade_coeff: float
    excluded: bool = False


@dataclass
class ValuationResult:
    """Результат оценки стоимости студента."""
    estimated_salary: float | None
    confidence: float  # 0..1
    skill_matches: list[SkillMatch]
    total_disciplines: int
    matched_disciplines: int


async def get_matching_search_queries(
    db: AsyncSession, specialty: str
) -> list[str]:
    """
    Семантически сопоставляет specialty с search_query из вакансий.
    Возвращает список search_query, похожих на specialty.
    """
    # Получаем все уникальные search_query
    stmt = select(distinct(Vacancy.search_query))
    result = await db.execute(stmt)
    all_queries = [row[0] for row in result.all()]

    if not all_queries:
        return []

    # Получаем эмбеддинг specialty
    specialty_emb = await embedding_service.get_embedding(specialty)

    # Получаем эмбеддинги всех search_query
    query_embeddings = await embedding_service.get_embeddings_batch(all_queries)

    # Вычисляем cosine similarity и фильтруем
    matching = []
    for query_text, query_emb in zip(all_queries, query_embeddings):
        sim = _cosine_similarity(specialty_emb, query_emb)
        if sim >= SPECIALTY_SIMILARITY_THRESHOLD:
            matching.append(query_text)

    return matching


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Вычисляет косинусное сходство двух векторов."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_tag_salary_stats(
    db: AsyncSession,
    tag_name: str,
    search_queries: list[str] | None = None,
    experience: str | None = None,
) -> tuple[float | None, int]:
    """
    Получает среднюю зарплату и количество вакансий для тега.
    Фильтрует по search_query и experience.
    Учитывает только вакансии с зарплатой в RUB.
    """
    stmt = (
        select(
            func.avg(
                func.coalesce(Vacancy.salary_from, Vacancy.salary_to)
            ).label("avg_salary"),
            func.count(Vacancy.id).label("cnt"),
        )
        .join(vacancy_tag_association, Vacancy.id == vacancy_tag_association.c.vacancy_id)
        .join(Tag, Tag.id == vacancy_tag_association.c.tag_id)
        .where(
            Tag.name == tag_name,
            Vacancy.salary_currency == "RUR",
            (Vacancy.salary_from.isnot(None)) | (Vacancy.salary_to.isnot(None)),
        )
    )

    if search_queries is not None:
        stmt = stmt.where(Vacancy.search_query.in_(search_queries))

    if experience is not None:
        stmt = stmt.where(Vacancy.experience == experience)

    result = await db.execute(stmt)
    row = result.one()
    avg_salary = float(row.avg_salary) if row.avg_salary else None
    return avg_salary, row.cnt


async def evaluate_student(
    db: AsyncSession,
    disciplines: list[DisciplineWithGrade],
    specialty: str,
    experience: str | None = None,
    top_k: int = 5,
    excluded_skills: list[str] | None = None,
) -> ValuationResult:
    """
    Оценивает потенциальную рыночную стоимость студента.

    Args:
        db: Сессия БД
        disciplines: Список дисциплин с оценками
        specialty: Специальность для фильтрации вакансий
        experience: Фильтр по опыту работы
        top_k: Сколько ближайших навыков искать на дисциплину
        excluded_skills: Навыки, которые нужно исключить из расчёта
    """
    # Нормализуем excluded_skills для быстрого поиска
    excluded_set = set(
        s.lower() for s in (excluded_skills or [])
    )

    # Шаг 1: Семантическая фильтрация вакансий по специальности
    matching_queries = await get_matching_search_queries(db, specialty)

    all_matches: list[SkillMatch] = []
    weighted_salary_sum = 0.0
    weight_sum = 0.0
    matched_disciplines = 0

    for disc in disciplines:
        grade_coeff = GRADE_COEFFICIENTS.get(disc.grade, 1.0)

        # Семантический поиск ближайших навыков hh.ru
        similar_skills = await vector_store.search_similar_skills(
            text=disc.name,
            top_k=top_k,
            score_threshold=settings.similarity_threshold,
        )

        discipline_has_match = False

        for skill_data in similar_skills:
            skill_name = skill_data["name"]
            similarity = skill_data["score"]

            # Получаем статистику ЗП с фильтрами
            avg_salary, vacancy_count = await get_tag_salary_stats(
                db, skill_name,
                search_queries=matching_queries if matching_queries else None,
                experience=experience,
            )

            is_excluded = skill_name.lower() in excluded_set

            match = SkillMatch(
                discipline=disc.name,
                skill_name=skill_name,
                similarity=similarity,
                avg_salary=avg_salary,
                vacancy_count=vacancy_count,
                grade=disc.grade,
                grade_coeff=grade_coeff,
                excluded=is_excluded,
            )
            all_matches.append(match)

            # Фильтр: тег валиден только если >= MIN_TAG_COUNT вакансий
            # и навык не в списке исключённых
            if avg_salary and vacancy_count >= MIN_TAG_COUNT and not is_excluded:
                discipline_has_match = True
                weight = similarity * math.log1p(vacancy_count) * grade_coeff
                weighted_salary_sum += avg_salary * weight
                weight_sum += weight

        if discipline_has_match:
            matched_disciplines += 1

    # Итоговая оценка
    estimated_salary = None
    if weight_sum > 0:
        estimated_salary = round(weighted_salary_sum / weight_sum, 2)

    confidence = (
        matched_disciplines / len(disciplines)
        if disciplines
        else 0.0
    )

    return ValuationResult(
        estimated_salary=estimated_salary,
        confidence=round(confidence, 2),
        skill_matches=all_matches,
        total_disciplines=len(disciplines),
        matched_disciplines=matched_disciplines,
    )
