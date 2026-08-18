from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User]):
    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_roll_number(self, roll_number: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.roll_number == roll_number)
        )
        return result.scalar_one_or_none()

    async def create(self, user_in: UserCreate, password_hash: str) -> User:
        user = User(
            username=user_in.username,
            email=user_in.email,
            password_hash=password_hash,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            roll_number=user_in.roll_number,
            semester=user_in.semester,
            section=user_in.section,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(user)
        return user

    async def update(self, user: User, user_in: UserUpdate) -> User:
        update_data = user_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(user)
        return user
