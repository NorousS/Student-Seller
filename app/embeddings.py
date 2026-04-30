"""
Сервис генерации эмбеддингов через Ollama API.
Использует модель nomic-embed-text для создания векторных представлений текста.
"""

import re

import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def normalize_text(text: str) -> str:
    """
    Нормализует текст перед генерацией эмбеддинга:
    - trim (удаление пробелов по краям)
    - collapse multiple spaces (схлопывание множественных пробелов)
    - lowercase (приведение к нижнему регистру)

    Args:
        text: Входной текст

    Returns:
        Нормализованный текст
    """
    normalized = text.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.lower()
    return normalized


class EmbeddingService:
    """
    Обёртка над Ollama API для генерации эмбеддингов.
    nomic-embed-text поддерживает русский язык, размерность 768.
    """

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

    async def get_embedding(self, text: str) -> list[float]:
        """
        Генерирует эмбеддинг для одного текста.

        Args:
            text: Входной текст (название навыка или дисциплины)

        Returns:
            Вектор размерности 768
        """
        normalized_text = normalize_text(text)
        logger.debug(
            "Генерация эмбеддинга: старт",
            model=self.model,
            text_len=len(normalized_text),
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": normalized_text},
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["embedding"]
            except httpx.HTTPError as e:
                logger.warning(
                    "Генерация эмбеддинга: ошибка",
                    model=self.model,
                    text_len=len(normalized_text),
                    error=str(e),
                    exc_info=True,
                )
                raise

        logger.debug(
            "Генерация эмбеддинга: успешно",
            model=self.model,
            vector_dim=len(embedding),
        )
        return embedding

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Генерирует эмбеддинги для списка текстов.
        Ollama не поддерживает batch нативно, поэтому запросы последовательные.

        Args:
            texts: Список текстов

        Returns:
            Список векторов
        """
        if not texts:
            logger.debug("Пакетная генерация эмбеддингов: пустой список")
            return []

        logger.info(
            "Пакетная генерация эмбеддингов: старт",
            model=self.model,
            items_count=len(texts),
        )
        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for index, text in enumerate(texts):
                normalized_text = normalize_text(text)
                try:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model, "prompt": normalized_text},
                    )
                    response.raise_for_status()
                    data = response.json()
                    embeddings.append(data["embedding"])
                except httpx.HTTPError as e:
                    logger.warning(
                        "Пакетная генерация эмбеддингов: ошибка",
                        model=self.model,
                        item_index=index,
                        items_count=len(texts),
                        text_len=len(normalized_text),
                        error=str(e),
                        exc_info=True,
                    )
                    raise

        logger.info(
            "Пакетная генерация эмбеддингов: успешно",
            model=self.model,
            items_count=len(texts),
        )
        return embeddings

    async def ensure_model_loaded(self) -> bool:
        """
        Проверяет, что модель загружена в Ollama.
        Если нет — подтягивает (pull).

        Returns:
            True если модель доступна
        """
        logger.info("Проверка модели эмбеддингов: старт", model=self.model)
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Проверяем наличие модели
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                if not any(self.model in name for name in model_names):
                    # Модель не найдена — подтягиваем
                    logger.info(
                        "Модель эмбеддингов не найдена, запускаем pull",
                        model=self.model,
                    )
                    pull_response = await client.post(
                        f"{self.base_url}/api/pull",
                        json={"name": self.model},
                    )
                    pull_response.raise_for_status()
                    logger.info("Pull модели эмбеддингов завершён", model=self.model)

                logger.info("Проверка модели эмбеддингов: успешно", model=self.model)
                return True
            except httpx.HTTPError as e:
                logger.warning(
                    "Проверка модели эмбеддингов: ошибка",
                    model=self.model,
                    error=str(e),
                    exc_info=True,
                )
                return False


# Глобальный экземпляр
embedding_service = EmbeddingService()
