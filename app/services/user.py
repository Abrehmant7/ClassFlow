from fastapi import status

from app.core.exceptions import ClassFlowError
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def update_profile(self, user: User, user_in: UserUpdate) -> User:
        if user_in.roll_number is not None:
            existing_user = await self.user_repository.get_by_roll_number(user_in.roll_number)
            if existing_user is not None and existing_user.id != user.id:
                raise ClassFlowError(
                    detail="Roll number is already registered",
                    error_code="ROLL_NUMBER_ALREADY_EXISTS",
                    status_code=status.HTTP_409_CONFLICT,
                )

        return await self.user_repository.update(user, user_in)