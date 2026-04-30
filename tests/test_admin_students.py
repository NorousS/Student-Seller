<<<<<<< HEAD
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_patch_student_happy_path(client: AsyncClient, admin_headers: dict):
    create_resp = await client.post(
        "/api/v1/students/",
        json={"full_name": "Old Name", "group_name": "OLD-1"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    student_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/students/{student_id}",
        json={"full_name": "New Name", "group_name": "NEW-2"},
        headers=admin_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "New Name"
    assert data["group_name"] == "NEW-2"


@pytest.mark.asyncio
async def test_admin_patch_student_requires_admin(
    client: AsyncClient,
    admin_headers: dict,
    student_headers: dict,
):
    create_resp = await client.post(
        "/api/v1/students/",
        json={"full_name": "Protected", "group_name": "P-1"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    student_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/admin/students/{student_id}",
        json={"full_name": "Forbidden"},
        headers=student_headers,
    )

    assert resp.status_code == 403
=======
"""
Tests for admin student PATCH endpoint.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Student


@pytest.mark.asyncio
async def test_patch_student_name(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Admin can update student full_name and group_name."""
    student = Student(full_name="Иванов Иван", group_name="ИВТ-21")
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)

    response = await client.patch(
        f"/api/v1/admin/students/{student.id}",
        json={"full_name": "Петров Пётр", "group_name": "ПМИ-22"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Петров Пётр"
    assert data["group_name"] == "ПМИ-22"


@pytest.mark.asyncio
async def test_patch_student_partial(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Admin can update only full_name, group_name stays unchanged."""
    student = Student(full_name="Сидоров Сидор", group_name="КИ-10")
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)

    response = await client.patch(
        f"/api/v1/admin/students/{student.id}",
        json={"full_name": "Сидоров Семён"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Сидоров Семён"
    # group_name should remain KI-10
    assert data["group_name"] == "КИ-10"


@pytest.mark.asyncio
async def test_patch_student_not_found(client: AsyncClient, admin_headers: dict):
    """Returns 404 for non-existent student."""
    response = await client.patch(
        "/api/v1/admin/students/999999",
        json={"full_name": "Ghost"},
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_student_requires_admin(client: AsyncClient, db_session: AsyncSession):
    """Non-admin cannot patch a student."""
    student = Student(full_name="Protected", group_name="X-1")
    db_session.add(student)
    await db_session.commit()
    await db_session.refresh(student)

    # No auth header
    response = await client.patch(
        f"/api/v1/admin/students/{student.id}",
        json={"full_name": "Hacked"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_admin_students(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Admin can list all students via /admin/students."""
    student = Student(full_name="Список Тест", group_name="ЛС-1")
    db_session.add(student)
    await db_session.commit()

    response = await client.get("/api/v1/admin/students", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = [s["full_name"] for s in data]
    assert "Список Тест" in names
>>>>>>> github/main
