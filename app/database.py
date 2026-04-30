"""
Подключение к базе данных PostgreSQL.
Использует SQLAlchemy async для асинхронной работы.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Создаём асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Отключаем логирование SQL-запросов в проде
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии БД.
    Используется в FastAPI эндпоинтах через Depends().
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Создаёт все таблицы в БД и применяет safe column migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
<<<<<<< HEAD
        if engine.dialect.name == "postgresql":
            await conn.exec_driver_sql(
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS estimated_salary DOUBLE PRECISION"
            )
            await conn.exec_driver_sql(
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS valuation_updated_at TIMESTAMP"
            )
=======
        # Safe idempotent column additions (ADD COLUMN IF NOT EXISTS ignores existing columns)
        for sql in [
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS estimated_salary DOUBLE PRECISION",
            "ALTER TABLE students ADD COLUMN IF NOT EXISTS valuation_updated_at TIMESTAMP",
        ]:
            await conn.execute(text(sql))
>>>>>>> github/main
