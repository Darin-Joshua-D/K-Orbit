"""
User management routes for K-Orbit API.
Handles user CRUD operations, search, and statistics.
"""

import os
import math
from datetime import datetime
from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from supabase import create_client, Client

from app.auth.middleware import get_current_user, require_manager, require_admin
from app.users.models import (
    UserDetailResponse,
    UserListResponse,
    UpdateUserRequest,
    UserSearchRequest,
    UserSearchResponse,
    UserStatsResponse,
    UserActivityLog
)

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()


@router.get("/search", response_model=UserSearchResponse)
async def search_users(
    query: Optional[str] = Query(None, description="Search query"),
    role: Optional[str] = Query(None, description="Filter by role"),
    department: Optional[str] = Query(None, description="Filter by department"), 
    manager_id: Optional[str] = Query(None, description="Filter by manager"),
    include_inactive: bool = Query(False, description="Include inactive users"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user: dict = Depends(get_current_user)
):
    """
    Search and filter users in the organization.
    """
    try:
        # Build query with RLS (org_id filtering handled by Supabase RLS)
        query_builder = supabase.table("profiles").select(
            "id, email, full_name, role, department, position, avatar_url, "
            "last_active, onboarding_completed"
        )
        
        # Apply filters
        if query:
            # Search in full_name, email, and department
            query_builder = query_builder.or_(
                f"full_name.ilike.%{query}%,"
                f"email.ilike.%{query}%,"
                f"department.ilike.%{query}%"
            )
        
        if role:
            query_builder = query_builder.eq("role", role)
        
        if department:
            query_builder = query_builder.eq("department", department)
            
        if manager_id:
            query_builder = query_builder.eq("manager_id", manager_id)
        
        # Handle inactive users (last_active > 30 days ago)
        if not include_inactive:
            from datetime import timedelta
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
            query_builder = query_builder.gte("last_active", thirty_days_ago)
        
        # Get total count
        count_response = query_builder.execute()
        total = len(count_response.data) if count_response.data else 0
        
        # Apply pagination
        offset = (page - 1) * limit
        paginated_response = query_builder.range(offset, offset + limit - 1).execute()
        
        users = []
        if paginated_response.data:
            for user_data in paginated_response.data:
                users.append(UserListResponse(
                    id=user_data["id"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    department=user_data.get("department"),
                    position=user_data.get("position"),
                    avatar_url=user_data.get("avatar_url"),
                    last_active=datetime.fromisoformat(user_data["last_active"]) if user_data.get("last_active") else None,
                    onboarding_completed=user_data.get("onboarding_completed", False)
                ))
        
        pages = math.ceil(total / limit) if total > 0 else 1
        
        return UserSearchResponse(
            users=users,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error("User search failed", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to search users"
        )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed user information.
    Users can only view their own profile unless they're managers/admins.
    """
    try:
        # Check permissions - users can view their own profile, managers can view team members
        if (user_id != current_user["sub"] and 
            current_user["role"] not in ["manager", "admin", "super_admin"]):
            # For regular users, check if the target user is in their team
            if current_user["role"] == "sme":
                # SMEs can view learners in their courses (simplified check)
                pass  # You might want to implement course-based access control
            else:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )
        
        # Get user profile
        user_response = supabase.table("profiles").select(
            "*, manager:manager_id(full_name)"
        ).eq("id", user_id).single().execute()
        
        if not user_response.data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        user_data = user_response.data
        
        # Get direct reports if user is a manager
        direct_reports = []
        if user_data["role"] in ["manager", "admin"]:
            reports_response = supabase.table("profiles").select(
                "id, email, full_name, role, department, position, avatar_url, "
                "last_active, onboarding_completed"
            ).eq("manager_id", user_id).execute()
            
            if reports_response.data:
                for report in reports_response.data:
                    direct_reports.append(UserListResponse(
                        id=report["id"],
                        email=report["email"],
                        full_name=report["full_name"],
                        role=report["role"],
                        department=report.get("department"),
                        position=report.get("position"),
                        avatar_url=report.get("avatar_url"),
                        last_active=datetime.fromisoformat(report["last_active"]) if report.get("last_active") else None,
                        onboarding_completed=report.get("onboarding_completed", False)
                    ))
        
        # Get user statistics
        stats = await _get_user_stats(user_id)
        
        return UserDetailResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            role=user_data["role"],
            org_id=user_data["org_id"],
            department=user_data.get("department"),
            position=user_data.get("position"),
            avatar_url=user_data.get("avatar_url"),
            manager_id=user_data.get("manager_id"),
            manager_name=user_data.get("manager", {}).get("full_name") if user_data.get("manager") else None,
            direct_reports=direct_reports,
            onboarding_completed=user_data.get("onboarding_completed", False),
            last_active=datetime.fromisoformat(user_data["last_active"]) if user_data.get("last_active") else None,
            total_xp=stats["total_xp"],
            level=stats["level"],
            badges_count=stats["badges_earned"],
            courses_completed=stats["courses_completed"],
            created_at=datetime.fromisoformat(user_data["created_at"]),
            updated_at=datetime.fromisoformat(user_data["updated_at"]) if user_data.get("updated_at") else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get user information"
        )


@router.put("/{user_id}", response_model=UserDetailResponse, dependencies=[Depends(require_manager)])
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user information (Manager+ only).
    """
    try:
        # Check if user exists and is in the same organization
        existing_user = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        
        if not existing_user.data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Prepare update data
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Update user profile
        updated_response = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        
        if not updated_response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to update user"
            )
        
        logger.info(
            "User updated",
            user_id=user_id,
            updated_by=current_user["sub"],
            updated_fields=list(update_data.keys())
        )
        
        # Return updated user details
        return await get_user(user_id, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update user"
        )


@router.delete("/{user_id}", dependencies=[Depends(require_admin)])
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete user account (Admin only).
    """
    try:
        # Check if user exists
        existing_user = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        
        if not existing_user.data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Prevent self-deletion
        if user_id == current_user["sub"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account"
            )
        
        # Soft delete - mark as inactive instead of hard delete
        supabase.table("profiles").update({
            "deleted_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        logger.info(
            "User deleted",
            user_id=user_id,
            deleted_by=current_user["sub"]
        )
        
        return {"message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete user", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user"
        )


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user statistics and progress information.
    """
    try:
        # Check permissions
        if (user_id != current_user["sub"] and 
            current_user["role"] not in ["manager", "admin", "super_admin"]):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        stats = await _get_user_stats(user_id)
        
        return UserStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user stats", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get user statistics"
        )


@router.get("/{user_id}/activity", response_model=List[UserActivityLog])
async def get_user_activity(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user activity log.
    """
    try:
        # Check permissions
        if (user_id != current_user["sub"] and 
            current_user["role"] not in ["manager", "admin", "super_admin"]):
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
        
        activity_response = supabase.table("user_activity_logs").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(limit).execute()
        
        activities = []
        if activity_response.data:
            for activity in activity_response.data:
                activities.append(UserActivityLog(
                    id=activity["id"],
                    user_id=activity["user_id"],
                    action=activity["action"],
                    resource_type=activity.get("resource_type"),
                    resource_id=activity.get("resource_id"),
                    metadata=activity.get("metadata"),
                    ip_address=activity.get("ip_address"),
                    user_agent=activity.get("user_agent"),
                    created_at=datetime.fromisoformat(activity["created_at"])
                ))
        
        return activities
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user activity", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get user activity"
        )


async def _get_user_stats(user_id: str) -> dict:
    """Helper function to get user statistics."""
    try:
        # Get XP and level
        xp_response = supabase.table("xp_transactions").select(
            "xp_earned"
        ).eq("user_id", user_id).execute()
        
        total_xp = sum(xp["xp_earned"] for xp in xp_response.data) if xp_response.data else 0
        
        # Calculate level (simple formula: every 1000 XP = 1 level)
        level = max(1, total_xp // 1000 + 1)
        level_progress = (total_xp % 1000) / 1000
        
        # Get badges count
        badges_response = supabase.table("user_badges").select("id").eq("user_id", user_id).execute()
        badges_earned = len(badges_response.data) if badges_response.data else 0
        
        # Get course completion stats
        course_completions = supabase.table("course_enrollments").select(
            "status"
        ).eq("user_id", user_id).execute()
        
        courses_completed = 0
        courses_in_progress = 0
        if course_completions.data:
            for enrollment in course_completions.data:
                if enrollment["status"] == "completed":
                    courses_completed += 1
                elif enrollment["status"] == "in_progress":
                    courses_in_progress += 1
        
        # Get forum stats
        forum_posts_response = supabase.table("forum_answers").select("id").eq("user_id", user_id).execute()
        forum_posts = len(forum_posts_response.data) if forum_posts_response.data else 0
        
        helpful_answers_response = supabase.table("forum_answers").select("id").eq(
            "user_id", user_id
        ).eq("is_helpful", True).execute()
        forum_helpful_answers = len(helpful_answers_response.data) if helpful_answers_response.data else 0
        
        # Calculate login streak (simplified - you might want to implement proper streak logic)
        login_streak = 1  # Placeholder
        
        # Get last activity
        user_response = supabase.table("profiles").select("last_active").eq("id", user_id).single().execute()
        last_activity = None
        if user_response.data and user_response.data.get("last_active"):
            last_activity = datetime.fromisoformat(user_response.data["last_active"])
        
        return {
            "user_id": user_id,
            "total_xp": total_xp,
            "level": level,
            "level_progress": level_progress,
            "badges_earned": badges_earned,
            "courses_completed": courses_completed,
            "courses_in_progress": courses_in_progress,
            "forum_posts": forum_posts,
            "forum_helpful_answers": forum_helpful_answers,
            "login_streak": login_streak,
            "last_activity": last_activity
        }
        
    except Exception as e:
        logger.error("Failed to calculate user stats", user_id=user_id, error=str(e))
        return {
            "user_id": user_id,
            "total_xp": 0,
            "level": 1,
            "level_progress": 0.0,
            "badges_earned": 0,
            "courses_completed": 0,
            "courses_in_progress": 0,
            "forum_posts": 0,
            "forum_helpful_answers": 0,
            "login_streak": 0,
            "last_activity": None
        } 