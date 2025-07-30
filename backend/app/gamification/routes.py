"""
Gamification routes for K-Orbit API.
Handles XP transactions, badges, achievements, and leaderboards.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends, Query, BackgroundTasks
from supabase import create_client, Client

from app.auth.middleware import get_current_user, require_admin, require_manager
from app.gamification.models import (
    XPTransactionRequest,
    XPTransactionResponse,
    BadgeResponse,
    UserBadgeResponse,
    CreateBadgeRequest,
    AwardBadgeRequest,
    UserStatsResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    LeaderboardRequest,
    UserAchievementsResponse,
    XPAnalyticsResponse,
    GamificationSettingsRequest,
    GamificationSettingsResponse
)

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()


@router.get("/profile", response_model=UserStatsResponse)
async def get_user_gamification_profile(
    user: dict = Depends(get_current_user)
):
    """
    Get current user's gamification profile with XP, level, and badges.
    """
    try:
        # Get user's total XP
        xp_response = supabase.table("xp_transactions").select("xp_earned").eq("user_id", user["sub"]).execute()
        total_xp = sum(xp["xp_earned"] for xp in xp_response.data) if xp_response.data else 0
        
        # Calculate level and progress
        level, level_progress, xp_to_next = _calculate_level_info(total_xp)
        
        # Get badges count
        badges_response = supabase.table("user_badges").select("id").eq("user_id", user["sub"]).execute()
        badges_earned = len(badges_response.data) if badges_response.data else 0
        
        # Get user rank in organization
        rank = await _get_user_rank(user["sub"], user["org_id"])
        
        # Get recent badges (last 5)
        recent_badges_response = supabase.table("user_badges").select(
            "*, badges(*)"
        ).eq("user_id", user["sub"]).order("earned_at", desc=True).limit(5).execute()
        
        recent_badges = []
        for ub in recent_badges_response.data or []:
            recent_badges.append(UserBadgeResponse(
                id=ub["id"],
                user_id=ub["user_id"],
                badge_id=ub["badge_id"],
                badge=BadgeResponse(
                    id=ub["badges"]["id"],
                    name=ub["badges"]["name"],
                    description=ub["badges"]["description"],
                    icon_url=ub["badges"].get("icon_url"),
                    criteria=ub["badges"]["criteria"],
                    xp_reward=ub["badges"]["xp_reward"],
                    rarity=ub["badges"]["rarity"],
                    is_active=ub["badges"]["is_active"],
                    created_at=datetime.fromisoformat(ub["badges"]["created_at"])
                ),
                earned_at=datetime.fromisoformat(ub["earned_at"])
            ))
        
        # Get recent XP transactions (last 10)
        recent_xp_response = supabase.table("xp_transactions").select("*").eq(
            "user_id", user["sub"]
        ).order("created_at", desc=True).limit(10).execute()
        
        recent_xp = []
        for xp in recent_xp_response.data or []:
            recent_xp.append(XPTransactionResponse(
                id=xp["id"],
                user_id=xp["user_id"],
                xp_earned=xp["xp_earned"],
                source=xp["source"],
                source_id=xp.get("source_id"),
                description=xp["description"],
                created_at=datetime.fromisoformat(xp["created_at"])
            ))
        
        return UserStatsResponse(
            user_id=user["sub"],
            total_xp=total_xp,
            level=level,
            level_progress=level_progress,
            xp_to_next_level=xp_to_next,
            badges_earned=badges_earned,
            rank=rank,
            recent_badges=recent_badges,
            recent_xp=recent_xp
        )
        
    except Exception as e:
        logger.error("Failed to get user gamification profile", user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve gamification profile"
        )


@router.post("/xp/award", response_model=XPTransactionResponse, dependencies=[Depends(require_admin)])
async def award_xp(
    request: XPTransactionRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Award XP to a user (Admin only).
    """
    try:
        # Create XP transaction
        xp_data = {
            "user_id": request.user_id,
            "xp_earned": request.xp_earned,
            "source": request.source,
            "source_id": request.source_id,
            "description": request.description,
            "created_at": datetime.utcnow().isoformat()
        }
        
        xp_response = supabase.table("xp_transactions").insert(xp_data).execute()
        
        if not xp_response.data:
            raise HTTPException(status_code=500, detail="Failed to award XP")
        
        xp_transaction = xp_response.data[0]
        
        # Check for new badges in background
        background_tasks.add_task(_check_badge_criteria, request.user_id)
        
        logger.info(
            "XP awarded",
            user_id=request.user_id,
            xp_earned=request.xp_earned,
            source=request.source,
            awarded_by=user["sub"]
        )
        
        return XPTransactionResponse(
            id=xp_transaction["id"],
            user_id=xp_transaction["user_id"],
            xp_earned=xp_transaction["xp_earned"],
            source=xp_transaction["source"],
            source_id=xp_transaction.get("source_id"),
            description=xp_transaction["description"],
            created_at=datetime.fromisoformat(xp_transaction["created_at"])
        )
        
    except Exception as e:
        logger.error("Failed to award XP", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to award XP"
        )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str = Query("all", description="Time period (all, month, week)"),
    department: Optional[str] = Query(None, description="Filter by department"),
    limit: int = Query(50, ge=1, le=100, description="Number of entries"),
    user: dict = Depends(get_current_user)
):
    """
    Get XP leaderboard for the organization.
    """
    try:
        # Build base query for user profiles in organization
        query_builder = supabase.table("profiles").select(
            "id, full_name, avatar_url, department"
        ).eq("org_id", user["org_id"]).eq("deleted_at", None)
        
        if department:
            query_builder = query_builder.eq("department", department)
        
        profiles_response = query_builder.execute()
        
        if not profiles_response.data:
            return LeaderboardResponse(
                leaderboard=[],
                user_rank=None,
                total_users=0,
                period=period,
                last_updated=datetime.utcnow()
            )
        
        # Calculate XP for each user based on period
        leaderboard_data = []
        current_user_rank = None
        
        for profile in profiles_response.data:
            user_id = profile["id"]
            
            # Get XP based on period
            xp_query = supabase.table("xp_transactions").select("xp_earned").eq("user_id", user_id)
            
            if period == "week":
                week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
                xp_query = xp_query.gte("created_at", week_ago)
            elif period == "month":
                month_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
                xp_query = xp_query.gte("created_at", month_ago)
            
            xp_response = xp_query.execute()
            total_xp = sum(xp["xp_earned"] for xp in xp_response.data) if xp_response.data else 0
            
            # Get badges count
            badges_response = supabase.table("user_badges").select("id").eq("user_id", user_id).execute()
            badges_count = len(badges_response.data) if badges_response.data else 0
            
            level, _, _ = _calculate_level_info(total_xp)
            
            leaderboard_data.append({
                "user_id": user_id,
                "user_name": profile["full_name"],
                "avatar_url": profile.get("avatar_url"),
                "total_xp": total_xp,
                "level": level,
                "badges_count": badges_count,
                "department": profile.get("department")
            })
        
        # Sort by XP and assign ranks
        leaderboard_data.sort(key=lambda x: x["total_xp"], reverse=True)
        
        leaderboard = []
        for i, entry in enumerate(leaderboard_data[:limit]):
            rank = i + 1
            if entry["user_id"] == user["sub"]:
                current_user_rank = rank
            
            leaderboard.append(LeaderboardEntry(
                rank=rank,
                user_id=entry["user_id"],
                user_name=entry["user_name"],
                avatar_url=entry["avatar_url"],
                total_xp=entry["total_xp"],
                level=entry["level"],
                badges_count=entry["badges_count"],
                department=entry["department"]
            ))
        
        # Find current user rank if not in top results
        if current_user_rank is None:
            for i, entry in enumerate(leaderboard_data):
                if entry["user_id"] == user["sub"]:
                    current_user_rank = i + 1
                    break
        
        return LeaderboardResponse(
            leaderboard=leaderboard,
            user_rank=current_user_rank,
            total_users=len(leaderboard_data),
            period=period,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Failed to get leaderboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve leaderboard"
        )


