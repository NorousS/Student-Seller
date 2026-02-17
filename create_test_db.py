from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def create_test_db():
    print("Connecting to postgres to check for test DB...")
    # Use default postgres DB to perform administrative tasks
    default_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    engine = create_async_engine(default_db_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        from sqlalchemy import text
        
        # Check if database exists
        result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'hh_parser_test'"))
        exists = result.scalar()
        
        if not exists:
            print("Creating test database 'hh_parser_test'...")
            # Cannot create database inside a transaction block usually, requires autocommit
            await conn.execute(text("CREATE DATABASE hh_parser_test"))
        else:
            print("Test database 'hh_parser_test' already exists.")

    await engine.dispose()

if __name__ == "__main__":
    import asyncio
    import os
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_test_db())
