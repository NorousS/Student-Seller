"""
Кластеризация дисциплин студента в группы компетенций.
Использует эмбеддинги и иерархическую кластеризацию.
"""
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from app.embeddings import embedding_service


# Предопределённые метки категорий для именования кластеров
CATEGORY_LABELS = {
    "programming": "Языки программирования",
    "databases": "Базы данных",
    "math": "Математика",
    "networks": "Сети и системы",
    "ai_ml": "Искусственный интеллект",
    "management": "Менеджмент",
    "security": "Информационная безопасность",
    "web": "Веб-разработка",
    "other": "Другое",
}

# Эталонные фразы для определения категории кластера
CATEGORY_ANCHORS = {
    "programming": ["программирование", "языки программирования", "Python Java C++"],
    "databases": ["базы данных", "SQL PostgreSQL", "СУБД"],
    "math": ["математика", "алгебра", "анализ", "статистика"],
    "networks": ["компьютерные сети", "операционные системы", "Linux"],
    "ai_ml": ["машинное обучение", "искусственный интеллект", "нейронные сети"],
    "management": ["менеджмент", "управление проектами"],
    "security": ["информационная безопасность", "криптография"],
    "web": ["веб-разработка", "HTML CSS JavaScript"],
}


@dataclass
class ClusterResult:
    """Результат кластеризации."""

    clusters: dict[str, list[str]]  # category_name -> list of disciplines
    embeddings: dict[str, list[float]]  # discipline -> embedding


class DisciplineClusterer:
    """Кластеризует дисциплины студента в смысловые группы."""

    def __init__(self, n_clusters: int = 5, min_cluster_size: int = 2):
        self.n_clusters = n_clusters
        self.min_cluster_size = min_cluster_size
        self._anchor_embeddings: dict[str, list[float]] | None = None

    async def _get_anchor_embeddings(self) -> dict[str, list[float]]:
        """Получить эмбеддинги эталонных категорий."""
        if self._anchor_embeddings is None:
            self._anchor_embeddings = {}
            for category, anchors in CATEGORY_ANCHORS.items():
                combined = " ".join(anchors)
                emb = await embedding_service.get_embedding(combined)
                self._anchor_embeddings[category] = emb
        return self._anchor_embeddings

    def _find_best_category(
        self,
        cluster_embeddings: list[list[float]],
        anchor_embeddings: dict[str, list[float]],
    ) -> str:
        """Найти лучшую категорию для кластера по центроиду."""
        centroid = np.mean(cluster_embeddings, axis=0).reshape(1, -1)

        best_category = "other"
        best_score = -1.0

        for category, anchor_emb in anchor_embeddings.items():
            score = cosine_similarity(centroid, [anchor_emb])[0][0]
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    async def cluster(self, disciplines: list[str]) -> ClusterResult:
        """
        Кластеризовать дисциплины в группы.

        Args:
            disciplines: Список названий дисциплин

        Returns:
            ClusterResult с группами и эмбеддингами
        """
        if len(disciplines) == 0:
            return ClusterResult(clusters={}, embeddings={})

        if len(disciplines) == 1:
            return ClusterResult(clusters={"Другое": disciplines}, embeddings={})

        # Получить эмбеддинги дисциплин
        embeddings_list = await embedding_service.get_embeddings_batch(disciplines)
        disc_embeddings = dict(zip(disciplines, embeddings_list))

        # Получить эмбеддинги эталонов
        anchor_embeddings = await self._get_anchor_embeddings()

        # Определить количество кластеров
        n_clusters = min(self.n_clusters, len(disciplines))

        if n_clusters < 2:
            # Все в один кластер
            category = self._find_best_category(embeddings_list, anchor_embeddings)
            return ClusterResult(
                clusters={CATEGORY_LABELS.get(category, "Другое"): disciplines},
                embeddings=disc_embeddings,
            )

        # Иерархическая кластеризация
        X = np.array(embeddings_list)
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters, metric="cosine", linkage="average"
        )
        labels = clustering.fit_predict(X)

        # Группировка по кластерам
        cluster_groups: dict[int, list[tuple[str, list[float]]]] = {}
        for disc, emb, label in zip(disciplines, embeddings_list, labels):
            cluster_groups.setdefault(label, []).append((disc, emb))

        # Присвоение имён категорий кластерам
        used_categories: set[str] = set()
        result_clusters: dict[str, list[str]] = {}

        for label, items in cluster_groups.items():
            disc_names = [item[0] for item in items]
            cluster_embs = [item[1] for item in items]

            category = self._find_best_category(cluster_embs, anchor_embeddings)

            # Избегаем дублирования имён
            base_name = CATEGORY_LABELS.get(category, "Другое")
            name = base_name
            counter = 2
            while name in used_categories:
                name = f"{base_name} {counter}"
                counter += 1
            used_categories.add(name)

            result_clusters[name] = disc_names

        return ClusterResult(clusters=result_clusters, embeddings=disc_embeddings)
