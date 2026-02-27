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