@router.get("/badges", response_model=List[BadgeResponse])
async def get_badges(
    user: dict = Depends(get_current_user)
):
    """
    Get all available badges in the system.
    """
    try:
        badges_response = supabase.table("badges").select("*").eq("is_active", True).execute()
        
        badges = []
        for badge_data in badges_response.data or []:
            badges.append(BadgeResponse(
                id=badge_data["id"],
                name=badge_data["name"],
                description=badge_data["description"],
                icon_url=badge_data.get("icon_url"),
                criteria=badge_data["criteria"],
                xp_reward=badge_data["xp_reward"],
                rarity=badge_data["rarity"],
                is_active=badge_data["is_active"],
                created_at=datetime.fromisoformat(badge_data["created_at"])
            ))
        
        return badges
        
    except Exception as e:
        logger.error("Failed to get badges", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve badges"
        )


@router.post("/badges", response_model=BadgeResponse, dependencies=[Depends(require_admin)])
async def create_badge(
    request: CreateBadgeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a new badge (Admin only).
    """
    try:
        badge_data = {
            "name": request.name,
            "description": request.description,
            "icon_url": request.icon_url,
            "criteria": request.criteria,
            "xp_reward": request.xp_reward,
            "rarity": request.rarity,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        badge_response = supabase.table("badges").insert(badge_data).execute()
        
        if not badge_response.data:
            raise HTTPException(status_code=500, detail="Failed to create badge")
        
        badge = badge_response.data[0]
        
        logger.info(
            "Badge created",
            badge_id=badge["id"],
            name=badge["name"],
            created_by=user["sub"]
        )
        
        return BadgeResponse(
            id=badge["id"],
            name=badge["name"],
            description=badge["description"],
            icon_url=badge.get("icon_url"),
            criteria=badge["criteria"],
            xp_reward=badge["xp_reward"],
            rarity=badge["rarity"],
            is_active=badge["is_active"],
            created_at=datetime.fromisoformat(badge["created_at"])
        )
        
    except Exception as e:
        logger.error("Failed to create badge", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to create badge"
        )


@router.post("/badges/award", response_model=UserBadgeResponse, dependencies=[Depends(require_admin)])
async def award_badge(
    request: AwardBadgeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Award a badge to a user (Admin only).
    """
    try:
        # Check if badge exists
        badge_response = supabase.table("badges").select("*").eq("id", request.badge_id).single().execute()
        
        if not badge_response.data:
            raise HTTPException(status_code=404, detail="Badge not found")
        
        badge = badge_response.data
        
        # Check if user already has this badge
        existing_badge = supabase.table("user_badges").select("id").eq(
            "user_id", request.user_id
        ).eq("badge_id", request.badge_id).execute()
        
        if existing_badge.data:
            raise HTTPException(status_code=409, detail="User already has this badge")
        
        # Award badge
        user_badge_data = {
            "user_id": request.user_id,
            "badge_id": request.badge_id,
            "earned_at": datetime.utcnow().isoformat()
        }
        
        user_badge_response = supabase.table("user_badges").insert(user_badge_data).execute()
        
        if not user_badge_response.data:
            raise HTTPException(status_code=500, detail="Failed to award badge")
        
        user_badge = user_badge_response.data[0]
        
        # Award XP for earning badge
        if badge["xp_reward"] > 0:
            xp_data = {
                "user_id": request.user_id,
                "xp_earned": badge["xp_reward"],
                "source": "badge_earned",
                "source_id": request.badge_id,
                "description": f"Earned badge: {badge['name']}",
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("xp_transactions").insert(xp_data).execute()
        
        logger.info(
            "Badge awarded",
            user_id=request.user_id,
            badge_id=request.badge_id,
            badge_name=badge["name"],
            awarded_by=user["sub"]
        )
        
        return UserBadgeResponse(
            id=user_badge["id"],
            user_id=user_badge["user_id"],
            badge_id=user_badge["badge_id"],
            badge=BadgeResponse(
                id=badge["id"],
                name=badge["name"],
                description=badge["description"],
                icon_url=badge.get("icon_url"),
                criteria=badge["criteria"],
                xp_reward=badge["xp_reward"],
                rarity=badge["rarity"],
                is_active=badge["is_active"],
                created_at=datetime.fromisoformat(badge["created_at"])
            ),
            earned_at=datetime.fromisoformat(user_badge["earned_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to award badge", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to award badge"
        )


@router.get("/achievements", response_model=UserAchievementsResponse)
async def get_user_achievements(
    user: dict = Depends(get_current_user)
):
    """
    Get user's achievements and progress towards badges.
    """
    try:
        # Get all badges
        all_badges_response = supabase.table("badges").select("*").eq("is_active", True).execute()
        
        # Get user's earned badges
        user_badges_response = supabase.table("user_badges").select(
            "*, badges(*)"
        ).eq("user_id", user["sub"]).execute()
        
        earned_badges = []
        earned_badge_ids = set()
        
        for ub in user_badges_response.data or []:
            earned_badge_ids.add(ub["badge_id"])
            earned_badges.append(UserBadgeResponse(
                id=ub["id"],
                user_id=ub["user_id"],
                badge_id=ub["badge_id"],
                badge=BadgeResponse(
                    id=ub["badges"]["id"],
                    name=ub["badges"]["name"],
                    description=ub["badges"]["description"],
                    icon_url=ub["badges"].get("icon_url"),
                    criteria=ub["badges"]["criteria"],
                    xp_reward=ub["badges"]["xp_reward"],
                    rarity=ub["badges"]["rarity"],
                    is_active=ub["badges"]["is_active"],
                    created_at=datetime.fromisoformat(ub["badges"]["created_at"])
                ),
                earned_at=datetime.fromisoformat(ub["earned_at"])
            ))
        
        # Calculate progress for unearned badges
        available_badges = []
        # This is simplified - in a real implementation, you'd calculate actual progress
        # based on the badge criteria
        
        total_badges = len(all_badges_response.data) if all_badges_response.data else 0
        completion_percentage = (len(earned_badges) / total_badges * 100) if total_badges > 0 else 0
        
        return UserAchievementsResponse(
            user_id=user["sub"],
            earned_badges=earned_badges,
            available_badges=available_badges,
            total_badges=total_badges,
            completion_percentage=completion_percentage
        )
        
    except Exception as e:
        logger.error("Failed to get user achievements", user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve achievements"
        )


def _calculate_level_info(total_xp: int) -> tuple[int, float, int]:
    """Calculate level, progress, and XP to next level."""
    # Simple level system: 1000 XP per level
    level = max(1, (total_xp // 1000) + 1)
    xp_for_current_level = (level - 1) * 1000
    xp_in_current_level = total_xp - xp_for_current_level
    xp_for_next_level = 1000
    
    level_progress = xp_in_current_level / xp_for_next_level
    xp_to_next = xp_for_next_level - xp_in_current_level
    
    return level, level_progress, xp_to_next


async def _get_user_rank(user_id: str, org_id: str) -> Optional[int]:
    """Get user's rank in organization by total XP."""
    try:
        # This is a simplified implementation
        # In production, you'd want to cache this or use a more efficient query
        
        # Get all users in org with their XP
        users_response = supabase.table("profiles").select("id").eq("org_id", org_id).execute()
        
        if not users_response.data:
            return None
        
        user_xp_data = []
        for profile in users_response.data:
            xp_response = supabase.table("xp_transactions").select("xp_earned").eq("user_id", profile["id"]).execute()
            total_xp = sum(xp["xp_earned"] for xp in xp_response.data) if xp_response.data else 0
            user_xp_data.append((profile["id"], total_xp))
        
        # Sort by XP descending
        user_xp_data.sort(key=lambda x: x[1], reverse=True)
        
        # Find user's rank
        for i, (uid, _) in enumerate(user_xp_data):
            if uid == user_id:
                return i + 1
        
        return None
        
    except Exception as e:
        logger.error("Failed to get user rank", user_id=user_id, error=str(e))
        return None


async def _check_badge_criteria(user_id: str):
    """Background task to check if user has earned any new badges."""
    try:
        # Get all badges the user hasn't earned yet
        earned_badges = supabase.table("user_badges").select("badge_id").eq("user_id", user_id).execute()
        earned_badge_ids = {ub["badge_id"] for ub in earned_badges.data} if earned_badges.data else set()
        
        available_badges = supabase.table("badges").select("*").eq("is_active", True).execute()
        
        for badge in available_badges.data or []:
            if badge["id"] in earned_badge_ids:
                continue
            
            # Check if user meets criteria (simplified implementation)
            criteria = badge["criteria"]
            if await _user_meets_criteria(user_id, criteria):
                # Award badge
                user_badge_data = {
                    "user_id": user_id,
                    "badge_id": badge["id"],
                    "earned_at": datetime.utcnow().isoformat()
                }
                supabase.table("user_badges").insert(user_badge_data).execute()
                
                logger.info(
                    "Badge automatically awarded",
                    user_id=user_id,
                    badge_id=badge["id"],
                    badge_name=badge["name"]
                )
        
    except Exception as e:
        logger.error("Failed to check badge criteria", user_id=user_id, error=str(e))


async def _user_meets_criteria(user_id: str, criteria: dict) -> bool:
    """Check if user meets badge criteria."""
    try:
        criteria_type = criteria.get("type")
        target = criteria.get("target", 0)
        
        if criteria_type == "course_completion":
            # Count completed courses
            completed_courses = supabase.table("course_enrollments").select("id").eq(
                "user_id", user_id
            ).eq("status", "completed").execute()
            count = len(completed_courses.data) if completed_courses.data else 0
            return count >= target
        
        elif criteria_type == "xp_milestone":
            # Check total XP
            xp_response = supabase.table("xp_transactions").select("xp_earned").eq("user_id", user_id).execute()
            total_xp = sum(xp["xp_earned"] for xp in xp_response.data) if xp_response.data else 0
            return total_xp >= target
        
        elif criteria_type == "forum_contribution":
            # Count helpful forum answers
            helpful_answers = supabase.table("forum_answers").select("id").eq(
                "user_id", user_id
            ).eq("is_helpful", True).execute()
            count = len(helpful_answers.data) if helpful_answers.data else 0
            return count >= target
        
        # Add more criteria types as needed
        return False
        
    except Exception as e:
        logger.error("Failed to check user criteria", user_id=user_id, error=str(e))
        return False 