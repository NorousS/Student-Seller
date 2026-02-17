"""
Роутер для работы с вакансиями.
Содержит эндпоинт для парсинга вакансий и получения статистики.
"""

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Tag, Vacancy
from app.parser import hh_parser
from app.vector_store import vector_store
from app.schemas import (
    ExperienceLevel,
    ParseRequest, 
    ParseResponse, 
    TagCount, 
    VacanciesWithStatsResponse,
    VacancyResponse,
)

router = APIRouter(prefix="/api/v1", tags=["vacancies"])


@router.post("/parse", response_model=ParseResponse)
async def parse_vacancies(
    request: ParseRequest,
    db: AsyncSession = Depends(get_db),
) -> ParseResponse:
    """
    Парсит вакансии по ключевому слову и сохраняет в БД.
    
    Возвращает статистику:
    - Количество распаршенных вакансий
    - Теги с количеством упоминаний
    - Средняя зарплата
    """
    # Парсим вакансии с hh.ru
    parsed_vacancies = await hh_parser.search_vacancies(
        query=request.query,
        count=request.count,
        experience=request.experience.value if request.experience else None,
    )
    
    # Счётчик тегов и данные для расчёта средней зарплаты
    tag_counter: Counter[str] = Counter()
    salaries: list[int] = []
    saved_count = 0
    all_tag_names: list[str] = []
    
    for parsed in parsed_vacancies:
        # Проверяем, нет ли уже такой вакансии
        existing = await db.execute(
            select(Vacancy).where(Vacancy.hh_id == parsed.hh_id)
        )
        if existing.scalar_one_or_none():
            continue
        
        # Создаём объект вакансии
        vacancy = Vacancy(
            hh_id=parsed.hh_id,
            url=parsed.url,
            title=parsed.title,
            salary_from=parsed.salary_from,
            salary_to=parsed.salary_to,
            salary_currency=parsed.salary_currency,
            experience=parsed.experience,
            search_query=request.query,
        )
        
        # Обрабатываем теги
        for tag_name in parsed.tags:
            tag_counter[tag_name] += 1
            
            # Ищем или создаём тег
            tag_result = await db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                await db.flush()  # Получаем ID тега
            
            vacancy.tags.append(tag)
        
        # Собираем зарплаты для расчёта средней
        # Приоритет: salary_from, если нет — salary_to
        if parsed.salary_from:
            salaries.append(parsed.salary_from)
        elif parsed.salary_to:
            salaries.append(parsed.salary_to)
        
        db.add(vacancy)
        saved_count += 1
    
    await db.commit()  # Явно фиксируем изменения
    
    # Индексируем теги в Qdrant для семантического поиска
    all_tag_names = list(tag_counter.keys())
    if all_tag_names:
        try:
            indexed = await vector_store.upsert_skills(all_tag_names)
            if indexed:
                print(f"Проиндексировано {indexed} новых навыков в Qdrant")
        except Exception as e:
            print(f"Ошибка индексации в Qdrant (не критично): {e}")
    
    # Формируем ответ
    # Сортируем теги по убыванию популярности
    sorted_tags = [
        TagCount(name=name, count=count)
        for name, count in tag_counter.most_common()
    ]
    
    average_salary = None
    if salaries:
        average_salary = sum(salaries) / len(salaries)
    
    return ParseResponse(
        total_parsed=saved_count,
        tags=sorted_tags,
        average_salary=average_salary,
    )


@router.get("/vacancies", response_model=VacanciesWithStatsResponse)
async def get_vacancies(
    query: str | None = None,
    experience: ExperienceLevel | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> VacanciesWithStatsResponse:
    """
    Получает сохранённые вакансии из БД со статистикой.
    
    Args:
        query: Поиск по названию вакансии (регистронезависимый)
        experience: Фильтр по уровню опыта
        limit: Максимальное количество вакансий
        
    Returns:
        Список вакансий со статистикой (теги, средняя ЗП)
    """
    stmt = select(Vacancy).limit(limit)
    
    if query:
        # Ищем по вхождению в название вакансии, игнорируя регистр
        stmt = stmt.where(Vacancy.title.ilike(f"%{query}%"))
    
    # TODO: для фильтрации по опыту нужно добавить поле experience в модель Vacancy
    # Пока фильтрация по опыту доступна только при парсинге
    
    result = await db.execute(stmt)
    vacancies = result.scalars().all()
    
    # Считаем статистику
    tag_counter: Counter[str] = Counter()
    salaries: list[int] = []
    
    vacancy_responses = []
    for v in vacancies:
        # Собираем теги
        for tag in v.tags:
            tag_counter[tag.name] += 1
        
        # Собираем зарплаты
        if v.salary_from:
            salaries.append(v.salary_from)
        elif v.salary_to:
            salaries.append(v.salary_to)
        
        vacancy_responses.append(
            VacancyResponse(
                id=v.id,
                hh_id=v.hh_id,
                url=v.url,
                title=v.title,
                salary_from=v.salary_from,
                salary_to=v.salary_to,
                salary_currency=v.salary_currency,
                tags=[tag.name for tag in v.tags],
            )
        )
    
    # Формируем статистику
    sorted_tags = [
        TagCount(name=name, count=count)
        for name, count in tag_counter.most_common()
    ]
    
    average_salary = None
    if salaries:
        average_salary = sum(salaries) / len(salaries)
    
    return VacanciesWithStatsResponse(
        total_count=len(vacancies),
        vacancies=vacancy_responses,
        tags=sorted_tags,
        average_salary=average_salary,
    )
