"""
Analytics routes for K-Orbit API.
Handles learning analytics, user progress insights, and reporting.
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Depends, Query
from supabase import create_client, Client

from app.auth.middleware import get_current_user, require_manager

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()


@router.get("/user-progress")
async def get_user_progress(
    user_id: Optional[str] = Query(None, description="User ID (managers only)"),
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    user: dict = Depends(get_current_user)
):
    """
    Get user learning progress analytics.
    """
    try:
        # Determine target user
        target_user_id = user_id if user_id and user.get("role") == "manager" else user["sub"]
        
        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get course progress
        course_progress = supabase.table("course_enrollments").select(
            "course_id, courses(title), progress_percentage, completed_at, enrolled_at"
        ).eq("user_id", target_user_id).gte("enrolled_at", start_date).execute()
        
        # Get XP progress
        xp_progress = supabase.table("xp_transactions").select(
            "amount, created_at"
        ).eq("user_id", target_user_id).gte("created_at", start_date).execute()
        
        # Calculate metrics
        total_courses = len(course_progress.data)
        completed_courses = len([c for c in course_progress.data if c.get("completed_at")])
        total_xp = sum([x["amount"] for x in xp_progress.data])
        avg_progress = sum([c["progress_percentage"] for c in course_progress.data]) / max(total_courses, 1)
        
        return {
            "user_id": target_user_id,
            "period": period,
            "metrics": {
                "total_courses": total_courses,
                "completed_courses": completed_courses,
                "completion_rate": completed_courses / max(total_courses, 1),
                "total_xp_earned": total_xp,
                "average_progress": round(avg_progress, 2)
            },
            "course_progress": course_progress.data,
            "xp_timeline": xp_progress.data
        }
        
    except Exception as e:
        logger.error("Failed to get user progress", error=str(e), user_id=target_user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve progress data")


@router.get("/organization-insights")
async def get_organization_insights(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    user: dict = Depends(require_manager)
):
    """
    Get organization-wide learning insights (managers only).
    """
    try:
        org_id = user["org_id"]
        
        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get organization stats
        total_users = supabase.table("profiles").select("id", count="exact").eq("org_id", org_id).execute()
        active_learners = supabase.table("course_enrollments").select(
            "user_id", count="exact"
        ).eq("profiles.org_id", org_id).gte("enrolled_at", start_date).execute()
        
        # Get course completion rates
        course_stats = supabase.table("courses").select(
            "id, title, enrollments:course_enrollments(count), completions:course_enrollments(count)"
        ).eq("org_id", org_id).execute()
        
        # Get top performers
        top_performers = supabase.table("profiles").select(
            "id, full_name, user_stats(total_xp, level)"
        ).eq("org_id", org_id).order("user_stats.total_xp", desc=True).limit(10).execute()
        
        return {
            "organization_id": org_id,
            "period": period,
            "overview": {
                "total_users": total_users.count,
                "active_learners": active_learners.count,
                "engagement_rate": active_learners.count / max(total_users.count, 1)
            },
            "course_performance": course_stats.data,
            "top_performers": top_performers.data
        }
        
    except Exception as e:
        logger.error("Failed to get organization insights", error=str(e), org_id=user.get("org_id"))
        raise HTTPException(status_code=500, detail="Failed to retrieve organization insights")


@router.get("/learning-trends")
async def get_learning_trends(
    period: str = Query("30d", description="Time period: 7d, 30d, 90d"),
    user: dict = Depends(get_current_user)
):
    """
    Get learning trends and patterns.
    """
    try:
        # Get data based on user role
        if user.get("role") == "manager":
            # Organization-wide trends
            org_filter = f"profiles.org_id.eq.{user['org_id']}"
        else:
            # Personal trends
            org_filter = f"user_id.eq.{user['sub']}"
        
        # Calculate date range
        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get daily activity
        daily_activity = supabase.table("learning_analytics").select(
            "recorded_at, metric_name, metric_value"
        ).gte("recorded_at", start_date).execute()
        
        # Mock trend data (in production, calculate from real data)
        trends = {
            "daily_engagement": [
                {"date": "2024-01-01", "value": 85},
                {"date": "2024-01-02", "value": 92},
                {"date": "2024-01-03", "value": 78},
                {"date": "2024-01-04", "value": 88},
                {"date": "2024-01-05", "value": 95}
            ],
            "completion_rates": [
                {"category": "Technical Skills", "rate": 78},
                {"category": "Soft Skills", "rate": 85},
                {"category": "Compliance", "rate": 92},
                {"category": "Leadership", "rate": 71}
            ],
            "popular_topics": [
                {"topic": "React Development", "enrollments": 156},
                {"topic": "Data Analysis", "enrollments": 134},
                {"topic": "Communication", "enrollments": 128},
                {"topic": "Project Management", "enrollments": 98}
            ]
        }
        
        return {
            "period": period,
            "trends": trends,
            "raw_data": daily_activity.data[:50]  # Limit for performance
        }
        
    except Exception as e:
        logger.error("Failed to get learning trends", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve learning trends")


@router.get("/reports/engagement")
async def get_engagement_report(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    user: dict = Depends(require_manager)
):
    """
    Generate detailed engagement report (managers only).
    """
    try:
        org_id = user["org_id"]
        
        # Get engagement metrics
        engagement_data = supabase.table("learning_analytics").select(
            "user_id, profiles(full_name), metric_name, metric_value, recorded_at"
        ).eq("org_id", org_id).gte("recorded_at", start_date).lte("recorded_at", end_date).execute()
        
        # Generate report summary
        report = {
            "report_type": "engagement",
            "period": {"start": start_date, "end": end_date},
            "organization_id": org_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_activities": len(engagement_data.data),
                "unique_users": len(set([d["user_id"] for d in engagement_data.data])),
                "average_daily_engagement": len(engagement_data.data) / max(1, 
                    (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days)
            },
            "detailed_data": engagement_data.data[:100]  # Limit for performance
        }
        
        return report
        
    except Exception as e:
        logger.error("Failed to generate engagement report", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/health")
async def analytics_health():
    """
    Health check for analytics service.
    """
    return {
        "status": "healthy",
        "service": "analytics",
        "timestamp": datetime.utcnow().isoformat()
    } 