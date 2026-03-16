"""
Тесты политики видимости данных по ролям (US-017).

Проверяет, что:
- Работодатель видит только анонимизированный профиль (без ФИО, email, user_id)
- Студент видит свой полный профиль
- Студент не может использовать эндпоинты работодателя (403)
- Работодатель не может использовать эндпоинты студента (403)
- Неаутентифицированный пользователь не может обращаться к защищённым ресурсам (401)
- Админ имеет доступ ко всем эндпоинтам
"""

import pytest
from httpx import AsyncClient


# --- Employer sees anonymized profile ---


@pytest.mark.asyncio
async def test_employer_sees_anonymized_profile(
    client: AsyncClient, employer_headers: dict, admin_headers: dict,
):
    """Работодатель видит анонимизированный профиль: нет full_name, email, user_id."""
    # Создаём студента через admin
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Иванов Иван Иванович",
        "group_name": "ВИС-101",
        "disciplines": [{"name": "Программирование", "grade": 5}],
    }, headers=admin_headers)
    assert resp.status_code == 201
    student_id = resp.json()["id"]

    # Получаем анонимизированный профиль как работодатель
    resp = await client.get(
        f"/api/v1/employer/students/{student_id}/profile",
        headers=employer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Поля, которых НЕ должно быть
    assert "full_name" not in data, "full_name must not be in anonymized profile"
    assert "email" not in data, "email must not be in anonymized profile"
    assert "user_id" not in data, "user_id must not be in anonymized profile"
    assert "group_name" not in data, "group_name must not be in anonymized profile"

    # Поля, которые ДОЛЖНЫ быть
    assert data["student_id"] == student_id
    assert "disciplines" in data
    assert "contact_status" in data


@pytest.mark.asyncio
async def test_employer_anonymized_profile_has_no_email(
    client: AsyncClient, employer_headers: dict, student_headers: dict,
):
    """Даже у студента с user_id (зарегистрированного) email не виден работодателю."""
    # student_headers создаёт зарегистрированного студента с email
    profile_resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert profile_resp.status_code == 200
    student_id = profile_resp.json()["id"]

    # Работодатель смотрит профиль
    resp = await client.get(
        f"/api/v1/employer/students/{student_id}/profile",
        headers=employer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "email" not in data
    assert "full_name" not in data
    assert "user_id" not in data


# --- Student sees own profile with full data ---


@pytest.mark.asyncio
async def test_student_sees_own_full_profile(
    client: AsyncClient, student_headers: dict,
):
    """Студент видит свой полный профиль: full_name, group_name, дисциплины."""
    resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert resp.status_code == 200
    data = resp.json()

    # Полные данные должны присутствовать
    assert "full_name" in data
    assert data["full_name"] == "Test Student"
    assert "group_name" in data
    assert "id" in data
    assert "disciplines" in data


# --- Student cannot access employer endpoints (403) ---


@pytest.mark.asyncio
async def test_student_cannot_access_employer_profile(
    client: AsyncClient, student_headers: dict,
):
    """Студент не может получить профиль работодателя — 403."""
    resp = await client.get("/api/v1/employer/profile", headers=student_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_access_employer_search(
    client: AsyncClient, student_headers: dict,
):
    """Студент не может использовать поиск работодателя — 403."""
    resp = await client.post(
        "/api/v1/employer/search",
        json={"job_title": "Python Developer"},
        headers=student_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_access_employer_student_profile(
    client: AsyncClient, student_headers: dict, admin_headers: dict,
):
    """Студент не может просматривать анонимизированные профили других студентов — 403."""
    # Создаём другого студента
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Другой Студент",
    }, headers=admin_headers)
    assert resp.status_code == 201
    other_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/employer/students/{other_id}/profile",
        headers=student_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_request_contact(
    client: AsyncClient, student_headers: dict, admin_headers: dict,
):
    """Студент не может отправить запрос на контакт — 403."""
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Target Student",
    }, headers=admin_headers)
    assert resp.status_code == 201
    student_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/employer/students/{student_id}/request-contact",
        headers=student_headers,
    )
    assert resp.status_code == 403


# --- Employer cannot access student profile endpoints (403) ---


