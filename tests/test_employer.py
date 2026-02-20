"""
Тесты работодателя: профиль, анонимизированные профили, запросы на контакт.
TDD: RED → GREEN цикл.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Student, ContactRequest


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
