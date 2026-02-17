import asyncio
import sys
import os

# Add project root to python path to allow imports from app
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.database import async_session_maker, create_tables
from app.models import Student, Discipline, StudentDiscipline

students_data = [
    {
        "full_name": "Иван Иванов",
        "group_name": "CS-101",
        "disciplines": ["Python", "Algorithms", "Databases", "Linux"]
    },
    {
        "full_name": "Петр Петров",
        "group_name": "DS-202",
        "disciplines": ["Python", "Machine Learning", "Linear Algebra", "Statistics"]
    },
    {
        "full_name": "Анна Сидорова",
        "group_name": "WEB-303",
        "disciplines": ["JavaScript", "React", "HTML/CSS", "Node.js"]
    },
    {
        "full_name": "Мария Кузнецова",
        "group_name": "JAVA-404",
        "disciplines": ["Java", "Spring", "OOP", "PostgreSQL"]
    },
    {
        "full_name": "Алексей Смирнов",
        "group_name": "DEVOPS-505",
        "disciplines": ["Docker", "Kubernetes", "Linux", "Python", "Ansible"]
    }
]

async def seed():
    print("Creating tables...")
    await create_tables()
    
    async with async_session_maker() as session:
        print("Seeding students...")
        
        # 1. Ensure all disciplines exist
        # Collect all unique discipline names
        all_discs_names = set()
        for s in students_data:
            all_discs_names.update(s["disciplines"])
            
        print(f"Found {len(all_discs_names)} unique disciplines.")
        
        disc_map = {} # name -> Discipline object
        
        for name in all_discs_names:
            stmt = select(Discipline).where(Discipline.name == name)
            res = await session.execute(stmt)
            discipline = res.scalar_one_or_none()
            
            if not discipline:
                discipline = Discipline(name=name)
                session.add(discipline)
                await session.flush()
                print(f"Created discipline: {name}")
            else:
                print(f"Discipline exists: {name}")
                
            disc_map[name] = discipline

        # 2. Create students
        for s_data in students_data:
            # Check if student already exists (by name and group mostly for this seed check)
            stmt = select(Student).where(Student.full_name == s_data["full_name"])
            res = await session.execute(stmt)
            existing_student = res.scalar_one_or_none()
            
            if existing_student:
                print(f"Student {s_data['full_name']} already exists. Skipping.")
                continue

            student = Student(
                full_name=s_data["full_name"],
                group_name=s_data["group_name"]
            )
            session.add(student)
            await session.flush() # get ID
            
            print(f"Created student: {student.full_name}")
            
            # 3. Add disciplines
            for d_name in s_data["disciplines"]:
                disc = disc_map[d_name]
                link = StudentDiscipline(student_id=student.id, discipline_id=disc.id)
                session.add(link)
                
        await session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed())
