"""
Тесты категоризации дисциплин через LLM-эмбеддинги.
"""

import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Discipline
from app.categorization import DEFAULT_CATEGORIES, FALLBACK_CATEGORY, categorize_disciplines, _cosine_similarity
from app.discipline_groups import (
    EXACT_SCIENCES,
    FOREIGN_LANGUAGES,
    PROGRAMMING,
    SOFT_SKILLS,
    infer_discipline_group,
)


# --- Unit tests ---


class TestCosineSimilarity:
    pytestmark = pytest.mark.no_db

    def test_identical_vectors(self):
        assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0


class TestCategorizeDisciplines:
    pytestmark = pytest.mark.no_db

    @pytest.mark.asyncio
    async def test_empty_list(self):
        result = await categorize_disciplines([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_ollama_unavailable_fallback(self):
        """При недоступности Ollama возвращается категория-заглушка."""
        with patch("app.categorization.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(side_effect=Exception("Connection refused"))
            result = await categorize_disciplines(["Тестовая дисциплина"])
            assert result == {"Тестовая дисциплина": FALLBACK_CATEGORY}

    @pytest.mark.asyncio
    async def test_keyword_rules_match_required_groups(self):
        """Базовые учебные дисциплины группируются без обращения к Ollama."""
        examples = {
            "Python": PROGRAMMING,
            "Java": PROGRAMMING,
            "Алгоритмы и структуры данных": PROGRAMMING,
            "Английский": FOREIGN_LANGUAGES,
            "Немецкий": FOREIGN_LANGUAGES,
            "Soft skills в IT": SOFT_SKILLS,
            "Lean менеджмент": SOFT_SKILLS,
            "Основы психологии": SOFT_SKILLS,
            "Управление IT проектами": SOFT_SKILLS,
            "Информатика": EXACT_SCIENCES,
            "Основы вычислительной техники": EXACT_SCIENCES,
            "Линал": EXACT_SCIENCES,
            "Матан": EXACT_SCIENCES,
            "Матстат": EXACT_SCIENCES,
            "Физика": EXACT_SCIENCES,
        }

        with patch("app.categorization.embedding_service") as mock_svc:
            result = await categorize_disciplines(list(examples))
            mock_svc.get_embeddings_batch.assert_not_called()
            assert result == examples

        for name, category in examples.items():
            assert infer_discipline_group(name) == category

    @pytest.mark.asyncio
    async def test_embedding_fallback_for_unknown_default_category(self):
        """Неизвестные дисциплины можно докатегоризировать embeddings fallback."""
        with patch("app.categorization.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(
                side_effect=[
                    [[1, 0, 0]] * len(DEFAULT_CATEGORIES),
                    [[0.9, 0.1, 0]],
                ]
            )
            result = await categorize_disciplines(["Неизвестная кафедральная практика"])
            assert result == {"Неизвестная кафедральная практика": DEFAULT_CATEGORIES[0]}

    @pytest.mark.asyncio
    async def test_picks_best_category(self):
        """Выбирает категорию с наибольшим косинусным сходством."""
        # Эмбеддинги: 3-мерные для простоты
        cat_embeddings = [
            [1, 0, 0],  # "Программирование"
            [0, 1, 0],  # "Математика"
        ]
        disc_embeddings = [
            [0.9, 0.1, 0],  # ближе к "Программирование"
        ]

        with patch("app.categorization.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(
                side_effect=[cat_embeddings, disc_embeddings]
            )
            result = await categorize_disciplines(
                ["Python разработка"],
                categories=["Программирование", "Математика"],
            )
            assert result["Python разработка"] == "Программирование"


# --- Integration tests (endpoint) ---


class TestCategorizeEndpoint:
    @pytest.mark.asyncio
    async def test_requires_admin(self, client: AsyncClient, student_headers: dict):
        """Эндпоинт доступен только администратору."""
        resp = await client.post(
            "/api/v1/admin/disciplines/categorize",
            json={},
            headers=student_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_no_disciplines_returns_zero(self, client: AsyncClient, admin_headers: dict):
        """Если нет дисциплин без категории — updated_count=0."""
        resp = await client.post(
            "/api/v1/admin/disciplines/categorize",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 0
        assert data["mapping"] == {}

    @pytest.mark.asyncio
    async def test_categorize_saves_to_db(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Категоризация сохраняет категорию в БД."""
        # Создаём дисциплину без категории
        disc = Discipline(name="Алгоритмы и структуры данных")
        db_session.add(disc)
        await db_session.flush()
        disc_id = disc.id

        cat_embeddings = [[1, 0, 0]] * len(DEFAULT_CATEGORIES)
        # Первая категория — "Программирование", делаем дисциплину ближе к ней
        disc_embeddings = [[0.95, 0.05, 0]]

        with patch("app.categorization.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(
                side_effect=[cat_embeddings, disc_embeddings]
            )
            resp = await client.post(
                "/api/v1/admin/disciplines/categorize",
                json={"discipline_ids": [disc_id]},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 1
        assert "Алгоритмы и структуры данных" in data["mapping"]

        # Проверяем что категория сохранена в БД
        result = await db_session.execute(select(Discipline).where(Discipline.id == disc_id))
        saved = result.scalar_one()
        assert saved.category is not None

    @pytest.mark.asyncio
    async def test_categorize_only_uncategorized(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """Без discipline_ids категоризируются только дисциплины без категории."""
        # Дисциплина с категорией — не должна попасть
        disc_with = Discipline(name="Уже категоризирована", category="Математика")
        # Дисциплина без категории — должна попасть
        disc_without = Discipline(name="Базы данных SQL")
        db_session.add_all([disc_with, disc_without])
        await db_session.flush()

        cat_embeddings = [[1, 0, 0]] * len(DEFAULT_CATEGORIES)
        disc_embeddings = [[0.8, 0.2, 0]]

        with patch("app.categorization.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(
                side_effect=[cat_embeddings, disc_embeddings]
            )
            resp = await client.post(
                "/api/v1/admin/disciplines/categorize",
                json={},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 1
        assert "Базы данных SQL" in data["mapping"]
        assert "Уже категоризирована" not in data["mapping"]

    @pytest.mark.asyncio
    async def test_categorize_ollama_fallback(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """При недоступности Ollama дисциплины получают категорию-заглушку."""
        disc = Discipline(name="Тестовая дисциплина")
        db_session.add(disc)
        await db_session.flush()
        disc_id = disc.id

        with patch("app.categorization.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            resp = await client.post(
                "/api/v1/admin/disciplines/categorize",
                json={"discipline_ids": [disc_id]},
                headers=admin_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_count"] == 1
        assert data["mapping"]["Тестовая дисциплина"] == FALLBACK_CATEGORY
