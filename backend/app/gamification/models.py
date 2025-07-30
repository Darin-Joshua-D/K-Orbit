"""
Pydantic models for gamification features.
Handles XP transactions, badges, achievements, and leaderboards.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class XPTransactionRequest(BaseModel):
    """Request model for awarding XP."""
    user_id: str = Field(..., description="User ID to award XP to")
    xp_earned: int = Field(..., gt=0, description="XP amount to award")
    source: str = Field(..., description="XP source")
    source_id: Optional[str] = Field(None, description="Source entity ID")
    description: str = Field(..., description="XP description")


class XPTransactionResponse(BaseModel):
    """Response model for XP transaction."""
    id: str = Field(..., description="Transaction ID")
    user_id: str = Field(..., description="User ID")
    xp_earned: int = Field(..., description="XP amount earned")
    source: str = Field(..., description="XP source")
    source_id: Optional[str] = Field(None, description="Source entity ID")
    description: str = Field(..., description="XP description")
    created_at: datetime = Field(..., description="Transaction timestamp")


class BadgeResponse(BaseModel):
    """Response model for badge."""
    id: str = Field(..., description="Badge ID")
    name: str = Field(..., description="Badge name")
    description: str = Field(..., description="Badge description")
    icon_url: Optional[str] = Field(None, description="Badge icon URL")
    criteria: Dict[str, Any] = Field(..., description="Badge criteria")
    xp_reward: int = Field(..., description="XP reward for earning badge")
    rarity: str = Field(..., description="Badge rarity")
    is_active: bool = Field(..., description="Whether badge is active")
    created_at: datetime = Field(..., description="Badge creation timestamp")


class UserBadgeResponse(BaseModel):
    """Response model for user badge."""
    id: str = Field(..., description="User badge ID")
    user_id: str = Field(..., description="User ID")
    badge_id: str = Field(..., description="Badge ID")
    badge: BadgeResponse = Field(..., description="Badge details")
    earned_at: datetime = Field(..., description="Badge earned timestamp")


class CreateBadgeRequest(BaseModel):
    """Request model for creating a badge."""
    name: str = Field(..., min_length=1, max_length=100, description="Badge name")
    description: str = Field(..., min_length=1, description="Badge description")
    icon_url: Optional[str] = Field(None, description="Badge icon URL")
    criteria: Dict[str, Any] = Field(..., description="Badge criteria JSON")
    xp_reward: int = Field(default=0, ge=0, description="XP reward for earning badge")
    rarity: str = Field(default="common", description="Badge rarity")


class AwardBadgeRequest(BaseModel):
    """Request model for awarding a badge."""
    user_id: str = Field(..., description="User ID to award badge to")
    badge_id: str = Field(..., description="Badge ID to award")


class UserStatsResponse(BaseModel):
    """Response model for user statistics."""
    user_id: str = Field(..., description="User ID")
    total_xp: int = Field(..., description="Total XP earned")
    level: int = Field(..., description="Current level")
    level_progress: float = Field(..., description="Progress to next level (0-1)")
    xp_to_next_level: int = Field(..., description="XP needed for next level")
    badges_earned: int = Field(..., description="Number of badges earned")
    rank: Optional[int] = Field(None, description="User rank in organization")
    recent_badges: List[UserBadgeResponse] = Field(default=[], description="Recently earned badges")
    recent_xp: List[XPTransactionResponse] = Field(default=[], description="Recent XP transactions")


class LeaderboardEntry(BaseModel):
    """Model for leaderboard entry."""
    rank: int = Field(..., description="User rank")
    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    total_xp: int = Field(..., description="Total XP")
    level: int = Field(..., description="User level")
    badges_count: int = Field(..., description="Number of badges")
    department: Optional[str] = Field(None, description="User department")


class LeaderboardResponse(BaseModel):
    """Response model for leaderboard."""
    leaderboard: List[LeaderboardEntry] = Field(..., description="Leaderboard entries")
    user_rank: Optional[int] = Field(None, description="Current user's rank")
    total_users: int = Field(..., description="Total users in leaderboard")
    period: str = Field(..., description="Leaderboard period")
    last_updated: datetime = Field(..., description="Last update timestamp")


class LeaderboardRequest(BaseModel):
    """Request model for leaderboard."""
    period: str = Field(default="all", description="Time period (all, month, week)")
    department: Optional[str] = Field(None, description="Filter by department")
    limit: int = Field(default=50, ge=1, le=100, description="Number of entries")


class AchievementProgress(BaseModel):
    """Model for achievement progress."""
    badge_id: str = Field(..., description="Badge ID")
    badge_name: str = Field(..., description="Badge name")
    badge_description: str = Field(..., description="Badge description")
    progress: float = Field(..., description="Progress towards badge (0-1)")
    current_value: int = Field(..., description="Current progress value")
    target_value: int = Field(..., description="Target value to earn badge")
    is_earned: bool = Field(..., description="Whether badge is already earned")


class UserAchievementsResponse(BaseModel):
    """Response model for user achievements."""
    user_id: str = Field(..., description="User ID")
    earned_badges: List[UserBadgeResponse] = Field(..., description="Earned badges")
    available_badges: List[AchievementProgress] = Field(..., description="Available badges with progress")
    total_badges: int = Field(..., description="Total badges in system")
    completion_percentage: float = Field(..., description="Badge completion percentage")


class XPBreakdown(BaseModel):
    """Model for XP breakdown by source."""
    source: str = Field(..., description="XP source")
    xp_earned: int = Field(..., description="XP earned from this source")
    transaction_count: int = Field(..., description="Number of transactions")
    percentage: float = Field(..., description="Percentage of total XP")


class XPAnalyticsResponse(BaseModel):
    """Response model for XP analytics."""
    user_id: str = Field(..., description="User ID")
    total_xp: int = Field(..., description="Total XP earned")
    xp_this_week: int = Field(..., description="XP earned this week")
    xp_this_month: int = Field(..., description="XP earned this month")
    breakdown: List[XPBreakdown] = Field(..., description="XP breakdown by source")
    daily_xp: List[Dict[str, Any]] = Field(..., description="Daily XP for last 30 days")
    streak_days: int = Field(..., description="Current streak in days")


class LevelSystemConfig(BaseModel):
    """Model for level system configuration."""
    level: int = Field(..., description="Level number")
    xp_required: int = Field(..., description="Total XP required for this level")
    xp_for_level: int = Field(..., description="XP needed from previous level")
    title: str = Field(..., description="Level title")
    benefits: List[str] = Field(default=[], description="Level benefits")


class GamificationSettingsRequest(BaseModel):
    """Request model for gamification settings."""
    xp_lesson_completion: int = Field(default=50, ge=0, description="XP for lesson completion")
    xp_course_completion: int = Field(default=200, ge=0, description="XP for course completion")
    xp_forum_answer: int = Field(default=25, ge=0, description="XP for forum answer")
    xp_helpful_answer: int = Field(default=50, ge=0, description="XP for helpful answer")
    xp_login_streak: int = Field(default=10, ge=0, description="XP for daily login")
    level_xp_multiplier: int = Field(default=1000, ge=100, description="XP multiplier for levels")


class GamificationSettingsResponse(BaseModel):
    """Response model for gamification settings."""
    org_id: str = Field(..., description="Organization ID")
    settings: GamificationSettingsRequest = Field(..., description="Gamification settings")
    level_system: List[LevelSystemConfig] = Field(..., description="Level system configuration")
    updated_at: datetime = Field(..., description="Last update timestamp")


class XPLeaderboardFilters(BaseModel):
    """Filters for XP leaderboard."""
    time_period: str = Field(default="all_time", description="Time period filter")
    department: Optional[str] = Field(None, description="Department filter")
    role: Optional[str] = Field(None, description="Role filter")
    course_id: Optional[str] = Field(None, description="Course-specific leaderboard")


class BadgeLeaderboardEntry(BaseModel):
    """Model for badge leaderboard entry."""
    rank: int = Field(..., description="User rank")
    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    badges_count: int = Field(..., description="Total badges earned")
    rare_badges_count: int = Field(..., description="Rare badges earned")
    latest_badge: Optional[str] = Field(None, description="Latest badge earned")
    department: Optional[str] = Field(None, description="User department")


class BadgeLeaderboardResponse(BaseModel):
    """Response model for badge leaderboard."""
    leaderboard: List[BadgeLeaderboardEntry] = Field(..., description="Badge leaderboard entries")
    user_rank: Optional[int] = Field(None, description="Current user's rank")
    total_users: int = Field(..., description="Total users in leaderboard")
    last_updated: datetime = Field(..., description="Last update timestamp") 