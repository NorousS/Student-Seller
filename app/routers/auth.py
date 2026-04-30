"""
Роутер аутентификации: регистрация, логин, refresh, профиль.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.logging_config import get_logger
from app.models import EmployerProfile, Student, User, UserRole
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
logger = get_logger(__name__)


def _mask_email(email: str) -> str:
    """Маскирует email для безопасного логирования."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Регистрация нового пользователя.
    При role=student автоматически создаётся Student.
    При role=employer автоматически создаётся EmployerProfile.
    """
    logger.info(
        "Попытка регистрации пользователя",
        email=_mask_email(request.email),
        role=request.role,
    )

    # Проверяем, что email не занят
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        logger.warning(
            "Регистрация отклонена: email уже занят",
            email=_mask_email(request.email),
            role=request.role,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Валидация: студент должен указать ФИО
    if request.role == "student" and not request.full_name:
        logger.warning(
            "Регистрация отклонена: для студента не передано ФИО",
            email=_mask_email(request.email),
            role=request.role,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="full_name is required for students")

    # Создаём пользователя
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        role=UserRole(request.role),
    )
    db.add(user)
    await db.flush()

    # Создаём связанный профиль
    if request.role == "student":
        student = Student(
            user_id=user.id,
            full_name=request.full_name,
            group_name=request.group_name,
        )
        db.add(student)
    elif request.role == "employer":
        employer_profile = EmployerProfile(
            user_id=user.id,
            company_name=request.company_name,
        )
        db.add(employer_profile)

    await db.commit()
    logger.info("Пользователь успешно зарегистрирован", user_id=user.id, role=user.role.value)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Аутентификация пользователя. Возвращает JWT-токены."""
    logger.info("Попытка входа", email=_mask_email(request.email))
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        logger.warning("Вход отклонён: неверные учетные данные", email=_mask_email(request.email))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        logger.warning("Вход отклонён: аккаунт деактивирован", user_id=user.id, role=user.role.value)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    logger.info("Вход выполнен успешно", user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Обновление access-токена по refresh-токену."""
    logger.info("Попытка обновления access-токена")
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        logger.warning("Обновление токена отклонено: неверный тип токена")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.warning("Обновление токена отклонено: пользователь не найден или неактивен", user_id=user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    logger.info("Access-токен успешно обновлён", user_id=user.id, role=user.role.value)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Текущий пользователь."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active,
    )
