"""
Сервис для работы с векторной БД Qdrant.
Хранит эмбеддинги навыков hh.ru и обеспечивает семантический поиск.
"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    QueryResponse,
)

from app.config import settings
from app.embeddings import embedding_service
from app.middleware.external_api_metrics import track_external_api_call


# Имена коллекций
HH_SKILLS_COLLECTION = "hh_skills"


class VectorStore:
    """
    Клиент Qdrant для хранения и поиска эмбеддингов навыков.
    Совместим с qdrant-client >= 1.12.
    """

    def __init__(self):
        self.client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self.dimension = settings.embedding_dimension

    async def init_collections(self) -> None:
        """Создаёт коллекции, если их нет."""
        async with track_external_api_call("qdrant", "get_collections"):
            collections = await self.client.get_collections()
        existing = {c.name for c in collections.collections}

        if HH_SKILLS_COLLECTION not in existing:
            async with track_external_api_call("qdrant", "create_collection"):
                await self.client.create_collection(
                    collection_name=HH_SKILLS_COLLECTION,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                    ),
                )
            print(f"Коллекция '{HH_SKILLS_COLLECTION}' создана")

    async def upsert_skills(self, skills: list[str]) -> int:
        """
        Индексирует навыки hh.ru: генерирует эмбеддинги и сохраняет в Qdrant.
        Использует хэш имени навыка как ID точки для дедупликации.

        Args:
            skills: Список названий навыков

        Returns:
            Количество проиндексированных навыков
        """
        if not skills:
            return 0

        # Фильтруем уже существующие
        new_skills = []
        for skill in skills:
            point_id = self._skill_id(skill)
            async with track_external_api_call("qdrant", "retrieve"):
                points = await self.client.retrieve(
                    collection_name=HH_SKILLS_COLLECTION,
                    ids=[point_id],
                )
            if not points:
                new_skills.append(skill)

        if not new_skills:
            return 0

        # Генерируем эмбеддинги
        embeddings = await embedding_service.get_embeddings_batch(new_skills)

        # Создаём точки
        points = [
            PointStruct(
                id=self._skill_id(skill),
                vector=embedding,
                payload={"name": skill},
            )
            for skill, embedding in zip(new_skills, embeddings)
        ]

        async with track_external_api_call("qdrant", "upsert"):
            await self.client.upsert(
                collection_name=HH_SKILLS_COLLECTION,
                points=points,
            )

        return len(points)

    async def search_similar_skills(
        self,
        text: str,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[dict]:
        """
        Ищет навыки hh.ru, семантически похожие на входной текст.

        Args:
            text: Текст для поиска (например, название дисциплины)
            top_k: Количество результатов
            score_threshold: Минимальный порог сходства

        Returns:
            Список словарей: [{"name": str, "score": float}, ...]
        """
        threshold = score_threshold or settings.similarity_threshold

        # Получаем эмбеддинг запроса
        query_vector = await embedding_service.get_embedding(text)

        # qdrant-client >= 1.12 использует query_points вместо search
        async with track_external_api_call("qdrant", "query_points"):
            response: QueryResponse = await self.client.query_points(
                collection_name=HH_SKILLS_COLLECTION,
                query=query_vector,
                limit=top_k,
                score_threshold=threshold,
            )

        return [
            {"name": hit.payload["name"], "score": hit.score}
            for hit in response.points
        ]

    async def get_skills_count(self) -> int:
        """Возвращает количество навыков в коллекции."""
        async with track_external_api_call("qdrant", "get_collection"):
            info = await self.client.get_collection(HH_SKILLS_COLLECTION)
        return info.points_count

    @staticmethod
    def _skill_id(skill_name: str) -> int:
        """Генерирует детерминированный ID из названия навыка."""
        # Используем положительный хэш, усечённый до 63 бит (Qdrant int64)
        return abs(hash(skill_name)) % (2**63)


# Глобальный экземпляр
vector_store = VectorStore()
