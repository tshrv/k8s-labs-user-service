import bcrypt
import structlog
from fastapi import APIRouter, Query, status
from ulid import ULID
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models.user import User
from app.dependencies import DbSession
from app.exceptions import ConflictError, NotFoundError
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate

logger = structlog.get_logger(__name__)
router = APIRouter()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@router.get("", response_model=UserListResponse)
async def list_users(
    db: DbSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> UserListResponse:
    offset = (page - 1) * size
    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()
    result = await db.execute(
        select(User).offset(offset).limit(size).order_by(User.created_at.desc())
    )
    users = list(result.scalars().all())
    return UserListResponse(items=users, total=total, page=page, size=size)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: DbSession) -> User:
    user = User(
        id=str(ULID()),
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=_hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Email or username already exists") from exc
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: DbSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User", user_id)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, payload: UserUpdate, db: DbSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User", user_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = _hash_password(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, db: DbSession) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User", user_id)
    await db.delete(user)
