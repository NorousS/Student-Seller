from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import require_role
from app.database import get_db
from app.discipline_groups import infer_discipline_group_semantic
from app.models import Student, Discipline, StudentDiscipline, User, UserRole
from app.schemas import StudentCreate, StudentResponse, DisciplineResponse, AddDisciplinesRequest
from app.valuation_cache import refresh_student_valuation

router = APIRouter(
    prefix="/api/v1/students",
    tags=["Students"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


async def get_or_create_discipline(db: AsyncSession, name: str) -> Discipline:
    """
    Helper to find a discipline by name or create it if it doesn't exist.
    """
    stmt = select(Discipline).where(Discipline.name == name)
    result = await db.execute(stmt)
    discipline = result.scalar_one_or_none()
    
    if not discipline:
        try:
            category = await infer_discipline_group_semantic(name)
        except Exception:
            category = "OTHER"
        discipline = Discipline(name=name, category=category)
        db.add(discipline)
        await db.flush()  # We need the ID
        
    return discipline


def build_student_response(student: Student) -> StudentResponse:
    """Построить ответ с оценками из student_disciplines."""
    disciplines = []
    for sd in student.student_disciplines:
        disciplines.append(DisciplineResponse(
            id=sd.discipline.id,
            name=sd.discipline.name,
            grade=sd.grade,
            category=sd.discipline.category,
        ))
    return StudentResponse(
        id=student.id,
        full_name=student.full_name,
        group_name=student.group_name,
        disciplines=disciplines,
    )


@router.get("/", response_model=list[StudentResponse])
async def list_students(db: AsyncSession = Depends(get_db)):
    """Получить список всех студентов."""
    stmt = select(Student).options(
        selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline)
    )
    result = await db.execute(stmt)
    students = result.scalars().all()
    return [build_student_response(s) for s in students]


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(student_in: StudentCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать нового студента с (опционально) списком дисциплин.
    Если дисциплины не существуют, они будут созданы.
    """
    # 1. Создаем студента
    new_student = Student(
        full_name=student_in.full_name,
        group_name=student_in.group_name
    )
    db.add(new_student)
    await db.flush()  # Для получения ID студента

    # 2. Добавляем дисциплины
    if student_in.disciplines:
        for disc in student_in.disciplines:
            discipline = await get_or_create_discipline(db, disc.name)
            link = StudentDiscipline(student_id=new_student.id, discipline_id=discipline.id, grade=disc.grade)
            db.add(link)

    await db.flush()
    await refresh_student_valuation(db, new_student.id)
    await db.commit()
    
    # 3. Возвращаем с подгруженными связями
    stmt = select(Student).options(
        selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline)
    ).where(Student.id == new_student.id)
    result = await db.execute(stmt)
    student_loaded = result.scalar_one()
    
    return build_student_response(student_loaded)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получить профиль студента по ID.
    """
    stmt = select(Student).options(
        selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline)
    ).where(Student.id == student_id)
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    return build_student_response(student)


@router.post("/{student_id}/disciplines", response_model=StudentResponse)
async def add_disciplines_to_student(
    student_id: int, 
    request: AddDisciplinesRequest,
    replace: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Добавить дисциплины существующему студенту.
    """
    # Проверяем студента
    stmt = select(Student).where(Student.id == student_id)
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    incoming_names = {disc.name for disc in request.disciplines}
    if replace:
        existing_stmt = (
            select(StudentDiscipline)
            .join(Discipline, StudentDiscipline.discipline_id == Discipline.id)
            .where(StudentDiscipline.student_id == student_id)
        )
        existing_res = await db.execute(existing_stmt)
        for link in existing_res.scalars().all():
            if link.discipline.name not in incoming_names:
                await db.delete(link)

    # Добавляем дисциплины
    seen_names: set[str] = set()
    for disc in request.disciplines:
        if disc.name in seen_names:
            continue
        seen_names.add(disc.name)
        
        discipline = await get_or_create_discipline(db, disc.name)
        
        # Проверяем существование связи
        link_stmt = select(StudentDiscipline).where(
            StudentDiscipline.student_id == student_id,
            StudentDiscipline.discipline_id == discipline.id
        )
        link_res = await db.execute(link_stmt)
        existing_link = link_res.scalar_one_or_none()
        
        if existing_link:
            # Обновляем оценку если связь уже есть
            existing_link.grade = disc.grade
        else:
            new_link = StudentDiscipline(student_id=student_id, discipline_id=discipline.id, grade=disc.grade)
            db.add(new_link)
            
    await db.flush()
    await refresh_student_valuation(db, student_id)
    db.expire_all()
    
    # Reload and return
    stmt = select(Student).options(
        selectinload(Student.student_disciplines).selectinload(StudentDiscipline.discipline)
    ).where(Student.id == student_id)
    result = await db.execute(stmt)
    student_loaded = result.scalar_one()
    
    return build_student_response(student_loaded)
