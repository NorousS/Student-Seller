"""
Тесты аутентификации и авторизации.
TDD: RED → GREEN цикл.
"""

import pytest
from httpx import AsyncClient


# === REGISTER ===


@pytest.mark.asyncio
async def test_register_student_success(client: AsyncClient):
    """Регистрация студента — успех."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "new_student@test.com",
        "password": "pass123",
        "role": "student",
        "full_name": "Иванов Иван",
        "group_name": "CS-101",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_student@test.com"
    assert data["role"] == "student"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_employer_success(client: AsyncClient):
    """Регистрация работодателя — успех."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "employer@test.com",
        "password": "pass123",
        "role": "employer",
        "company_name": "ООО Тест",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "employer"


@pytest.mark.asyncio
async def test_register_admin_success(client: AsyncClient):
    """Регистрация админа — успех."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "admin123",
        "role": "admin",
    })
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Дублирующий email — 409."""
    await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com",
        "password": "pass123",
        "role": "admin",
    })
    response = await client.post("/api/v1/auth/register", json={
        "email": "dup@test.com",
        "password": "pass456",
        "role": "admin",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_student_without_name(client: AsyncClient):
    """Студент без ФИО — 400."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "no_name@test.com",
        "password": "pass123",
        "role": "student",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Короткий пароль — 422 (Pydantic validation)."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "short@test.com",
        "password": "12345",
        "role": "admin",
    })
    assert response.status_code == 422


# === LOGIN ===


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Успешный логин — получаем токены."""
    await client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "password": "pass123",
        "role": "admin",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "pass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Неправильный пароль — 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@test.com",
        "password": "pass123",
        "role": "admin",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "wrong@test.com",
        "password": "wrongpass",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    """Несуществующий email — 401."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "ghost@test.com",
        "password": "pass123",
    })
    assert response.status_code == 401


# === ME ===


@pytest.mark.asyncio
async def test_me_with_token(client: AsyncClient, admin_headers: dict):
    """GET /me с валидным токеном — успех."""
    response = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    """GET /me без токена — 401/403."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


# === REFRESH ===


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    """Refresh token — получаем новые токены."""
    await client.post("/api/v1/auth/register", json={
        "email": "refresh@test.com",
        "password": "pass123",
        "role": "admin",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "refresh@test.com",
        "password": "pass123",
    })
    refresh_tok = login_resp.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_tok,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient):
    """Refresh с access-токеном — 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "refresh_bad@test.com",
        "password": "pass123",
        "role": "admin",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "refresh_bad@test.com",
        "password": "pass123",
    })
    access_tok = login_resp.json()["access_token"]

    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_tok,
    })
    assert response.status_code == 401


# === ROLE PROTECTION ===


@pytest.mark.asyncio
async def test_admin_endpoint_without_auth(client: AsyncClient):
    """Доступ к admin-эндпоинту без токена — 401/403."""
    response = await client.get("/api/v1/students/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_endpoint_as_student(client: AsyncClient, student_headers: dict):
    """Студент не может использовать admin-эндпоинт — 403."""
    response = await client.get("/api/v1/students/", headers=student_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_endpoint_as_admin(client: AsyncClient, admin_headers: dict):
    """Админ может использовать admin-эндпоинт — 200."""
    response = await client.get("/api/v1/students/", headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_parse(client: AsyncClient, student_headers: dict):
    """Студент не может парсить вакансии — 403."""
    response = await client.post("/api/v1/parse", json={
        "query": "python",
        "count": 1,
    }, headers=student_headers)
    assert response.status_code == 403
