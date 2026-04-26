"""
Тесты управления партнерством работодателей.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_employer_profile_has_partnership_status(client: AsyncClient, employer_headers: dict):
    """Профиль работодателя содержит partnership_status."""
    resp = await client.get("/api/v1/employer/profile", headers=employer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "partnership_status" in data
    assert data["partnership_status"] == "non_partner"


@pytest.mark.asyncio
async def test_admin_can_update_partnership(client: AsyncClient, admin_headers: dict, employer_headers: dict):
    """Админ может изменить статус партнерства."""
    # First get employer user id
    resp = await client.get("/api/v1/auth/me", headers=employer_headers)
    employer_user_id = resp.json()["id"]

    # Update partnership
    resp = await client.patch(
        f"/api/v1/admin/partnership/employer/{employer_user_id}",
        json={"partnership_status": "partner"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["partnership_status"] == "partner"


@pytest.mark.asyncio
async def test_admin_can_list_employers(client: AsyncClient, admin_headers: dict):
    """Админ видит список работодателей и статус партнерства."""
    resp = await client.get("/api/v1/admin/employers", headers=admin_headers)
    assert resp.status_code == 200
    employers = resp.json()
    assert len(employers) >= 1
    first = employers[0]
    assert "employer_user_id" in first
    assert "email" in first
    assert first["partnership_status"] in {"partner", "non_partner"}


@pytest.mark.asyncio
async def test_non_admin_cannot_list_employers(client: AsyncClient, student_headers: dict):
    """Список работодателей доступен только администратору."""
    resp = await client.get("/api/v1/admin/employers", headers=student_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employer_cannot_update_own_partnership(client: AsyncClient, employer_headers: dict):
    """Работодатель не может сам изменить статус."""
    resp = await client.get("/api/v1/auth/me", headers=employer_headers)
    employer_user_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/partnership/employer/{employer_user_id}",
        json={"partnership_status": "partner"},
        headers=employer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_partnership_audit_trail(client: AsyncClient, admin_headers: dict, employer_headers: dict):
    """Изменение статуса создает запись в аудите."""
    resp = await client.get("/api/v1/auth/me", headers=employer_headers)
    employer_user_id = resp.json()["id"]

    # Change to partner
    await client.patch(
        f"/api/v1/admin/partnership/employer/{employer_user_id}",
        json={"partnership_status": "partner"},
        headers=admin_headers,
    )

    # Check audit
    resp = await client.get(
        f"/api/v1/admin/partnership/audit/{employer_user_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    audits = resp.json()
    assert len(audits) >= 1
    assert audits[0]["old_status"] == "non_partner"
    assert audits[0]["new_status"] == "partner"


# --- Discipline category override tests ---


@pytest.mark.asyncio
async def test_admin_can_update_discipline_category(client: AsyncClient, admin_headers: dict):
    """Админ может обновить категорию дисциплины."""
    # Create a student with a discipline to get a discipline in DB
    resp = await client.post(
        "/api/v1/students/",
        json={"full_name": "Cat Student", "disciplines": [{"name": "Алгоритмы", "grade": 5}]},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    discipline_id = resp.json()["disciplines"][0]["id"]

    # Update category
    resp = await client.patch(
        f"/api/v1/admin/partnership/disciplines/{discipline_id}/category",
        json={"category": "Программирование"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == discipline_id
    assert data["category"] == "Программирование"


@pytest.mark.asyncio
async def test_non_admin_cannot_update_discipline_category(client: AsyncClient, admin_headers: dict, student_headers: dict):
    """Студент не может обновить категорию дисциплины (403)."""
    # Create discipline via admin
    resp = await client.post(
        "/api/v1/students/",
        json={"full_name": "Cat Student 2", "disciplines": [{"name": "Физика", "grade": 4}]},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    discipline_id = resp.json()["disciplines"][0]["id"]

    # Try update as student
    resp = await client.patch(
        f"/api/v1/admin/partnership/disciplines/{discipline_id}/category",
        json={"category": "Наука"},
        headers=student_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_category_invalid_discipline_returns_404(client: AsyncClient, admin_headers: dict):
    """Несуществующая дисциплина возвращает 404."""
    resp = await client.patch(
        "/api/v1/admin/partnership/disciplines/999999/category",
        json={"category": "Несуществующая"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
