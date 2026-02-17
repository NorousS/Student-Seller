import asyncio
from sqlalchemy import select, func
from app.database import async_session_maker
from app.models import Vacancy

async def check_db():
    async with async_session_maker() as session:
        # Проверяем количество вакансий
        result = await session.execute(select(func.count(Vacancy.id)))
        count = result.scalar()
        print(f"Total vacancies in DB: {count}")

        if count > 0:
            # Выводим первые 5 для примера
            result = await session.execute(select(Vacancy).limit(5))
            vacancies = result.scalars().all()
            for v in vacancies:
                print(f"ID: {v.id}, Title: {v.title}, HH ID: {v.hh_id}, Search Query: '{v.search_query}'")

if __name__ == "__main__":
    asyncio.run(check_db())
