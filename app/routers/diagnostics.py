"""
API эндпоинт для диагностики аномалий similarity в эмбеддингах.

Предназначен для администраторов для выявления потенциальных
проблем с качеством векторных представлений.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.embedding_diagnostics import detect_anomalies, DiagnosticsResult
from app.models import User


router = APIRouter(prefix="/api/v1/diagnostics", tags=["diagnostics"])


# --- Схемы запросов ---


class DiagnosticsRequest(BaseModel):
    """
    Запрос на диагностику аномалий similarity.
    
    Attributes:
        terms: Список терминов для проверки (до 100)
        threshold: Порог similarity для аномалий (default: 0.99)
    """
    terms: list[str] = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Список терминов для проверки (2-100 терминов)",
    )
    threshold: float = Field(
        default=0.99,
        ge=0.8,
        le=1.0,
        description="Порог similarity для считывания аномалией (0.8-1.0)",
    )


# --- Эндпоинты ---


@router.post(
    "/similarity-anomalies",
    response_model=DiagnosticsResult,
    summary="Диагностика аномалий similarity",
    description=(
        "Проверяет список терминов на подозрительно высокие значения "
        "косинусного сходства между различными терминами. "
        "**Требует роли admin.**"
    ),
)
async def check_similarity_anomalies(
    request: DiagnosticsRequest,
    current_user: User = Depends(get_current_user),
) -> DiagnosticsResult:
    """
    Диагностика аномалий similarity для списка терминов.
    
    Генерирует эмбеддинги для всех предоставленных терминов и
    вычисляет попарное косинусное сходство. Возвращает пары терминов
    с подозрительно высоким similarity (по умолчанию >= 0.99).
    
    Args:
        request: Запрос с терминами и порогом
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        DiagnosticsResult с обнаруженными аномалиями
        
    Raises:
        HTTPException 403: Если пользователь не является администратором
        HTTPException 400: Если входные данные некорректны
        HTTPException 500: Если произошла ошибка при генерации эмбеддингов
    """
    # Проверка прав доступа
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль admin.",
        )
    
    # Валидация входных данных
    if len(request.terms) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо минимум 2 термина для сравнения",
        )
    
    # Проверка на пустые термины
    empty_terms = [i for i, term in enumerate(request.terms) if not term.strip()]
    if empty_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Обнаружены пустые термины на позициях: {empty_terms}",
        )
    
    try:
        # Выполняем диагностику
        result = await detect_anomalies(
            terms=request.terms,
            threshold=request.threshold,
        )
        return result
        
    except ValueError as e:
        # Ошибки валидации из detect_anomalies
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except httpx.HTTPError as e:
        # Ошибки подключения к Ollama
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Сервис эмбеддингов недоступен: {str(e)}",
        ) from e
