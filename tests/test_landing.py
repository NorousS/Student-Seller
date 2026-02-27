"""
Тесты лендинга, воронки приглашений, paywall и гейтинга контактов.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_top_students_returns_list(client: AsyncClient):
    """Эндпоинт top-students возвращает список."""
    resp = await client.get("/api/v1/landing/top-students")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_top_students_max_five(client: AsyncClient, admin_headers: dict):
    """Не более 5 студентов."""
    # Create several students
    for i in range(7):
        await client.post("/api/v1/students/", json={
            "full_name": f"Student {i}",
            "group_name": "GRP-1",
            "disciplines": [{"name": f"Disc-{i}-A", "grade": 5}, {"name": f"Disc-{i}-B", "grade": 4}],
        }, headers=admin_headers)

    resp = await client.get("/api/v1/landing/top-students")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 5


@pytest.mark.asyncio
async def test_top_students_no_contacts_exposed(client: AsyncClient, admin_headers: dict):
    """Карточки не содержат персональных контактов."""
    await client.post("/api/v1/students/", json={
        "full_name": "Secret Student",
        "group_name": "GRP-1",
        "disciplines": [{"name": "Math-Landing", "grade": 5}],
    }, headers=admin_headers)

    resp = await client.get("/api/v1/landing/top-students")
    data = resp.json()
    for card in data:
        assert "full_name" not in card
        assert "email" not in card
        assert "group_name" not in card


@pytest.mark.asyncio
async def test_partner_invite_creates_request(client: AsyncClient, admin_headers: dict, employer_headers: dict):
    """Партнер может создать приглашение."""
    # Create student
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Invite Target",
        "group_name": "GRP-1",
        "disciplines": [{"name": "Prog-Invite", "grade": 5}],
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    # Make employer a partner
    resp = await client.get("/api/v1/auth/me", headers=employer_headers)
    employer_user_id = resp.json()["id"]
    await client.patch(
        f"/api/v1/admin/partnership/employer/{employer_user_id}",
        json={"partnership_status": "partner"},
        headers=admin_headers,
    )

    # Invite
    resp = await client.post(f"/api/v1/landing/invite/{student_id}", headers=employer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "invite_created"


@pytest.mark.asyncio
async def test_non_partner_gets_paywall(client: AsyncClient, admin_headers: dict, employer_headers: dict):
    """Непартнер получает paywall_required."""
    # Create student
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Paywall Target",
        "group_name": "GRP-1",
        "disciplines": [{"name": "Prog-Paywall", "grade": 5}],
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    # Non-partner tries to invite
    resp = await client.post(f"/api/v1/landing/invite/{student_id}", headers=employer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "paywall_required"


@pytest.mark.asyncio
async def test_paywall_options_returns_options(client: AsyncClient, employer_headers: dict):
    """Paywall options возвращает минимум 2 варианта."""
    resp = await client.get("/api/v1/landing/paywall-options", headers=employer_headers)
    assert resp.status_code == 200
    options = resp.json()
    assert len(options) >= 2
    for opt in options:
        assert "id" in opt
        assert "title" in opt


@pytest.mark.asyncio
async def test_contacts_hidden_without_accepted_invite(client: AsyncClient, admin_headers: dict, employer_headers: dict):
    """Контакты недоступны без accepted приглашения."""
    # Create student
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Hidden Contact",
        "group_name": "GRP-1",
        "disciplines": [{"name": "Prog-Hidden", "grade": 5}],
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    # Try to get contacts without any invite
    resp = await client.get(f"/api/v1/landing/student/{student_id}/contacts", headers=employer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contacts_visible_after_accepted_invite(client: AsyncClient, admin_headers: dict, employer_headers: dict, student_headers: dict):
    """Контакты доступны после принятия приглашения."""
    # Get student user's student record
    resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert resp.status_code == 200
    student_id = resp.json()["id"]

    # Make employer a partner
    resp = await client.get("/api/v1/auth/me", headers=employer_headers)
    employer_user_id = resp.json()["id"]
    await client.patch(
        f"/api/v1/admin/partnership/employer/{employer_user_id}",
        json={"partnership_status": "partner"},
        headers=admin_headers,
    )

    # Create invite via landing
    resp = await client.post(f"/api/v1/landing/invite/{student_id}", headers=employer_headers)
    assert resp.status_code == 200

    # Student accepts the invite
    resp = await client.get("/api/v1/profile/student/contact-requests", headers=student_headers)
    requests = resp.json()
    assert len(requests) >= 1
    cr_id = requests[0]["id"]

    resp = await client.post(
        f"/api/v1/profile/student/contact-requests/{cr_id}/respond",
        json={"accept": True},
        headers=student_headers,
    )
    assert resp.status_code == 200

    # Now employer can get contacts
    resp = await client.get(f"/api/v1/landing/student/{student_id}/contacts", headers=employer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "full_name" in data


@pytest.mark.asyncio
async def test_role_visibility_employer_no_full_grades(client: AsyncClient, admin_headers: dict, employer_headers: dict):
    """Работодатель не видит полную академическую ведомость."""
    # Create student
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Visibility Target",
        "group_name": "GRP-1",
        "disciplines": [{"name": "Prog-Visibility", "grade": 5}],
    }, headers=admin_headers)
    student_id = resp.json()["id"]

    # Get profile as employer
    resp = await client.get(f"/api/v1/employer/students/{student_id}/profile", headers=employer_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Should not contain full_name (anonymized)
    assert "full_name" not in data
    # Should have student_id
    assert data["student_id"] == student_id
