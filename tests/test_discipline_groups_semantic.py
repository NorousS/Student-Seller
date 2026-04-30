from unittest.mock import patch

import pytest

from app import discipline_groups


class MockEmbeddingService:
    def __init__(self):
        self.seed_vectors = {
            "Python": [1, 0, 0, 0],
            "Java": [1, 0, 0, 0],
            "Алгоритмы и структуры данных": [1, 0, 0, 0],
            "Базы данных": [1, 0, 0, 0],
            "ООП": [1, 0, 0, 0],
            "Веб-разработка": [1, 0, 0, 0],
            "Английский язык": [0, 1, 0, 0],
            "Немецкий язык": [0, 1, 0, 0],
            "Французский язык": [0, 1, 0, 0],
            "Иностранный язык": [0, 1, 0, 0],
            "Soft skills в IT": [0, 0, 1, 0],
            "Управление проектами": [0, 0, 1, 0],
            "Lean менеджмент": [0, 0, 1, 0],
            "Коммуникативные навыки": [0, 0, 1, 0],
            "Лидерство": [0, 0, 1, 0],
            "Линейная алгебра": [0, 0, 0, 1],
            "Математический анализ": [0, 0, 0, 1],
            "Математическая статистика": [0, 0, 0, 1],
            "Физика": [0, 0, 0, 1],
            "Дискретная математика": [0, 0, 0, 1],
        }
        self.query_vectors = {
            "Маркетинг": [0, 0, 0, 0],
        }

    async def get_embeddings_batch(self, texts):
        return [self.seed_vectors[text] for text in texts]

    async def get_embedding(self, text):
        return self.seed_vectors.get(text, self.query_vectors.get(text, [0, 0, 0, 0]))


@pytest.mark.asyncio
async def test_semantic_group_exact_sciences():
    discipline_groups._centroids = None
    with patch("app.discipline_groups.EmbeddingService", MockEmbeddingService):
        assert await discipline_groups.infer_discipline_group_semantic("Линейная алгебра") == "EXACT_SCIENCES"


@pytest.mark.asyncio
async def test_semantic_group_foreign_languages():
    discipline_groups._centroids = None
    with patch("app.discipline_groups.EmbeddingService", MockEmbeddingService):
        assert await discipline_groups.infer_discipline_group_semantic("Английский язык") == "FOREIGN_LANGUAGES"


@pytest.mark.asyncio
async def test_semantic_group_other_below_threshold():
    discipline_groups._centroids = None
    with patch("app.discipline_groups.EmbeddingService", MockEmbeddingService):
        assert await discipline_groups.infer_discipline_group_semantic("Маркетинг") == "OTHER"
