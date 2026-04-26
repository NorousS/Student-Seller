"""
Асинхронный парсер вакансий с hh.ru через официальный API.

Поиск вакансий обычно доступен без OAuth, но hh.ru строго проверяет
User-Agent и может отдавать 403/429 на уровне защиты. Такие ошибки
поднимаются наружу с request_id, чтобы админ видел настоящую причину.
Документация: https://api.hh.ru/openapi/redoc
"""

import asyncio
from dataclasses import dataclass
from typing import Any

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


class HHParserError(Exception):
    """Ошибка внешнего API hh.ru с безопасными диагностическими деталями."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        error_type: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.error_type = error_type
        self.endpoint = endpoint

    def to_detail(self) -> dict[str, Any]:
        """Сериализуемая деталь для FastAPI HTTPException."""
        return {
            "message": self.message,
            "status_code": self.status_code,
            "request_id": self.request_id,
            "error_type": self.error_type,
            "endpoint": self.endpoint,
        }


class HHParser:
    """
    Парсер вакансий с hh.ru через официальный API.

    Использует два эндпоинта:
    1. GET /vacancies - поиск вакансий
    2. GET /vacancies/{id} - детали вакансии с key_skills
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        access_token: str | None = None,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or settings.hh_api_base_url
        self.user_agent = user_agent or settings.hh_user_agent
        self.access_token = access_token if access_token is not None else settings.hh_access_token
        self.transport = transport
        self.headers = self._build_headers()
        self._semaphore = asyncio.Semaphore(5)

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _client(self, timeout: float = 30.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout,
            transport=self.transport,
        )

    async def search_vacancies(
        self,
        query: str,
        count: int = 50,
        experience: str | None = None,
    ) -> list[ParsedVacancy]:
        """
        Ищет вакансии по ключевому слову и возвращает детальную информацию.
        """
        async with self._client(timeout=30.0) as client:
            vacancy_ids = await self._fetch_vacancy_ids(client, query, count, experience)

            tasks = [
                self._fetch_vacancy_details(client, vacancy_id)
                for vacancy_id in vacancy_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        vacancies: list[ParsedVacancy] = []
        errors: list[Exception] = []
        for result in results:
            if isinstance(result, ParsedVacancy):
                vacancies.append(result)
            elif isinstance(result, Exception):
                errors.append(result)

        if errors and not vacancies:
            first = errors[0]
            if isinstance(first, HHParserError):
                raise first
            raise HHParserError(f"Не удалось получить детали вакансий hh.ru: {first}")

        return vacancies

    async def check_health(self) -> dict[str, Any]:
        """Проверяет доступность базового справочника и поиска вакансий hh.ru."""
        async with self._client(timeout=20.0) as client:
            areas = await self._probe(client, "/areas")
            vacancies = await self._probe(
                client,
                "/vacancies",
                params={"text": "python", "per_page": 1},
            )

        return {
            "ok": bool(areas["ok"] and vacancies["ok"]),
            "base_url": self.base_url,
            "has_access_token": bool(self.access_token),
            "checks": {
                "areas": areas,
                "vacancies": vacancies,
            },
        }

    async def _probe(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await client.get(endpoint, params=params)
            if response.status_code >= 400:
                error = self._error_from_response(response, endpoint)
                return {
                    "ok": False,
                    **error.to_detail(),
                }
            return {
                "ok": True,
                "status_code": response.status_code,
                "request_id": self._request_id(response),
                "endpoint": endpoint,
            }
        except httpx.HTTPError as e:
            return {
                "ok": False,
                "message": str(e),
                "status_code": None,
                "request_id": None,
                "error_type": "network_error",
                "endpoint": endpoint,
            }

    async def _fetch_vacancy_ids(
        self,
        client: httpx.AsyncClient,
        query: str,
        count: int,
        experience: str | None = None,
    ) -> list[str]:
        """Получает список ID вакансий через поиск."""
        vacancy_ids: list[str] = []
        per_page = min(count, 100)
        pages_needed = (count + per_page - 1) // per_page

        for page in range(pages_needed):
            if len(vacancy_ids) >= count:
                break

            params: dict[str, Any] = {
                "text": query,
                "per_page": per_page,
                "page": page,
            }
            if experience:
                params["experience"] = experience

            try:
                async with track_external_api_call("hh", "search_vacancies"):
                    response = await client.get("/vacancies", params=params)
            except httpx.HTTPError as e:
                raise HHParserError(
                    f"Не удалось подключиться к hh.ru при поиске вакансий: {e}",
                    endpoint="/vacancies",
                    error_type="network_error",
                ) from e

            self._raise_for_bad_response(response, "/vacancies")
            data = response.json()

            items = data.get("items", [])
            for item in items:
                if len(vacancy_ids) >= count:
                    break
                vacancy_ids.append(str(item["id"]))

        return vacancy_ids

    async def _fetch_vacancy_details(
        self,
        client: httpx.AsyncClient,
        vacancy_id: str,
    ) -> ParsedVacancy:
        """Получает детальную информацию о вакансии, включая key_skills."""
        endpoint = f"/vacancies/{vacancy_id}"
        async with self._semaphore:
            try:
                async with track_external_api_call("hh", "vacancy_details"):
                    response = await client.get(endpoint)
            except httpx.HTTPError as e:
                raise HHParserError(
                    f"Не удалось подключиться к hh.ru при получении вакансии {vacancy_id}: {e}",
                    endpoint=endpoint,
                    error_type="network_error",
                ) from e

            self._raise_for_bad_response(response, endpoint)
            data = response.json()

        salary = data.get("salary")
        salary_from = salary.get("from") if salary else None
        salary_to = salary.get("to") if salary else None
        salary_currency = salary.get("currency") if salary else None

        key_skills = data.get("key_skills", [])
        tags = [skill.get("name", "") for skill in key_skills if skill.get("name")]

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

    def _raise_for_bad_response(self, response: httpx.Response, endpoint: str) -> None:
        if response.status_code >= 400:
            raise self._error_from_response(response, endpoint)

    def _error_from_response(self, response: httpx.Response, endpoint: str) -> HHParserError:
        description: str | None = None
        error_type: str | None = None
        request_id = self._request_id(response)

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if isinstance(payload, dict):
            description = payload.get("description")
            request_id = payload.get("request_id") or request_id
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                first = errors[0]
                if isinstance(first, dict):
                    error_type = first.get("type")
                    description = description or first.get("value")

        reason = error_type or response.reason_phrase or "error"
        message = f"HH API вернул {response.status_code} для {endpoint}: {description or reason}"
        return HHParserError(
            message,
            status_code=response.status_code,
            request_id=request_id,
            error_type=error_type,
            endpoint=endpoint,
        )

    @staticmethod
    def _request_id(response: httpx.Response) -> str | None:
        return response.headers.get("X-Request-ID") or response.headers.get("X-Request-Id")


hh_parser = HHParser()
