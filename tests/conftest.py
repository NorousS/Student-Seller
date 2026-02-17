import pytest
import asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base, get_db
from app.config import settings

# --- Database Setup for Tests ---

# Use a separate test database to avoid messing with production/dev data
# Override settings for tests
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/hh_parser_test"

# Engine for the test database
# Use NullPool to avoid binding connections to a specific event loop, 
# allowing the engine to be used across session-scoped setup and function-scoped tests.
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
test_async_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# Removed event_loop fixture as pytest-asyncio handles loop lifecycle now.


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """
    Create the test database and tables before running tests.
    Drop them afterwards.
    """
    # Create the database itself requires connecting to 'postgres' db
    # and running CREATE DATABASE. This is tricky with async driver in a transaction.
    # Simplified approach: Treat existing DB as test DB or ensure it exists beforehand.
    # Alternatively, create tables in the existing DB but use a prefix or just clean up.
    
    # For CI/CD cleanliness, ideally we create/drop DB.
    # But for this environment, let's assume the user can run this against a test DB they created or we try to create it.
    
    # Let's try to connect to the default 'postgres' database to create 'hh_parser_test'
    default_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    default_engine = create_async_engine(default_db_url, isolation_level="AUTOCOMMIT")
    
    async with default_engine.connect() as conn:
        # Check if database exists
        result = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'hh_parser_test'"))
        if not result.scalar():
            await conn.execute(text("CREATE DATABASE hh_parser_test"))

    await default_engine.dispose()
    
    # Now connect to test DB and create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    
    # Cleanup: Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that returns a SQLAlchemy session with a SAVEPOINT.
    This allows rolling back changes after each test.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        # Ensure expire_on_commit=False to avoid MissingGreenlet error during Pydantic serialization
        session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
        
        yield session
        
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture for async HTTP client that overrides the get_db dependency.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
