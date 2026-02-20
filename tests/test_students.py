import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Student, Discipline, StudentDiscipline

@pytest.mark.asyncio
async def test_create_student_simple(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Test creating a student without disciplines."""
    response = await client.post("/api/v1/students/", json={
        "full_name": "Test Student",
        "group_name": "TEST-1"
    }, headers=admin_headers)
    
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Test Student"
    assert data["group_name"] == "TEST-1"
    assert "id" in data
    
    # Verify in DB
    student_id = data["id"]
    result = await db_session.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    assert student is not None
    assert student.full_name == "Test Student"

@pytest.mark.asyncio
async def test_create_student_with_disciplines(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Test creating a student with disciplines and grades."""
    response = await client.post("/api/v1/students/", json={
        "full_name": "Student With Skills",
        "disciplines": [
            {"name": "Skill1", "grade": 5},
            {"name": "Skill2", "grade": 4}
        ]
    }, headers=admin_headers)
    
    assert response.status_code == 201
    data = response.json()
    assert len(data["disciplines"]) == 2
    
    disc_map = {d["name"]: d for d in data["disciplines"]}
    assert "Skill1" in disc_map
    assert "Skill2" in disc_map
    assert disc_map["Skill1"]["grade"] == 5
    assert disc_map["Skill2"]["grade"] == 4
    
    # Verify Disciplines exist in DB
    result = await db_session.execute(select(Discipline).where(Discipline.name.in_(["Skill1", "Skill2"])))
    disciplines = result.scalars().all()
    assert len(disciplines) == 2

@pytest.mark.asyncio
async def test_get_student_profile(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Test getting a student profile."""
    # Create manually
    student = Student(full_name="Get Me", group_name="G1")
    db_session.add(student)
    await db_session.commit()
    
    response = await client.get(f"/api/v1/students/{student.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student.id
    assert data["full_name"] == "Get Me"

@pytest.mark.asyncio
async def test_add_disciplines_to_existing_student(client: AsyncClient, db_session: AsyncSession, admin_headers: dict):
    """Test adding disciplines with grades to an existing student."""
    # Create student
    student = Student(full_name="Update Me")
    db_session.add(student)
    await db_session.commit()
    
    # Add disciplines
    response = await client.post(f"/api/v1/students/{student.id}/disciplines", json={
        "disciplines": [
            {"name": "NewSkill", "grade": 5},
            {"name": "OldSkill", "grade": 3}
        ]
    }, headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["disciplines"]) == 2
    
    # Add one more (idempotency check — grade update)
    response = await client.post(f"/api/v1/students/{student.id}/disciplines", json={
        "disciplines": [
            {"name": "NewSkill", "grade": 4},
            {"name": "UniqueSkill", "grade": 5}
        ]
    }, headers=admin_headers)
    
    assert response.status_code == 200
    data = response.json()
    # Should now have 3 unique skills
    assert len(data["disciplines"]) == 3
    disc_map = {d["name"]: d for d in data["disciplines"]}
    assert disc_map["NewSkill"]["grade"] == 4  # Updated
    assert disc_map["UniqueSkill"]["grade"] == 5

@pytest.mark.asyncio
async def test_student_not_found(client: AsyncClient, admin_headers: dict):
    """Test 404 for non-existent student."""
    response = await client.get("/api/v1/students/999999", headers=admin_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_student_default_grade(client: AsyncClient, admin_headers: dict):
    """Test that default grade is 5."""
    response = await client.post("/api/v1/students/", json={
        "full_name": "Default Grade Student",
        "disciplines": [{"name": "Math"}]
    }, headers=admin_headers)
    
    assert response.status_code == 201
    data = response.json()
    assert data["disciplines"][0]["grade"] == 5
