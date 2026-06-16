from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: str | None = Field(default=None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)
    full_name: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
