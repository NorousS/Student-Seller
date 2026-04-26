import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tag, Vacancy


@pytest.mark.asyncio
async def test_tags_endpoint_returns_global_stats(client: AsyncClient, db_session: AsyncSession):
    """Админская вкладка тегов получает агрегированную статистику по вакансиям."""
    python = Tag(name="Python")
    sql = Tag(name="SQL")
    vacancy = Vacancy(
        hh_id="tag-test-1",
        url="https://hh.ru/vacancy/tag-test-1",
        title="Python разработчик",
        salary_from=200000,
        salary_to=None,
        salary_currency="RUR",
        experience="noExperience",
        search_query="python",
    )
    vacancy.tags.extend([python, sql])
    db_session.add(vacancy)
    await db_session.flush()

    resp = await client.get("/api/v1/tags")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_vacancies"] == 1
    assert {"name": "Python", "count": 1} in data["tags"]
    assert {"name": "SQL", "count": 1} in data["tags"]
