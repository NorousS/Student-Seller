"""
Тесты профиля студента.
TDD: RED → GREEN цикл.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_student_profile(client: AsyncClient, student_headers: dict):
    """Студент может получить свой профиль."""
    response = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Test Student"
    assert data["group_name"] == "TEST-1"


@pytest.mark.asyncio
async def test_update_about_me(client: AsyncClient, student_headers: dict):
    """Студент может обновить 'о себе'."""
    response = await client.put(
        "/api/v1/profile/student/",
        params={"about_me": "Я люблю программирование"},
        headers=student_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_student_self_add_disciplines(client: AsyncClient, student_headers: dict):
    """Студент может добавить себе дисциплины."""
    response = await client.post("/api/v1/profile/student/disciplines", json={
        "disciplines": [
            {"name": "Python", "grade": 5},
            {"name": "SQL", "grade": 4},
        ]
    }, headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["disciplines"]) == 2
    disc_map = {d["name"]: d for d in data["disciplines"]}
    assert disc_map["Python"]["grade"] == 5
    assert disc_map["SQL"]["grade"] == 4


@pytest.mark.asyncio
async def test_get_my_disciplines(client: AsyncClient, student_headers: dict):
    """Студент может получить список своих дисциплин."""
    # Add disciplines first
    await client.post("/api/v1/profile/student/disciplines", json={
        "disciplines": [{"name": "Math", "grade": 3}]
    }, headers=student_headers)

    response = await client.get("/api/v1/profile/student/disciplines", headers=student_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(d["name"] == "Math" for d in data)


@pytest.mark.asyncio
async def test_student_cannot_parse_vacancies(client: AsyncClient, student_headers: dict):
    """Студент НЕ может парсить вакансии (403)."""
    response = await client.post("/api/v1/parse", json={
        "query": "python", "count": 1,
    }, headers=student_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_access_admin_students(client: AsyncClient, student_headers: dict):
    """Студент НЕ может использовать admin CRUD студентов (403)."""
    response = await client.get("/api/v1/students/", headers=student_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employer_cannot_access_student_profile(client: AsyncClient, employer_headers: dict):
    """Работодатель НЕ может получить профиль студента через этот эндпоинт (403)."""
    response = await client.get("/api/v1/profile/student/", headers=employer_headers)
    assert response.status_code == 403


# === NEW TESTS: Extended coverage ===


@pytest.mark.asyncio
async def test_update_about_me_long_text(client: AsyncClient, student_headers: dict):
    """Обновление about_me длинным текстом — успех."""
    long_text = "А" * 5000
    response = await client.put(
        "/api/v1/profile/student/",
        params={"about_me": long_text},
        headers=student_headers,
    )
    assert response.status_code == 200

    # Verify it was saved
    profile = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert profile.json()["about_me"] == long_text


@pytest.mark.asyncio
async def test_add_duplicate_discipline_updates_grade(client: AsyncClient, student_headers: dict):
    """Добавление дисциплины с тем же именем обновляет оценку."""
    # Add discipline
    await client.post("/api/v1/profile/student/disciplines", json={
        "disciplines": [{"name": "Algorithms", "grade": 3}]
    }, headers=student_headers)

    # Add same discipline with different grade
    response = await client.post("/api/v1/profile/student/disciplines", json={
        "disciplines": [{"name": "Algorithms", "grade": 5}]
    }, headers=student_headers)
    assert response.status_code == 200

    # Verify only one entry with updated grade
    disc_resp = await client.get("/api/v1/profile/student/disciplines", headers=student_headers)
    disciplines = disc_resp.json()
    algo_discs = [d for d in disciplines if d["name"] == "Algorithms"]
    assert len(algo_discs) == 1
    assert algo_discs[0]["grade"] == 5


@pytest.mark.asyncio
async def test_profile_photo_url_null_when_no_photo(client: AsyncClient, student_headers: dict):
    """photo_url = null если фото не загружено."""
    response = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert response.status_code == 200
    assert response.json()["photo_url"] is None


@pytest.mark.asyncio
async def test_add_disciplines_in_same_request_deduplicates(client: AsyncClient, student_headers: dict):
    """Дублирующие дисциплины в одном запросе дедуплицируются."""
    response = await client.post("/api/v1/profile/student/disciplines", json={
        "disciplines": [
            {"name": "Physics", "grade": 4},
            {"name": "Physics", "grade": 5},
        ]
    }, headers=student_headers)
    assert response.status_code == 200

    disc_resp = await client.get("/api/v1/profile/student/disciplines", headers=student_headers)
    physics_discs = [d for d in disc_resp.json() if d["name"] == "Physics"]
    assert len(physics_discs) == 1
