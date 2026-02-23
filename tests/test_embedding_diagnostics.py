"""
Тесты для модуля диагностики аномалий similarity.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.embedding_diagnostics import (
    detect_anomalies,
    detect_duplicate_embeddings,
    _normalize_term,
    _cosine_similarity,
    ANOMALY_THRESHOLD,
    MAX_INPUT_TERMS,
)


# --- Тесты утилит ---


def test_normalize_term():
    """Тест нормализации терминов."""
    assert _normalize_term("Python") == "python"
    assert _normalize_term("  Java  ") == "java"
    assert _normalize_term("JavaScript") == "javascript"
    assert _normalize_term("  C++  ") == "c++"


def test_cosine_similarity_identical():
    """Тест косинусного сходства для идентичных векторов."""
    vec = [1.0, 2.0, 3.0]
    similarity = _cosine_similarity(vec, vec)
    assert similarity == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_orthogonal():
    """Тест косинусного сходства для ортогональных векторов."""
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.0, 1.0, 0.0]
    similarity = _cosine_similarity(vec_a, vec_b)
    assert similarity == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_opposite():
    """Тест косинусного сходства для противоположных векторов."""
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [-1.0, 0.0, 0.0]
    # Косинус противоположных векторов = -1, но мы ограничиваем до [0, 1]
    similarity = _cosine_similarity(vec_a, vec_b)
    assert similarity == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_zero_vector():
    """Тест косинусного сходства с нулевым вектором."""
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [0.0, 0.0, 0.0]
    similarity = _cosine_similarity(vec_a, vec_b)
    assert similarity == 0.0


# --- Тесты detect_anomalies ---


@pytest.mark.asyncio
async def test_detect_anomalies_empty_list():
    """Тест с пустым списком терминов."""
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        with pytest.raises(ValueError, match="не может быть пустым"):
            await detect_anomalies([])


@pytest.mark.asyncio
async def test_detect_anomalies_single_term():
    """Тест с одним термином (невозможно создать пары)."""
    # После дедупликации останется один термин
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        mock_service.get_embeddings_batch = AsyncMock(return_value=[[0.1] * 384])
        # Это должно пройти, но detect_anomalies не выдаст ошибку если есть хотя бы один термин
        # Фактически, с одним термином будет 0 пар, что валидно
        result = await detect_anomalies(["Python"])
        assert result.total_terms == 1
        assert result.total_pairs == 0
        assert len(result.anomalies) == 0


@pytest.mark.asyncio
async def test_detect_anomalies_too_many_terms():
    """Тест с превышением лимита терминов."""
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        terms = [f"term_{i}" for i in range(MAX_INPUT_TERMS + 1)]
        with pytest.raises(ValueError, match="превышает лимит"):
            await detect_anomalies(terms)


@pytest.mark.asyncio
async def test_detect_anomalies_duplicates_excluded():
    """Тест что дубликаты исключаются из аномалий."""
    # Два одинаковых термина не должны создать аномалию
    terms = ["Python", "python", "Java"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Мокаем эмбеддинги: после дедупликации останется Python и Java
        # Python и Java имеют разные эмбеддинги
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,  # Python
            [0.0, 1.0] + [0.0] * 382,  # Java
        ])
        
        result = await detect_anomalies(terms, threshold=0.95)
        
        # Проверяем что дубликат не попал в аномалии
        for anomaly in result.anomalies:
            assert anomaly.term_a.lower() != anomaly.term_b.lower()


@pytest.mark.asyncio
async def test_detect_anomalies_basic():
    """Базовый тест диагностики с мокнутыми эмбеддингами."""
    terms = ["Python", "JavaScript", "Java"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Создаем три ортогональных вектора (низкое сходство)
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,  # Python
            [0.0, 1.0] + [0.0] * 382,  # JavaScript
            [0.0, 0.0, 1.0] + [0.0] * 381,  # Java
        ])
        
        result = await detect_anomalies(terms, threshold=0.99)
        
        assert result.total_terms == 3
        assert result.total_pairs == 3  # C(3, 2) = 3
        assert result.threshold_used == 0.99
        assert 0.0 <= result.max_similarity <= 1.0
        
        # С ортогональными векторами не должно быть аномалий
        assert isinstance(result.anomalies, list)
        assert len(result.anomalies) == 0


@pytest.mark.asyncio
async def test_detect_anomalies_custom_threshold():
    """Тест с пользовательским порогом."""
    terms = ["Python", "Django", "Flask"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Создаем векторы с высоким сходством (>0.7) между Django и Flask
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,  # Python
            [0.0, 0.8, 0.6] + [0.0] * 381,  # Django
            [0.0, 0.6, 0.8] + [0.0] * 381,  # Flask (высокое сходство с Django)
        ])
        
        result = await detect_anomalies(terms, threshold=0.7)
        
        assert result.threshold_used == 0.7
        # При низком пороге должны появиться аномалии (Django-Flask)
        assert len(result.anomalies) >= 1
        for anomaly in result.anomalies:
            assert anomaly.similarity >= 0.7


@pytest.mark.asyncio
async def test_detect_anomalies_structure():
    """Тест структуры результата."""
    terms = ["Python", "Java"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Создаем два вектора с очень высоким сходством для создания аномалии
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0, 0.1] + [0.0] * 382,  # Python
            [0.99, 0.15] + [0.0] * 382,  # Java (очень похоже на Python)
        ])
        
        result = await detect_anomalies(terms)
        
        # Проверяем поля результата
        assert hasattr(result, 'total_terms')
        assert hasattr(result, 'total_pairs')
        assert hasattr(result, 'anomalies')
        assert hasattr(result, 'max_similarity')
        assert hasattr(result, 'threshold_used')
        
        # Должна быть как минимум одна аномалия
        assert len(result.anomalies) >= 1
        
        # Проверяем структуру аномалий
        for anomaly in result.anomalies:
            assert hasattr(anomaly, 'term_a')
            assert hasattr(anomaly, 'term_b')
            assert hasattr(anomaly, 'similarity')
            assert hasattr(anomaly, 'reason')
            assert 0.0 <= anomaly.similarity <= 1.0


# --- Тесты detect_duplicate_embeddings ---


@pytest.mark.asyncio
async def test_detect_duplicate_embeddings():
    """Тест поиска дубликатов эмбеддингов."""
    terms = ["Python", "python", "Java"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # После дедупликации останется Python и Java
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,  # Python
            [0.0, 1.0] + [0.0] * 382,  # Java
        ])
        
        result = await detect_duplicate_embeddings(terms)
        
        # Порог должен быть установлен на 1.0
        assert result.threshold_used == 1.0
        
        # Дубликаты (идентичные термины) не должны попасть в результат
        for anomaly in result.anomalies:
            assert anomaly.term_a.lower() != anomaly.term_b.lower()


@pytest.mark.asyncio
async def test_detect_duplicate_embeddings_distinct_terms():
    """Тест что разные термины обычно не имеют идентичных эмбеддингов."""
    terms = ["Python", "Java", "JavaScript", "C++", "Ruby"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Создаем пять разных векторов (без полных дубликатов)
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,
            [0.0, 1.0] + [0.0] * 382,
            [0.0, 0.0, 1.0] + [0.0] * 381,
            [0.0, 0.0, 0.0, 1.0] + [0.0] * 380,
            [0.0, 0.0, 0.0, 0.0, 1.0] + [0.0] * 379,
        ])
        
        result = await detect_duplicate_embeddings(terms)
        
        # Обычно разные термины не должны иметь similarity = 1.0
        assert isinstance(result.anomalies, list)
        # Количество аномалий должно быть 0 (нет полных совпадений)
        assert len(result.anomalies) == 0


# --- Тесты граничных случаев ---


@pytest.mark.asyncio
async def test_detect_anomalies_whitespace_only():
    """Тест с терминами содержащими только пробелы."""
    terms = ["   ", "Python"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # После нормализации пробелы становятся пустой строкой, но оба термина остаются
        # Так как нормализация не фильтрует пустые строки, будет два термина: "" и "python"
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,  # пустая строка
            [0.0, 1.0] + [0.0] * 382,  # Python
        ])
        
        result = await detect_anomalies(terms)
        assert result.total_terms == 2
        assert result.total_pairs == 1


@pytest.mark.asyncio
async def test_detect_anomalies_max_terms_boundary():
    """Тест с граничным количеством терминов."""
    terms = [f"term_{i}" for i in range(MAX_INPUT_TERMS)]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Создаем уникальные ортогональные векторы для каждого термина
        embeddings = []
        for i in range(MAX_INPUT_TERMS):
            vec = [0.0] * 384
            vec[i % 384] = 1.0
            embeddings.append(vec)
        
        mock_service.get_embeddings_batch = AsyncMock(return_value=embeddings)
        
        result = await detect_anomalies(terms, threshold=0.99)
        
        assert result.total_terms <= MAX_INPUT_TERMS
        expected_pairs = MAX_INPUT_TERMS * (MAX_INPUT_TERMS - 1) // 2
        # Может быть меньше из-за дедупликации
        assert result.total_pairs <= expected_pairs


@pytest.mark.asyncio
async def test_detect_anomalies_special_characters():
    """Тест с терминами содержащими специальные символы."""
    terms = ["C++", "C#", ".NET", "Node.js"]
    
    with patch('app.embedding_diagnostics.embedding_service') as mock_service:
        # Создаем четыре разных вектора
        mock_service.get_embeddings_batch = AsyncMock(return_value=[
            [1.0] + [0.0] * 383,
            [0.0, 1.0] + [0.0] * 382,
            [0.0, 0.0, 1.0] + [0.0] * 381,
            [0.0, 0.0, 0.0, 1.0] + [0.0] * 380,
        ])
        
        result = await detect_anomalies(terms)
        
        assert result.total_terms == 4
        # Специальные символы не должны ломать обработку
        for anomaly in result.anomalies:
            assert anomaly.term_a in terms
            assert anomaly.term_b in terms
