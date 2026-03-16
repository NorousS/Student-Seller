"""
Сервис генерации эмбеддингов через Ollama API.
Использует модель nomic-embed-text для создания векторных представлений текста.
"""

import re

import httpx

from app.config import settings


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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": normalized_text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Генерирует эмбеддинги для списка текстов.
        Ollama не поддерживает batch нативно, поэтому запросы последовательные.

        Args:
            texts: Список текстов

        Returns:
            Список векторов
        """
        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                normalized_text = normalize_text(text)
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": normalized_text},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
        return embeddings

    async def ensure_model_loaded(self) -> bool:
        """
        Проверяет, что модель загружена в Ollama.
        Если нет — подтягивает (pull).

        Returns:
            True если модель доступна
        """
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Проверяем наличие модели
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]

                if not any(self.model in name for name in model_names):
                    # Модель не найдена — подтягиваем
                    print(f"Модель {self.model} не найдена, загружаем...")
                    pull_response = await client.post(
                        f"{self.base_url}/api/pull",
                        json={"name": self.model},
                    )
                    pull_response.raise_for_status()
                    print(f"Модель {self.model} загружена")

                return True
            except httpx.HTTPError as e:
                print(f"Ошибка подключения к Ollama: {e}")
                return False


# Глобальный экземпляр
embedding_service = EmbeddingService()
