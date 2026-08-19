from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ClassFlowError
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    hash_password_reset_token,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.password_reset_token import PasswordResetTokenRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserCreate
from app.services.email import EmailService


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_reset_token_repository: PasswordResetTokenRepository | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.password_reset_token_repository = password_reset_token_repository
        self.email_service = email_service

    async def register_user(self, user_in: UserCreate) -> User:
        existing_username = await self.user_repository.get_by_username(user_in.username)
        if existing_username is not None:
            raise ClassFlowError(
                detail="Username is already registered",
                error_code="USERNAME_ALREADY_EXISTS",
                status_code=status.HTTP_409_CONFLICT,
            )

        existing_email = await self.user_repository.get_by_email(str(user_in.email))
        if existing_email is not None:
            raise ClassFlowError(
                detail="Email is already registered",
                error_code="EMAIL_ALREADY_EXISTS",
                status_code=status.HTTP_409_CONFLICT,
            )

        if user_in.roll_number is not None:
            existing_roll_number = await self.user_repository.get_by_roll_number(
                user_in.roll_number
            )
            if existing_roll_number is not None:
                raise ClassFlowError(
                    detail="Roll number is already registered",
                    error_code="ROLL_NUMBER_ALREADY_EXISTS",
                    status_code=status.HTTP_409_CONFLICT,
                )

        try:
            return await self.user_repository.create(
                user_in=user_in,
                password_hash=hash_password(user_in.password),
            )
        except IntegrityError as exc:
            raise ClassFlowError(
                detail="User with these details already exists",
                error_code="USER_ALREADY_EXISTS",
                status_code=status.HTTP_409_CONFLICT,
            ) from exc

    async def authenticate_user(self, username: str, password: str) -> User:
        user = await self.user_repository.get_by_username(username)

        if user is None or not verify_password(password, user.password_hash):
            raise ClassFlowError(
                detail="Incorrect username or password",
                error_code="INVALID_LOGIN",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            raise ClassFlowError(
                detail="User account is inactive",
                error_code="INACTIVE_USER",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return user

    async def create_login_token(self, username: str, password: str) -> Token:
        user = await self.authenticate_user(username=username, password=password)
        return await self.create_token_pair(user)

    async def refresh_login_token(self, refresh_token: str) -> Token:
        token_record = await self.get_valid_refresh_token(refresh_token)
        user = await self.user_repository.get_by_id(token_record.user_id)

        if user is None or not user.is_active:
            raise ClassFlowError(
                detail="Invalid refresh token",
                error_code="INVALID_REFRESH_TOKEN",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        await self.refresh_token_repository.revoke(
            refresh_token=token_record,
            revoked_at=datetime.now(timezone.utc),
        )
        return await self.create_token_pair(user)

    async def logout(self, refresh_token: str) -> None:
        token_record = await self.get_valid_refresh_token(refresh_token)
        await self.refresh_token_repository.revoke(
            refresh_token=token_record,
            revoked_at=datetime.now(timezone.utc),
        )

    async def create_token_pair(self, user: User) -> Token:
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token()
        refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        await self.refresh_token_repository.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expires_at,
        )

        return Token(access_token=access_token, refresh_token=refresh_token)

    async def get_valid_refresh_token(self, refresh_token: str):
        token_record = await self.refresh_token_repository.get_by_hash(
            hash_refresh_token(refresh_token)
        )
        now = datetime.now(timezone.utc)

        if (
            token_record is None
            or token_record.revoked_at is not None
            or token_record.expires_at <= now
        ):
            raise ClassFlowError(
                detail="Invalid refresh token",
                error_code="INVALID_REFRESH_TOKEN",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return token_record

    async def request_password_reset(self, email: str) -> None:
        user = await self.user_repository.get_by_email(email)

        if user is None or not user.is_active:
            return

        if self.password_reset_token_repository is None or self.email_service is None:
            raise RuntimeError("Password reset dependencies are not configured")

        raw_token = create_password_reset_token()
        token_hash = hash_password_reset_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )

        await self.password_reset_token_repository.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        reset_link = f"{settings.FRONTEND_PASSWORD_RESET_URL}?token={raw_token}"
        await self.email_service.send_password_reset_email(str(user.email), reset_link)

    async def reset_password(self, token: str, new_password: str) -> None:
        if self.password_reset_token_repository is None:
            raise RuntimeError("Password reset dependencies are not configured")

        token_record = await self.password_reset_token_repository.get_by_hash(
            hash_password_reset_token(token)
        )
        now = datetime.now(timezone.utc)

        if (
            token_record is None
            or token_record.used_at is not None
            or token_record.expires_at <= now
        ):
            raise ClassFlowError(
                detail="Invalid or expired password reset token",
                error_code="INVALID_PASSWORD_RESET_TOKEN",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = await self.user_repository.get_by_id(token_record.user_id)
        if user is None or not user.is_active:
            raise ClassFlowError(
                detail="Invalid or expired password reset token",
                error_code="INVALID_PASSWORD_RESET_TOKEN",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        await self.user_repository.update_password_hash(user, hash_password(new_password))
        await self.password_reset_token_repository.mark_used(token_record, now)
        await self.refresh_token_repository.revoke_all_for_user(user.id, now)

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise ClassFlowError(
                detail="Current password is incorrect",
                error_code="INVALID_CURRENT_PASSWORD",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        now = datetime.now(timezone.utc)
        await self.user_repository.update_password_hash(user, hash_password(new_password))
        await self.refresh_token_repository.revoke_all_for_user(user.id, now)
