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
