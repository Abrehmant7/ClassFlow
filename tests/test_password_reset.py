from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app.core.exceptions import ClassFlowError
from app.core.security import hash_password, hash_password_reset_token, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.auth import AuthService


class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self.users_by_id = {user.id: user for user in users}
        self.users_by_email = {user.email: user for user in users}

    async def get_by_id(self, user_id: int) -> User | None:
        return self.users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return self.users_by_email.get(email)

    async def update_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.revoked_user_ids: list[int] = []

    async def revoke_all_for_user(self, user_id: int, revoked_at: datetime) -> None:
        self.revoked_user_ids.append(user_id)


class FakePasswordResetTokenRepository:
    def __init__(self, tokens: dict[str, PasswordResetToken] | None = None) -> None:
        self.tokens = tokens or {}
        self.created_tokens: list[PasswordResetToken] = []
        self.used_tokens: list[PasswordResetToken] = []

    async def create(
        self,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            id=len(self.created_tokens) + 1,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=None,
        )
        self.tokens[token_hash] = token
        self.created_tokens.append(token)
        return token

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.tokens.get(token_hash)

    async def mark_used(self, token: PasswordResetToken, used_at: datetime) -> PasswordResetToken:
        token.used_at = used_at
        self.used_tokens.append(token)
        return token


class FakeEmailService:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[str, str]] = []

    async def send_password_reset_email(self, email: str, reset_link: str) -> None:
        self.sent_messages.append((email, reset_link))


def make_user(
    user_id: int = 1,
    email: str = "student@example.com",
    password: str = "OldPassword123!",
    is_active: bool = True,
) -> User:
    return User(
        id=user_id,
        username="student",
        email=email,
        password_hash=hash_password(password),
        first_name="Student",
        last_name=None,
        roll_number=None,
        semester=None,
        section=None,
        is_active=is_active,
        is_superuser=False,
    )


def make_service(
    user: User | None,
    password_reset_repository: FakePasswordResetTokenRepository | None = None,
) -> tuple[
    AuthService,
    FakePasswordResetTokenRepository,
    FakeRefreshTokenRepository,
    FakeEmailService,
]:
    reset_repository = password_reset_repository or FakePasswordResetTokenRepository()
    refresh_repository = FakeRefreshTokenRepository()
    email_service = FakeEmailService()
    service = AuthService(
        user_repository=FakeUserRepository([user] if user is not None else []),
        refresh_token_repository=refresh_repository,
        password_reset_token_repository=reset_repository,
        email_service=email_service,
    )
    return service, reset_repository, refresh_repository, email_service


def extract_token_from_reset_link(reset_link: str) -> str:
    query = parse_qs(urlparse(reset_link).query)
    return query["token"][0]


@pytest.mark.anyio
async def test_request_password_reset_creates_token_and_sends_reset_link() -> None:
    user = make_user()
    service, reset_repository, _, email_service = make_service(user)

    await service.request_password_reset(user.email)

    assert len(reset_repository.created_tokens) == 1
    assert len(email_service.sent_messages) == 1
    sent_email, reset_link = email_service.sent_messages[0]
    raw_token = extract_token_from_reset_link(reset_link)

    assert sent_email == user.email
    assert reset_repository.created_tokens[0].user_id == user.id
    assert reset_repository.created_tokens[0].token_hash == hash_password_reset_token(raw_token)


@pytest.mark.anyio
async def test_request_password_reset_does_not_reveal_unknown_email() -> None:
    service, reset_repository, _, email_service = make_service(user=None)

    await service.request_password_reset("missing@example.com")

    assert reset_repository.created_tokens == []
    assert email_service.sent_messages == []


@pytest.mark.anyio
async def test_reset_password_updates_password_marks_token_used_and_revokes_refresh_tokens() -> None:
    raw_token = "valid-reset-token"
    user = make_user()
    token_record = PasswordResetToken(
        id=1,
        user_id=user.id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        used_at=None,
    )
    reset_repository = FakePasswordResetTokenRepository(
        {token_record.token_hash: token_record}
    )
    service, reset_repository, refresh_repository, _ = make_service(
        user,
        password_reset_repository=reset_repository,
    )

    await service.reset_password(raw_token, "NewPassword123!")

    assert verify_password("NewPassword123!", user.password_hash)
    assert reset_repository.used_tokens == [token_record]
    assert refresh_repository.revoked_user_ids == [user.id]


@pytest.mark.anyio
async def test_reset_password_rejects_used_token() -> None:
    raw_token = "used-reset-token"
    user = make_user()
    token_record = PasswordResetToken(
        id=1,
        user_id=user.id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        used_at=datetime.now(timezone.utc),
    )
    reset_repository = FakePasswordResetTokenRepository(
        {token_record.token_hash: token_record}
    )
    service, _, _, _ = make_service(user, password_reset_repository=reset_repository)

    with pytest.raises(ClassFlowError) as exc_info:
        await service.reset_password(raw_token, "NewPassword123!")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "INVALID_PASSWORD_RESET_TOKEN"


@pytest.mark.anyio
async def test_change_password_requires_current_password() -> None:
    user = make_user()
    service, _, _, _ = make_service(user)

    with pytest.raises(ClassFlowError) as exc_info:
        await service.change_password(user, "WrongPassword123!", "NewPassword123!")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "INVALID_CURRENT_PASSWORD"


@pytest.mark.anyio
async def test_change_password_updates_password_and_revokes_refresh_tokens() -> None:
    user = make_user()
    service, _, refresh_repository, _ = make_service(user)

    await service.change_password(user, "OldPassword123!", "NewPassword123!")

    assert verify_password("NewPassword123!", user.password_hash)
    assert refresh_repository.revoked_user_ids == [user.id]