@pytest.mark.asyncio
async def test_employer_cannot_access_student_self_profile(
    client: AsyncClient, employer_headers: dict,
):
    """Работодатель не может зайти на эндпоинт профиля студента — 403."""
    resp = await client.get("/api/v1/profile/student/", headers=employer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employer_cannot_update_student_profile(
    client: AsyncClient, employer_headers: dict,
):
    """Работодатель не может обновить профиль студента — 403."""
    resp = await client.put(
        "/api/v1/profile/student/",
        params={"about_me": "hack"},
        headers=employer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employer_cannot_access_student_disciplines(
    client: AsyncClient, employer_headers: dict,
):
    """Работодатель не может получить дисциплины студента — 403."""
    resp = await client.get(
        "/api/v1/profile/student/disciplines",
        headers=employer_headers,
    )
    assert resp.status_code == 403


# --- Unauthenticated user cannot access protected endpoints (401) ---


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_student_profile(client: AsyncClient):
    """Без токена — 401/403 на профиле студента."""
    resp = await client.get("/api/v1/profile/student/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_employer_profile(client: AsyncClient):
    """Без токена — 401/403 на профиле работодателя."""
    resp = await client.get("/api/v1/employer/profile")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_employer_search(client: AsyncClient):
    """Без токена — 401/403 на поиске."""
    resp = await client.post(
        "/api/v1/employer/search",
        json={"job_title": "Python Developer"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_contacts(client: AsyncClient):
    """Без токена — 401/403 на контактах."""
    resp = await client.get("/api/v1/landing/student/1/contacts")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_admin_students(client: AsyncClient):
    """Без токена — 401/403 на admin-only эндпоинтах."""
    resp = await client.get("/api/v1/students/")
    assert resp.status_code in (401, 403)


# --- Admin can access all endpoints (200) ---


@pytest.mark.asyncio
async def test_admin_can_list_students(
    client: AsyncClient, admin_headers: dict,
):
    """Админ может получить список студентов."""
    resp = await client.get("/api/v1/students/", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_create_student(
    client: AsyncClient, admin_headers: dict,
):
    """Админ может создать студента."""
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Admin Created",
        "group_name": "ADM-1",
        "disciplines": [{"name": "Математика", "grade": 4}],
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Admin Created"


@pytest.mark.asyncio
async def test_admin_can_view_student_detail(
    client: AsyncClient, admin_headers: dict,
):
    """Админ может просмотреть конкретного студента."""
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Admin View Target",
    }, headers=admin_headers)
    assert resp.status_code == 201
    student_id = resp.json()["id"]

    resp = await client.get(f"/api/v1/students/{student_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Admin View Target"


# --- Contact info only via accepted invite ---


@pytest.mark.asyncio
async def test_contacts_require_accepted_invite(
    client: AsyncClient, employer_headers: dict, admin_headers: dict,
):
    """Контакты недоступны без accepted приглашения — 403."""
    resp = await client.post("/api/v1/students/", json={
        "full_name": "Contact Guard",
        "group_name": "GRD-1",
    }, headers=admin_headers)
    assert resp.status_code == 201
    student_id = resp.json()["id"]

    # Без приглашения — 403
    resp = await client.get(
        f"/api/v1/landing/student/{student_id}/contacts",
        headers=employer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_contacts_available_after_accepted_invite(
    client: AsyncClient,
    admin_headers: dict,
    employer_headers: dict,
    student_headers: dict,
):
    """После accepted приглашения контакты доступны с full_name и email."""
    # Получаем ID студента из fixtures
    profile_resp = await client.get("/api/v1/profile/student/", headers=student_headers)
    assert profile_resp.status_code == 200
    student_id = profile_resp.json()["id"]

    # Делаем работодателя партнёром
    me_resp = await client.get("/api/v1/auth/me", headers=employer_headers)
    employer_user_id = me_resp.json()["id"]
    await client.patch(
        f"/api/v1/admin/partnership/employer/{employer_user_id}",
        json={"partnership_status": "partner"},
        headers=admin_headers,
    )

    # Создаём приглашение через landing
    resp = await client.post(
        f"/api/v1/landing/invite/{student_id}",
        headers=employer_headers,
    )
    assert resp.status_code == 200

    # Студент принимает приглашение
    cr_resp = await client.get(
        "/api/v1/profile/student/contact-requests",
        headers=student_headers,
    )
    requests = cr_resp.json()
    assert len(requests) >= 1
    cr_id = requests[0]["id"]

    await client.post(
        f"/api/v1/profile/student/contact-requests/{cr_id}/respond",
        json={"accept": True},
        headers=student_headers,
    )

    # Теперь контакты доступны
    resp = await client.get(
        f"/api/v1/landing/student/{student_id}/contacts",
        headers=employer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "full_name" in data
    assert "email" in data
    assert data["full_name"] == "Test Student"
