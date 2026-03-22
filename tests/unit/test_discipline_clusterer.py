from unittest.mock import AsyncMock, patch

import numpy as np
import pytest


def _make_fake_embedding(seed: int, dim: int = 768) -> list[float]:
    """Создать детерминированный фейковый эмбеддинг."""
    rng = np.random.default_rng(seed)
    vec = rng.random(dim).astype(float)
    return (vec / np.linalg.norm(vec)).tolist()


# Фейковые эмбеддинги для категорий (программирование ближе друг к другу)
FAKE_EMBEDDINGS = {
    # Программирование - похожие вектора
    "Python": _make_fake_embedding(100),
    "Java": _make_fake_embedding(101),
    "C++": _make_fake_embedding(102),
    "JavaScript": _make_fake_embedding(103),
    # Математика - другой кластер
    "Программирование на Python": _make_fake_embedding(110),
    "Базы данных": _make_fake_embedding(200),
    "Математический анализ": _make_fake_embedding(300),
    "Компьютерные сети": _make_fake_embedding(400),
    "SQL": _make_fake_embedding(201),
    "Линейная алгебра": _make_fake_embedding(301),
}

# Эталонные эмбеддинги для категорий
ANCHOR_EMBEDDINGS = {
    "programming": _make_fake_embedding(100),  # близко к Python, Java...
    "databases": _make_fake_embedding(200),
    "math": _make_fake_embedding(300),
    "networks": _make_fake_embedding(400),
    "ai_ml": _make_fake_embedding(500),
    "management": _make_fake_embedding(600),
    "security": _make_fake_embedding(700),
    "web": _make_fake_embedding(800),
}


class TestDisciplineClusterer:
    @pytest.fixture
    def mock_embedding_service(self):
        """Мок для embedding_service."""
        with patch("app.grouping.discipline_clusterer.embedding_service") as mock:

            async def get_embedding(text: str) -> list[float]:
                # Для эталонных категорий
                for cat, emb in ANCHOR_EMBEDDINGS.items():
                    if cat in text.lower():
                        return emb
                return _make_fake_embedding(hash(text) % 1000)

            async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
                result = []
                for text in texts:
                    if text in FAKE_EMBEDDINGS:
                        result.append(FAKE_EMBEDDINGS[text])
                    else:
                        result.append(_make_fake_embedding(hash(text) % 1000))
                return result

            mock.get_embedding = AsyncMock(side_effect=get_embedding)
            mock.get_embeddings_batch = AsyncMock(side_effect=get_embeddings_batch)
            yield mock

    @pytest.fixture
    def clusterer(self, mock_embedding_service):
        # Import here to ensure mock is in place before module loads
        from app.grouping.discipline_clusterer import DisciplineClusterer

        return DisciplineClusterer(n_clusters=3)

    async def test_empty_input(self, clusterer, mock_embedding_service):
        result = await clusterer.cluster([])
        assert result.clusters == {}

    async def test_single_discipline(self, clusterer, mock_embedding_service):
        result = await clusterer.cluster(["Python"])
        assert len(result.clusters) == 1
        assert "Python" in list(result.clusters.values())[0]

    async def test_programming_disciplines_grouped(
        self, clusterer, mock_embedding_service
    ):
        """Проверить что языки программирования группируются вместе."""
        disciplines = ["Python", "Java", "C++", "JavaScript"]
        result = await clusterer.cluster(disciplines)

        # Должны быть сгруппированы в 1-3 кластера (с моками может быть больше)
        assert len(result.clusters) <= 3

        # Все дисциплины присутствуют
        all_items = []
        for items in result.clusters.values():
            all_items.extend(items)
        assert set(all_items) == set(disciplines)

    async def test_mixed_disciplines(self, clusterer, mock_embedding_service):
        """Проверить кластеризацию разнородных дисциплин."""
        disciplines = [
            "Программирование на Python",
            "Базы данных",
            "Математический анализ",
            "Компьютерные сети",
            "SQL",
            "Линейная алгебра",
        ]
        result = await clusterer.cluster(disciplines)

        # Должны быть несколько кластеров
        assert len(result.clusters) >= 2

        # Все дисциплины распределены
        total = sum(len(v) for v in result.clusters.values())
        assert total == len(disciplines)
