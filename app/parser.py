"""
Асинхронный парсер вакансий с hh.ru через официальный API.

API hh.ru бесплатный и не требует авторизации для базового поиска.
Документация: https://api.hh.ru/openapi/redoc
"""

import asyncio
from dataclasses import dataclass

import httpx

from app.config import settings
from app.middleware.external_api_metrics import track_external_api_call


@dataclass
class ParsedVacancy:
    """Структура распаршенной вакансии."""
    hh_id: str
    url: str
    title: str
    salary_from: int | None
    salary_to: int | None
    salary_currency: str | None
    tags: list[str]
    experience: str | None  # noExperience, between1And3, between3And6, moreThan6


class HHParser:
    """
    Парсер вакансий с hh.ru через официальный API.
    
    Использует два эндпоинта:
    1. GET /vacancies - поиск вакансий (без детальной информации о навыках)
    2. GET /vacancies/{id} - детали вакансии с key_skills
    """
    
    def __init__(self):
        self.base_url = settings.hh_api_base_url
        # API hh.ru требует реалистичный User-Agent
        # Без него возвращает 400 Bad Request
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        # Ограничение на количество параллельных запросов
        self._semaphore = asyncio.Semaphore(5)
    
    async def search_vacancies(
        self, 
        query: str, 
        count: int = 50,
        experience: str | None = None,
    ) -> list[ParsedVacancy]:
        """
        Ищет вакансии по ключевому слову и возвращает детальную информацию.
        
        Args:
            query: Ключевое слово для поиска (например, "python")
            count: Количество вакансий для парсинга
            experience: Фильтр по опыту (noExperience, between1And3, between3And6, moreThan6)
            
        Returns:
            Список распаршенных вакансий с тегами
        """
        async with httpx.AsyncClient(
            base_url=self.base_url, 
            headers=self.headers,
            timeout=30.0
        ) as client:
            # Шаг 1: Получаем список вакансий
            vacancy_ids = await self._fetch_vacancy_ids(client, query, count, experience)
            
            # Шаг 2: Получаем детали каждой вакансии (с key_skills)
            # Используем gather для параллельных запросов
            tasks = [
                self._fetch_vacancy_details(client, vacancy_id) 
                for vacancy_id in vacancy_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтруем ошибки
            vacancies = [v for v in results if isinstance(v, ParsedVacancy)]
            return vacancies
    
    async def _fetch_vacancy_ids(
        self, 
        client: httpx.AsyncClient, 
        query: str, 
        count: int,
        experience: str | None = None,
    ) -> list[str]:
        """
        Получает список ID вакансий через поиск.
        API возвращает максимум 100 вакансий на страницу.
        """
        vacancy_ids: list[str] = []
        per_page = min(count, 100)  # Максимум 100 на страницу
        pages_needed = (count + per_page - 1) // per_page
        
        for page in range(pages_needed):
            if len(vacancy_ids) >= count:
                break
                
            params = {
                "text": query,
                "per_page": per_page,
                "page": page,
            }
            
            # Добавляем фильтр по опыту, если указан
            if experience:
                params["experience"] = experience
            
            try:
                async with track_external_api_call("hh", "search_vacancies"):
                    response = await client.get("/vacancies", params=params)
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                for item in items:
                    if len(vacancy_ids) >= count:
                        break
                    vacancy_ids.append(item["id"])
                    
            except httpx.HTTPError as e:
                # Логируем ошибку, но продолжаем с тем, что есть
                print(f"Ошибка при поиске вакансий: {e}")
                break
        
        return vacancy_ids
    
    async def _fetch_vacancy_details(
        self, 
        client: httpx.AsyncClient, 
        vacancy_id: str
    ) -> ParsedVacancy:
        """
        Получает детальную информацию о вакансии, включая key_skills.
        """
        async with self._semaphore:  # Ограничиваем параллельные запросы
            async with track_external_api_call("hh", "vacancy_details"):
                response = await client.get(f"/vacancies/{vacancy_id}")
            response.raise_for_status()
            data = response.json()
            
            # Извлекаем зарплату
            salary = data.get("salary")
            salary_from = None
            salary_to = None
            salary_currency = None
            
            if salary:
                salary_from = salary.get("from")
                salary_to = salary.get("to")
                salary_currency = salary.get("currency")
            
            # Извлекаем ключевые навыки (теги)
            key_skills = data.get("key_skills", [])
            tags = [skill.get("name", "") for skill in key_skills if skill.get("name")]
            
            # Извлекаем уровень опыта
            experience_data = data.get("experience")
            experience_id = experience_data.get("id") if experience_data else None
            
            return ParsedVacancy(
                hh_id=str(data["id"]),
                url=data.get("alternate_url", f"https://hh.ru/vacancy/{vacancy_id}"),
                title=data.get("name", "Без названия"),
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=salary_currency,
                tags=tags,
                experience=experience_id,
            )


# Глобальный экземпляр парсера
hh_parser = HHParser()
