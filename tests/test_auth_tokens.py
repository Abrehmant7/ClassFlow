from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import ClassFlowError
from app.core.security import hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth import AuthService


class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self.users_by_id = {user.id: user for user in users}

    async def get_by_id(self, user_id: int) -> User | None:
        return self.users_by_id.get(user_id)


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens_by_hash: dict[str, RefreshToken] = {}
        self.created_tokens: list[RefreshToken] = []
        self.revoked_tokens: list[RefreshToken] = []

    async def create(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        refresh_token = RefreshToken(
            id=len(self.created_tokens) + 1,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self.tokens_by_hash[token_hash] = refresh_token
        self.created_tokens.append(refresh_token)
        return refresh_token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.tokens_by_hash.get(token_hash)

    async def revoke(self, refresh_token: RefreshToken, revoked_at: datetime) -> RefreshToken:
        refresh_token.revoked_at = revoked_at
        self.revoked_tokens.append(refresh_token)
        return refresh_token

    async def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> None:
        for refresh_token in self.created_tokens:
            if refresh_token.user_id == user_id and refresh_token.revoked_at is None:
                await self.revoke(refresh_token, revoked_at)


def make_user(user_id: int = 1) -> User:
    return User(
        id=user_id,
        username="student",
        email="student@example.com",
        password_hash="not-used",
        first_name="Student",
        last_name=None,
        roll_number=None,
        semester=None,
        section=None,
        is_active=True,
        is_superuser=False,
    )


def make_service(user: User) -> tuple[AuthService, FakeRefreshTokenRepository]:
    refresh_repository = FakeRefreshTokenRepository()
    service = AuthService(
        user_repository=FakeUserRepository([user]),
        refresh_token_repository=refresh_repository,
    )
    return service, refresh_repository


@pytest.mark.anyio
async def test_refresh_token_rotation_rejects_reuse() -> None:
    user = make_user()
    service, refresh_repository = make_service(user)
    original_pair = await service.create_token_pair(user)

    rotated_pair = await service.refresh_login_token(original_pair.refresh_token)

    original_record = refresh_repository.tokens_by_hash[
        hash_refresh_token(original_pair.refresh_token)
    ]
    assert original_record.revoked_at is not None
    assert rotated_pair.refresh_token != original_pair.refresh_token
    assert len(refresh_repository.created_tokens) == 2

    with pytest.raises(ClassFlowError) as exc_info:
        await service.refresh_login_token(original_pair.refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.anyio
async def test_logout_revokes_refresh_token_and_blocks_future_use() -> None:
    user = make_user()
    service, refresh_repository = make_service(user)
    token_pair = await service.create_token_pair(user)

    await service.logout(token_pair.refresh_token)

    token_record = refresh_repository.tokens_by_hash[
        hash_refresh_token(token_pair.refresh_token)
    ]
    assert token_record.revoked_at is not None

    with pytest.raises(ClassFlowError) as exc_info:
        await service.refresh_login_token(token_pair.refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.anyio
async def test_expired_refresh_token_is_rejected() -> None:
    user = make_user()
    service, refresh_repository = make_service(user)
    raw_token = "expired-refresh-token"
    refresh_repository.tokens_by_hash[hash_refresh_token(raw_token)] = RefreshToken(
        id=1,
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        revoked_at=None,
    )

    with pytest.raises(ClassFlowError) as exc_info:
        await service.refresh_login_token(raw_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error_code"] == "INVALID_REFRESH_TOKEN"
