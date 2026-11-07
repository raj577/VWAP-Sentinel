"""Authentication and user-management schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name is too short.")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    device_name: str | None = Field(default=None, max_length=120)


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=500)
    device_name: str | None = Field(default=None, max_length=120)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=500)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=10, max_length=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class MessageResponse(BaseModel):
    message: str
    dev_token: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    account_status: str
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    roles: list[str] = Field(default_factory=list)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str
    user: UserOut


class SessionOut(BaseModel):
    id: str
    device_name: str | None
    user_agent: str | None
    ip_address: str | None = None
    created_at: datetime
    last_activity_at: datetime | None
    current: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionOut]


class AdminUserPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class UserStatusUpdate(BaseModel):
    account_status: str


class UserRoleUpdate(BaseModel):
    role: str


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    target_user_id: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    meta: dict
    ip_address: str | None
    created_at: datetime


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name is too short.")
        return cleaned
