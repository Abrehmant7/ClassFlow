from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, oauth2_scheme
from app.database.session import get_db_session
from app.repositories.user import UserRepository
from app.models.user import User

from app.core.exceptions import ClassFlowError
from app.models.classroom import (
    CLASS_ROLE_REPRESENTATIVE,
    MEMBERSHIP_STATUS_APPROVED,
    ClassMembership,
)
from app.repositories.membership import ClassMembershipRepository


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = await UserRepository(session).get_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return user


async def get_membership(
    class_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassMembership:
    membership = await ClassMembershipRepository(session).get_by_user_and_class(
        user_id=current_user.id,
        classroom_id=class_id,
    )
    if membership is None:
        raise ClassFlowError("Class membership required", "CLASS_MEMBERSHIP_REQUIRED", status.HTTP_403_FORBIDDEN)
    return membership


async def get_approved_membership(
    membership: Annotated[ClassMembership, Depends(get_membership)],
) -> ClassMembership:
    if membership.status != MEMBERSHIP_STATUS_APPROVED:
        raise ClassFlowError("Approved class membership required", "APPROVED_CLASS_MEMBERSHIP_REQUIRED", status.HTTP_403_FORBIDDEN)
    return membership


async def require_representative(
    membership: Annotated[ClassMembership, Depends(get_approved_membership)],
) -> ClassMembership:
    if membership.role != CLASS_ROLE_REPRESENTATIVE:
        raise ClassFlowError("Class representative access required", "CLASS_REPRESENTATIVE_REQUIRED", status.HTTP_403_FORBIDDEN)
    return membership


# Backward-compatible aliases for existing routes.
get_approved_member = get_approved_membership
get_class_representative = require_representative