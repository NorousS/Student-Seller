"""
Конфигурация приложения.
Загружает переменные окружения из .env файла.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Подключение к PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/hh_parser"
    
    # Настройки парсера
    default_vacancies_count: int = 50
    
    # Базовый URL API hh.ru
    hh_api_base_url: str = "https://api.hh.ru"
    
    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    
    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768
    
    # Оценка стоимости
    similarity_threshold: float = 0.6
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()
