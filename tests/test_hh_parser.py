import httpx
import pytest
from httpx import AsyncClient

from app.parser import HHParser, HHParserError
from app.routers import admin as admin_router


@pytest.mark.asyncio
@pytest.mark.no_db
async def test_hh_parser_success_mocked():
    """Парсер сохраняет заголовки и собирает вакансию из HH API."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/vacancies":
            return httpx.Response(200, json={"items": [{"id": "123"}]})
        if request.url.path == "/vacancies/123":
            return httpx.Response(
                200,
                json={
                    "id": "123",
                    "alternate_url": "https://hh.ru/vacancy/123",
                    "name": "Python developer",
                    "salary": {"from": 100000, "to": 150000, "currency": "RUR"},
                    "key_skills": [{"name": "Python"}, {"name": "SQL"}],
                    "experience": {"id": "noExperience"},
                },
            )
        return httpx.Response(404, json={"errors": [{"type": "not_found"}]})

    parser = HHParser(
        base_url="https://api.hh.test",
        user_agent="Test UA",
        access_token="secret-token",
        transport=httpx.MockTransport(handler),
    )

    vacancies = await parser.search_vacancies("python", count=1)

    assert len(vacancies) == 1
    assert vacancies[0].hh_id == "123"
    assert vacancies[0].tags == ["Python", "SQL"]
    assert all(request.headers["user-agent"] == "Test UA" for request in requests)
    assert all(request.headers["authorization"] == "Bearer secret-token" for request in requests)


@pytest.mark.asyncio
@pytest.mark.no_db
async def test_hh_parser_forbidden_is_not_silent():
    """403 от HH поднимается наружу с request_id и типом ошибки."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"X-Request-ID": "header-request-id"},
            json={"errors": [{"type": "forbidden"}], "request_id": "body-request-id"},
        )

    parser = HHParser(
        base_url="https://api.hh.test",
        user_agent="Test UA",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(HHParserError) as exc_info:
        await parser.search_vacancies("python", count=1)

    error = exc_info.value
    assert error.status_code == 403
    assert error.request_id == "body-request-id"
    assert error.error_type == "forbidden"
    assert error.endpoint == "/vacancies"


@pytest.mark.asyncio
async def test_admin_parser_health_requires_admin(client: AsyncClient, student_headers: dict):
    resp = await client.get("/api/v1/admin/parser/health", headers=student_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_parser_health_returns_diagnostics(
    client: AsyncClient,
    admin_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    class FakeParser:
        async def check_health(self):
            return {
                "ok": False,
                "base_url": "https://api.hh.test",
                "has_access_token": False,
                "checks": {
                    "areas": {"ok": True, "status_code": 200},
                    "vacancies": {
                        "ok": False,
                        "status_code": 403,
                        "error_type": "forbidden",
                        "request_id": "hh-request-id",
                    },
                },
            }

    monkeypatch.setattr(admin_router, "hh_parser", FakeParser())

    resp = await client.get("/api/v1/admin/parser/health", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["checks"]["vacancies"]["status_code"] == 403
    assert data["checks"]["vacancies"]["request_id"] == "hh-request-id"
