"""
Tests for semantic discipline grouping (embedding-based).
"""

import math
import pytest
from unittest.mock import AsyncMock, patch

from app.discipline_groups import (
    EXACT_SCIENCES,
    FOREIGN_LANGUAGES,
    OTHER,
    PROGRAMMING,
    SOFT_SKILLS,
    GROUP_SEEDS,
    _cosine_similarity,
    infer_discipline_group,
    infer_discipline_group_semantic,
    reload_centroids,
)


# ─── Unit tests ───────────────────────────────────────────────────────────────

pytestmark = pytest.mark.no_db


def _unit_vec(angle_deg: float) -> list[float]:
    """2D unit vector at given angle — handy for deterministic cosine tests."""
    a = math.radians(angle_deg)
    return [math.cos(a), math.sin(a)]


class TestCosineSimilarity:
    def test_identical(self):
        assert _cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_zero_vector(self):
        assert _cosine_similarity([0, 0], [1, 1]) == 0.0

    def test_opposite(self):
        assert _cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)


class TestKeywordFallback:
    """The synchronous keyword-based grouping should still work after rewrite."""

    def test_python_is_programming(self):
        assert infer_discipline_group("Python") == PROGRAMMING

    def test_english_is_foreign(self):
        assert infer_discipline_group("Английский язык") == FOREIGN_LANGUAGES

    def test_lean_is_soft(self):
        assert infer_discipline_group("Lean менеджмент") == SOFT_SKILLS

    def test_physics_is_exact(self):
        assert infer_discipline_group("Физика") == EXACT_SCIENCES

    def test_unknown_is_other(self):
        assert infer_discipline_group("Ксерокопирование документов") == OTHER


class TestReloadCentroids:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        """reload_centroids() returns True when embeddings succeed."""
        dim = 4
        n_seeds = max(len(v) for v in GROUP_SEEDS.values())

        async def fake_batch(texts):
            return [[1.0] * dim] * len(texts)

        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(side_effect=fake_batch)
            # Reset module-level cache so reload actually runs
            import app.discipline_groups as dg
            dg._centroids = None

            result = await reload_centroids()

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self):
        """reload_centroids() returns False when embedding service is unavailable."""
        import app.discipline_groups as dg
        dg._centroids = None

        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(side_effect=Exception("Ollama down"))
            result = await reload_centroids()

        assert result is False


class TestSemanticInference:
    """Deterministic tests using mocked embeddings."""

    @pytest.mark.asyncio
    async def test_programming_discipline(self):
        """A discipline whose embedding is closest to the PROGRAMMING centroid."""
        import app.discipline_groups as dg

        # Set up fake centroids: each group lives on a different axis.
        dg._centroids = {
            PROGRAMMING:       [1, 0, 0, 0],
            FOREIGN_LANGUAGES: [0, 1, 0, 0],
            SOFT_SKILLS:       [0, 0, 1, 0],
            EXACT_SCIENCES:    [0, 0, 0, 1],
        }

        # Discipline embedding close to PROGRAMMING (sim=0.99 >> 0.5)
        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embedding = AsyncMock(return_value=[0.99, 0.01, 0.01, 0.01])
            result = await infer_discipline_group_semantic("Алгоритмы и структуры данных")

        assert result == PROGRAMMING

    @pytest.mark.asyncio
    async def test_foreign_language_discipline(self):
        import app.discipline_groups as dg

        dg._centroids = {
            PROGRAMMING:       [1, 0, 0, 0],
            FOREIGN_LANGUAGES: [0, 1, 0, 0],
            SOFT_SKILLS:       [0, 0, 1, 0],
            EXACT_SCIENCES:    [0, 0, 0, 1],
        }

        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embedding = AsyncMock(return_value=[0.01, 0.99, 0.01, 0.01])
            result = await infer_discipline_group_semantic("Английский язык")

        assert result == FOREIGN_LANGUAGES

    @pytest.mark.asyncio
    async def test_below_threshold_returns_other(self):
        """When best similarity < 0.50, result must be OTHER."""
        import app.discipline_groups as dg

        dg._centroids = {
            PROGRAMMING: [1, 0],
            FOREIGN_LANGUAGES: [0, 1],
        }

        # Embedding perfectly orthogonal to both centroids (edge of 2D space)
        # Use [1/√2, 1/√2] → sim to [1,0] = 0.707 — hmm, this would match.
        # Instead, send a zero-length-ish vector that causes low sim:
        # Actually use a 3-component vector while centroids are 2D → zip cuts off at 2
        # Better approach: use a centroid that deliberately gives low similarity.
        dg._centroids = {
            PROGRAMMING: [1, 0, 0],
        }
        # Embedding [0, 0, 1] is orthogonal → sim = 0.0 < 0.50
        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embedding = AsyncMock(return_value=[0.0, 0.0, 1.0])
            result = await infer_discipline_group_semantic("Маркетинг и продажи")

        assert result == OTHER

    @pytest.mark.asyncio
    async def test_ollama_unavailable_uses_keyword_fallback(self):
        """When embedding service is down, falls back to keyword grouping."""
        import app.discipline_groups as dg

        dg._centroids = {PROGRAMMING: [1, 0]}

        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embedding = AsyncMock(side_effect=Exception("Connection refused"))
            result = await infer_discipline_group_semantic("Python")

        # keyword fallback: Python → PROGRAMMING
        assert result == PROGRAMMING

    @pytest.mark.asyncio
    async def test_no_centroids_uses_keyword_fallback(self):
        """When centroids are not loaded at all, falls back to keyword grouping."""
        import app.discipline_groups as dg

        dg._centroids = None

        # Patch reload_centroids to do nothing (no Ollama) and get_embedding to fail
        with patch("app.embeddings.embedding_service") as mock_svc:
            mock_svc.get_embeddings_batch = AsyncMock(side_effect=Exception("offline"))
            mock_svc.get_embedding = AsyncMock(side_effect=Exception("offline"))
            result = await infer_discipline_group_semantic("Английский язык")

        assert result == FOREIGN_LANGUAGES  # keyword fallback
