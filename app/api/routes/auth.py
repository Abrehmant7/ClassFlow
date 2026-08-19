from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database.session import get_db_session
from app.models.user import User
from app.repositories.password_reset_token import PasswordResetTokenRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LogoutResponse,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    Token,
)
from app.schemas.user import UserCreate, UserRead
from app.services.auth import AuthService
from app.services.email import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: AsyncSession) -> AuthService:
    return AuthService(
        user_repository=UserRepository(session),
        refresh_token_repository=RefreshTokenRepository(session),
        password_reset_token_repository=PasswordResetTokenRepository(session),
        email_service=EmailService(),
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRead:
    return await get_auth_service(session).register_user(user_in)


@router.post("/login", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    return await get_auth_service(session).create_login_token(
        username=form_data.username,
        password=form_data.password,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_in: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Token:
    return await get_auth_service(session).refresh_login_token(token_in.refresh_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout_user(
    token_in: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LogoutResponse:
    await get_auth_service(session).logout(token_in.refresh_token)
    return LogoutResponse(detail="Logged out successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    password_reset_in: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    await get_auth_service(session).request_password_reset(str(password_reset_in.email))
    return MessageResponse(
        detail="If an account exists for this email, password reset instructions have been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    password_reset_in: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    await get_auth_service(session).reset_password(
        token=password_reset_in.token,
        new_password=password_reset_in.new_password,
    )
    return MessageResponse(detail="Password has been reset successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_in: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MessageResponse:
    await get_auth_service(session).change_password(
        user=current_user,
        current_password=password_in.current_password,
        new_password=password_in.new_password,
    )
    return MessageResponse(detail="Password has been changed successfully")
