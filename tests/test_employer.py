"""
Тесты работодателя: профиль, анонимизированные профили, запросы на контакт.
TDD: RED → GREEN цикл.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Discipline, Student, ContactRequest, StudentDiscipline


@pytest.mark.asyncio
async def test_get_employer_profile(client: AsyncClient, employer_headers: dict):
    """Работодатель может получить свой профиль."""
    response = await client.get("/api/v1/employer/profile", headers=employer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Test Corp"


@pytest.mark.asyncio
async def test_update_employer_profile(client: AsyncClient, employer_headers: dict):
    """Работодатель может обновить свой профиль."""
    response = await client.put("/api/v1/employer/profile", json={
        "company_name": "New Corp",
        "position": "HR Manager",
    }, headers=employer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "New Corp"
    assert data["position"] == "HR Manager"


@pytest.mark.asyncio
async def test_anonymized_student_profile_no_name(client: AsyncClient, employer_headers: dict, admin_headers: dict):
    """Анонимизированный профиль не содержит ФИО."""
    # Create a student via admin
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Secret Name",
        "group_name": "SECRET-1",
        "disciplines": [{"name": "Python", "grade": 5}],
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    # Get anonymized profile as employer
    response = await client.get(
        f"/api/v1/employer/students/{student_id}/profile",
        headers=employer_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "full_name" not in data
    assert "group_name" not in data
    assert data["student_id"] == student_id
    assert len(data["disciplines"]) == 1
    assert data["about_me"] is None  # No contact yet


@pytest.mark.asyncio
async def test_anonymized_student_profile_includes_discipline_groups(
    client: AsyncClient,
    employer_headers: dict,
    db_session: AsyncSession,
):
    """Профиль работодателя явно отдаёт смысловые группы дисциплин."""
    student = Student(full_name="Grouped Student", group_name="HIDDEN")
    math = Discipline(name="Linear Algebra Employer", category="EXACT_SCIENCES")
    soft = Discipline(name="Leadership Employer", category="SOFT_SKILLS")
    db_session.add_all([student, math, soft])
    await db_session.flush()
    db_session.add_all([
        StudentDiscipline(student_id=student.id, discipline_id=math.id, grade=5),
        StudentDiscipline(student_id=student.id, discipline_id=soft.id, grade=4),
    ])
    await db_session.flush()

    response = await client.get(
        f"/api/v1/employer/students/{student.id}/profile",
        headers=employer_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "full_name" not in data
    assert "group_name" not in data
    assert {group["label"] for group in data["discipline_groups"]} == {"Точные науки", "Soft skills"}


@pytest.mark.asyncio
async def test_request_contact(client: AsyncClient, employer_headers: dict, admin_headers: dict):
    """Работодатель может отправить запрос на контакт."""
    # Create student
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Contact Me",
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    # Request contact
    response = await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["student_id"] == student_id


@pytest.mark.asyncio
async def test_request_contact_duplicate(client: AsyncClient, employer_headers: dict, admin_headers: dict):
    """Повторный запрос на контакт — 409."""
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Dup Contact",
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )
    response = await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_student_respond_to_contact_request(client: AsyncClient, employer_headers: dict, student_headers: dict):
    """
    Студент может принять запрос на контакт.
    Используем студента, созданного через student_headers fixture.
    """
    # Get student's profile to find their ID
    profile_resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    student_id = profile_resp.json()["id"]

    # Employer sends request
    cr_resp = await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )
    assert cr_resp.status_code == 200
    request_id = cr_resp.json()["id"]

    # Student sees incoming requests
    requests_resp = await client.get(
        "/api/v1/profile/student/contact-requests",
        headers=student_headers,
    )
    assert requests_resp.status_code == 200
    assert len(requests_resp.json()) == 1

    # Student accepts
    resp = await client.post(
        f"/api/v1/profile/student/contact-requests/{request_id}/respond",
        json={"accept": True},
        headers=student_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_about_me_visible_after_accept(client: AsyncClient, employer_headers: dict, student_headers: dict):
    """После принятия запроса about_me становится видимым."""
    # Update student about_me
    await client.put(
        "/api/v1/profile/student/",
        params={"about_me": "Привет, я студент!"},
        headers=student_headers,
    )

    # Get student ID
    profile_resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    student_id = profile_resp.json()["id"]

    # Before contact: about_me should be None
    anon_resp = await client.get(
        f"/api/v1/employer/students/{student_id}/profile",
        headers=employer_headers,
    )
    assert anon_resp.json()["about_me"] is None

    # Send and accept contact request
    cr_resp = await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )
    request_id = cr_resp.json()["id"]

    await client.post(
        f"/api/v1/profile/student/contact-requests/{request_id}/respond",
        json={"accept": True},
        headers=student_headers,
    )

    # After accept: about_me should be visible
    anon_resp2 = await client.get(
        f"/api/v1/employer/students/{student_id}/profile",
        headers=employer_headers,
    )
    assert anon_resp2.json()["about_me"] == "Привет, я студент!"


@pytest.mark.asyncio
async def test_student_cannot_access_employer_endpoints(client: AsyncClient, student_headers: dict):
    """Студент не может использовать эндпоинты работодателя."""
    response = await client.get("/api/v1/employer/profile", headers=student_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employer_contact_requests_list(client: AsyncClient, employer_headers: dict, admin_headers: dict):
    """Работодатель может получить список своих запросов."""
    resp = await client.post("/api/v1/students/", json={
        "full_name": "List Contact",
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )

    response = await client.get("/api/v1/employer/contact-requests", headers=employer_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


# === NEW TESTS: Extended coverage ===


@pytest.mark.asyncio
async def test_search_with_empty_job_title(client: AsyncClient, employer_headers: dict):
    """Поиск с пустым job_title — 422 (валидация min_length=1)."""
    response = await client.post("/api/v1/employer/search", json={
        "job_title": "",
    }, headers=employer_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_profile_nonexistent_student(client: AsyncClient, employer_headers: dict):
    """Профиль несуществующего студента — 404."""
    response = await client.get(
        "/api/v1/employer/students/999999/profile",
        headers=employer_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_request_contact_nonexistent_student(client: AsyncClient, employer_headers: dict):
    """Запрос на контакт несуществующему студенту — 404."""
    response = await client.post(
        "/api/v1/employer/students/999999/request-contact",
        headers=employer_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_multiple_contact_requests_different_students(
    client: AsyncClient, employer_headers: dict, admin_headers: dict,
):
    """Работодатель может отправить запросы разным студентам."""
    # Create two students
    resp1 = await client.post("/api/v1/students/", json={
        "full_name": "Student One",
    }, headers=admin_headers)
    sid1 = resp1.json()["id"]

    resp2 = await client.post("/api/v1/students/", json={
        "full_name": "Student Two",
    }, headers=admin_headers)
    sid2 = resp2.json()["id"]

    # Send contact requests to both
    cr1 = await client.post(
        f"/api/v1/employer/students/{sid1}/request-contact",
        headers=employer_headers,
    )
    assert cr1.status_code == 200
    assert cr1.json()["student_id"] == sid1

    cr2 = await client.post(
        f"/api/v1/employer/students/{sid2}/request-contact",
        headers=employer_headers,
    )
    assert cr2.status_code == 200
    assert cr2.json()["student_id"] == sid2

    # Verify both appear in list
    list_resp = await client.get("/api/v1/employer/contact-requests", headers=employer_headers)
    assert list_resp.status_code == 200
    requests = list_resp.json()
    student_ids = {r["student_id"] for r in requests}
    assert sid1 in student_ids
    assert sid2 in student_ids


@pytest.mark.asyncio
async def test_reject_contact_about_me_stays_hidden(
    client: AsyncClient, employer_headers: dict, student_headers: dict,
):
    """После отклонения запроса about_me остаётся скрытым."""
    # Set about_me
    await client.put(
        "/api/v1/profile/student/",
        params={"about_me": "Секретная информация"},
        headers=student_headers,
    )

    # Get student ID
    profile_resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    student_id = profile_resp.json()["id"]

    # Send and reject contact request
    cr_resp = await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=employer_headers,
    )
    request_id = cr_resp.json()["id"]

    await client.post(
        f"/api/v1/profile/student/contact-requests/{request_id}/respond",
        json={"accept": False},
        headers=student_headers,
    )

    # Verify about_me is still hidden
    anon_resp = await client.get(
        f"/api/v1/employer/students/{student_id}/profile",
        headers=employer_headers,
    )
    assert anon_resp.status_code == 200
    assert anon_resp.json()["about_me"] is None
