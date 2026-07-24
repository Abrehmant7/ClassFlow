from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LogoutResponse, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRead:
    service = AuthService(
        user_repository=UserRepository(session),
        refresh_token_repository=RefreshTokenRepository(session),
    )
    return await service.register_user(user_in)


@router.post("/login", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    service = AuthService(
        user_repository=UserRepository(session),
        refresh_token_repository=RefreshTokenRepository(session),
    )
    return await service.create_login_token(
        username=form_data.username,
        password=form_data.password,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_in: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    service = AuthService(
        user_repository=UserRepository(session),
        refresh_token_repository=RefreshTokenRepository(session),
    )
    return await service.refresh_login_token(token_in.refresh_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(
    token_in: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LogoutResponse:
    service = AuthService(
        user_repository=UserRepository(session),
        refresh_token_repository=RefreshTokenRepository(session),
    )
    await service.logout(token_in.refresh_token)
    return LogoutResponse(detail="Logged out successfully")
