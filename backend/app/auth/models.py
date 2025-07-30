"""
Pydantic models for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


class LoginRequest(BaseModel):
    """User login request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RegisterRequest(BaseModel):
    """User registration request model."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    org_id: str = Field(..., description="Organization ID")
    role: Optional[str] = Field(default="learner", description="User role")
    
    @validator("role")
    def validate_role(cls, v):
        allowed_roles = ["learner", "sme", "manager", "admin", "super_admin"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {allowed_roles}")
        return v


class AuthResponse(BaseModel):
    """Authentication response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: "UserProfile" = Field(..., description="User profile information")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="Refresh token")


class ResetPasswordRequest(BaseModel):
    """Password reset request model."""
    email: EmailStr = Field(..., description="User email address")


class UpdatePasswordRequest(BaseModel):
    """Update password request model."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class UserProfile(BaseModel):
    """User profile model."""
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    org_id: str = Field(..., description="Organization ID")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    department: Optional[str] = Field(None, description="User department")
    position: Optional[str] = Field(None, description="User position")
    manager_id: Optional[str] = Field(None, description="Manager user ID")
    onboarding_completed: bool = Field(default=False, description="Onboarding completion status")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class InviteUserRequest(BaseModel):
    """Invite user request model."""
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    role: str = Field(..., description="User role")
    department: Optional[str] = Field(None, description="User department")
    position: Optional[str] = Field(None, description="User position")
    manager_id: Optional[str] = Field(None, description="Manager user ID")
    
    @validator("role")
    def validate_role(cls, v):
        allowed_roles = ["learner", "sme", "manager", "admin"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {allowed_roles}")
        return v


class UpdateProfileRequest(BaseModel):
    """Update user profile request model."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="User full name")
    department: Optional[str] = Field(None, description="User department")
    position: Optional[str] = Field(None, description="User position")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")


class VerifyEmailRequest(BaseModel):
    """Email verification request model."""
    token: str = Field(..., description="Email verification token")


# Update forward references
AuthResponse.model_rebuild() 