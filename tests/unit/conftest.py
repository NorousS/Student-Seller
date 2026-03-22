# Пустой conftest для unit-тестов - переопределяем autouse fixture
import pytest


@pytest.fixture(scope="function", autouse=True)
async def setup_test_db():
    """Переопределяем setup_test_db из родительского conftest, чтобы не подключаться к БД."""
    yield
