from datetime import datetime, timedelta, timezone

from fastapi import status

from app.core.exceptions import ClassFlowError
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import Token
from app.schemas.user import UserCreate


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

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

        return await self.user_repository.create(
            user_in=user_in,
            password_hash=hash_password(user_in.password),
        )

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
