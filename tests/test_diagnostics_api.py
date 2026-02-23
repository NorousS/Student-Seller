"""
Интеграционные тесты для API диагностики аномалий.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.models import User


@pytest.mark.asyncio
async def test_similarity_anomalies_unauthorized(client: AsyncClient):
    """Тест доступа без аутентификации."""
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": ["Python", "Java"]},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_similarity_anomalies_forbidden_non_admin(
    client: AsyncClient,
    student_token: str,
):
    """Тест доступа для не-администратора."""
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": ["Python", "Java"]},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_similarity_anomalies_success(
    client: AsyncClient,
    admin_token: str,
):
    """Тест успешной диагностики администратором."""
    with patch('app.routers.diagnostics.detect_anomalies') as mock_detect:
        # Мокаем результат диагностики
        from app.embedding_diagnostics import DiagnosticsResult, SimilarityAnomaly
        
        mock_detect.return_value = DiagnosticsResult(
            total_terms=4,
            total_pairs=6,
            anomalies=[
                SimilarityAnomaly(
                    term_a="Python",
                    term_b="Ruby",
                    similarity=0.96,
                    reason="Подозрительно высокое сходство (similarity=0.9600, порог=0.95)"
                )
            ],
            max_similarity=0.96,
            threshold_used=0.95,
        )
        
        response = await client.post(
            "/api/v1/diagnostics/similarity-anomalies",
            json={
                "terms": ["Python", "JavaScript", "Java", "Ruby"],
                "threshold": 0.95,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "total_terms" in data
        assert "total_pairs" in data
        assert "anomalies" in data
        assert "max_similarity" in data
        assert "threshold_used" in data
        
        assert data["threshold_used"] == 0.95
        assert data["total_terms"] == 4
        assert data["total_pairs"] == 6
        assert isinstance(data["anomalies"], list)
        assert len(data["anomalies"]) == 1
        
        # Проверяем структуру аномалий
        for anomaly in data["anomalies"]:
            assert "term_a" in anomaly
            assert "term_b" in anomaly
            assert "similarity" in anomaly
            assert "reason" in anomaly
            assert 0.0 <= anomaly["similarity"] <= 1.0


@pytest.mark.asyncio
async def test_similarity_anomalies_default_threshold(
    client: AsyncClient,
    admin_token: str,
):
    """Тест с порогом по умолчанию."""
    with patch('app.routers.diagnostics.detect_anomalies') as mock_detect:
        from app.embedding_diagnostics import DiagnosticsResult
        
        mock_detect.return_value = DiagnosticsResult(
            total_terms=3,
            total_pairs=3,
            anomalies=[],
            max_similarity=0.85,
            threshold_used=0.99,
        )
        
        response = await client.post(
            "/api/v1/diagnostics/similarity-anomalies",
            json={"terms": ["Python", "Django", "Flask"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        # По умолчанию порог должен быть 0.99
        assert data["threshold_used"] == 0.99


@pytest.mark.asyncio
async def test_similarity_anomalies_validation_too_few_terms(
    client: AsyncClient,
    admin_token: str,
):
    """Тест валидации: слишком мало терминов."""
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": ["Python"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_similarity_anomalies_validation_too_many_terms(
    client: AsyncClient,
    admin_token: str,
):
    """Тест валидации: слишком много терминов."""
    terms = [f"term_{i}" for i in range(101)]
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": terms},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_similarity_anomalies_validation_empty_terms(
    client: AsyncClient,
    admin_token: str,
):
    """Тест валидации: пустые термины."""
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": ["Python", "   ", "Java"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    assert "пустые термины" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_similarity_anomalies_validation_threshold_too_low(
    client: AsyncClient,
    admin_token: str,
):
    """Тест валидации: слишком низкий порог."""
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": ["Python", "Java"], "threshold": 0.5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_similarity_anomalies_validation_threshold_too_high(
    client: AsyncClient,
    admin_token: str,
):
    """Тест валидации: слишком высокий порог."""
    response = await client.post(
        "/api/v1/diagnostics/similarity-anomalies",
        json={"terms": ["Python", "Java"], "threshold": 1.1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_similarity_anomalies_special_characters(
    client: AsyncClient,
    admin_token: str,
):
    """Тест с терминами содержащими специальные символы."""
    with patch('app.routers.diagnostics.detect_anomalies') as mock_detect:
        from app.embedding_diagnostics import DiagnosticsResult
        
        mock_detect.return_value = DiagnosticsResult(
            total_terms=5,
            total_pairs=10,
            anomalies=[],
            max_similarity=0.80,
            threshold_used=0.95,
        )
        
        response = await client.post(
            "/api/v1/diagnostics/similarity-anomalies",
            json={
                "terms": ["C++", "C#", ".NET", "Node.js", "Vue.js"],
                "threshold": 0.95,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_terms"] == 5


@pytest.mark.asyncio
async def test_similarity_anomalies_cyrillic(
    client: AsyncClient,
    admin_token: str,
):
    """Тест с кириллицей."""
    with patch('app.routers.diagnostics.detect_anomalies') as mock_detect:
        from app.embedding_diagnostics import DiagnosticsResult
        
        mock_detect.return_value = DiagnosticsResult(
            total_terms=3,
            total_pairs=3,
            anomalies=[],
            max_similarity=0.75,
            threshold_used=0.95,
        )
        
        response = await client.post(
            "/api/v1/diagnostics/similarity-anomalies",
            json={
                "terms": ["Программирование", "Алгоритмы", "Базы данных"],
                "threshold": 0.95,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_terms"] == 3


@pytest.mark.asyncio
async def test_similarity_anomalies_duplicates(
    client: AsyncClient,
    admin_token: str,
):
    """Тест с дубликатами терминов."""
    with patch('app.routers.diagnostics.detect_anomalies') as mock_detect:
        from app.embedding_diagnostics import DiagnosticsResult
        
        # После дедупликации останется только Python и Java
        mock_detect.return_value = DiagnosticsResult(
            total_terms=2,
            total_pairs=1,
            anomalies=[],
            max_similarity=0.60,
            threshold_used=0.95,
        )
        
        response = await client.post(
            "/api/v1/diagnostics/similarity-anomalies",
            json={
                "terms": ["Python", "python", "PYTHON", "Java"],
                "threshold": 0.95,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        data = response.json()
        # После дедупликации должно остаться меньше терминов
        assert data["total_terms"] <= 4
        
        # Дубликаты не должны создавать аномалии
        for anomaly in data["anomalies"]:
            assert anomaly["term_a"].lower() != anomaly["term_b"].lower()

