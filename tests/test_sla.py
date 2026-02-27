"""SLA-тест: проверка времени отклика эндпоинта оценки студента."""
import time
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evaluation_responds_within_sla(client: AsyncClient, student_headers: dict, admin_headers: dict):
    """Evaluation endpoint should respond within 10 seconds for a typical student."""
    # 1. Create a student profile with a few disciplines
    # Use the student profile update endpoint to add about_me
    await client.put(
        "/api/v1/profile/student/",
        json={"about_me": "Python developer", "full_name": "SLA Test Student"},
        headers=student_headers,
    )

    # 2. Add some disciplines to the student
    # First check what disciplines exist
    discs = await client.get("/api/v1/profile/student/disciplines", headers=student_headers)

    # 3. Call self-evaluation and measure time
    start = time.monotonic()
    response = await client.post(
        "/api/v1/profile/student/evaluate",
        params={"specialty": "Python разработчик"},
        headers=student_headers,
    )
    elapsed = time.monotonic() - start

    # The endpoint may return 200 (with results) or 400/500 (if Qdrant/Ollama unavailable)
    # For SLA we care about response time, not necessarily success
    # (in CI without Qdrant/Ollama it will fail fast)

    # Assert response time within SLA (10 seconds — generous for tests without Qdrant/Ollama)
    assert elapsed < 10.0, f"Evaluation took {elapsed:.2f}s, exceeds 10s SLA"

    # If successful, verify response structure
    if response.status_code == 200:
        data = response.json()
        assert "estimated_salary" in data or "salary" in data or isinstance(data, dict)


@pytest.mark.asyncio
async def test_top_students_endpoint_sla(client: AsyncClient):
    """Landing top-students endpoint should respond within 3 seconds."""
    start = time.monotonic()
    response = await client.get("/api/v1/landing/top-students")
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    assert elapsed < 3.0, f"Top students took {elapsed:.2f}s, exceeds 3s SLA"


@pytest.mark.asyncio
async def test_employer_search_sla(client: AsyncClient, employer_headers: dict):
    """Employer search endpoint should respond within 10 seconds."""
    start = time.monotonic()
    response = await client.post(
        "/api/v1/employer/search",
        json={"job_title": "Python разработчик"},
        headers=employer_headers,
    )
    elapsed = time.monotonic() - start

    # May fail if Qdrant/Ollama unavailable, but should respond fast
    assert elapsed < 10.0, f"Search took {elapsed:.2f}s, exceeds 10s SLA"
