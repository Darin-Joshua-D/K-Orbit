"""
Pydantic models for user management.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class UserListResponse(BaseModel):
    """User list response model."""
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    department: Optional[str] = Field(None, description="User department")
    position: Optional[str] = Field(None, description="User position")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    onboarding_completed: bool = Field(..., description="Onboarding completion status")


class UserDetailResponse(BaseModel):
    """Detailed user response model."""
    id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    org_id: str = Field(..., description="Organization ID")
    department: Optional[str] = Field(None, description="User department")
    position: Optional[str] = Field(None, description="User position")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    manager_id: Optional[str] = Field(None, description="Manager user ID")
    manager_name: Optional[str] = Field(None, description="Manager full name")
    direct_reports: List["UserListResponse"] = Field(default=[], description="Direct reports")
    onboarding_completed: bool = Field(..., description="Onboarding completion status")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    total_xp: int = Field(default=0, description="Total XP earned")
    level: int = Field(default=1, description="Current level")
    badges_count: int = Field(default=0, description="Number of badges earned")
    courses_completed: int = Field(default=0, description="Number of courses completed")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class UpdateUserRequest(BaseModel):
    """Update user request model (Admin/Manager only)."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="User full name")
    role: Optional[str] = Field(None, description="User role")
    department: Optional[str] = Field(None, description="User department")
    position: Optional[str] = Field(None, description="User position")
    manager_id: Optional[str] = Field(None, description="Manager user ID")


class UserSearchRequest(BaseModel):
    """User search request model."""
    query: Optional[str] = Field(None, description="Search query (name, email, department)")
    role: Optional[str] = Field(None, description="Filter by role")
    department: Optional[str] = Field(None, description="Filter by department")
    manager_id: Optional[str] = Field(None, description="Filter by manager")
    include_inactive: bool = Field(default=False, description="Include inactive users")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class UserSearchResponse(BaseModel):
    """User search response model."""
    users: List[UserListResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class UserActivityLog(BaseModel):
    """User activity log entry."""
    id: str = Field(..., description="Activity ID")
    user_id: str = Field(..., description="User ID")
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = Field(None, description="Resource type affected")
    resource_id: Optional[str] = Field(None, description="Resource ID affected")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="Activity timestamp")


class UserStatsResponse(BaseModel):
    """User statistics response model."""
    user_id: str = Field(..., description="User ID")
    total_xp: int = Field(..., description="Total XP earned")
    level: int = Field(..., description="Current level")
    level_progress: float = Field(..., description="Progress to next level (0-1)")
    badges_earned: int = Field(..., description="Number of badges earned")
    courses_completed: int = Field(..., description="Number of courses completed")
    courses_in_progress: int = Field(..., description="Number of courses in progress")
    forum_posts: int = Field(..., description="Number of forum posts")
    forum_helpful_answers: int = Field(..., description="Number of helpful answers")
    login_streak: int = Field(..., description="Current login streak in days")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


# Update forward references
UserDetailResponse.model_rebuild()
UserListResponse.model_rebuild() 