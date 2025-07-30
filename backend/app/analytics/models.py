"""
Analytics models for K-Orbit API.
Pydantic models for analytics requests and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProgressMetrics(BaseModel):
    """User progress metrics."""
    total_courses: int = Field(..., description="Total number of enrolled courses")
    completed_courses: int = Field(..., description="Number of completed courses")
    completion_rate: float = Field(..., description="Course completion rate (0-1)")
    total_xp_earned: int = Field(..., description="Total XP earned in period")
    average_progress: float = Field(..., description="Average progress across all courses")


class UserProgressResponse(BaseModel):
    """Response model for user progress analytics."""
    user_id: str = Field(..., description="User ID")
    period: str = Field(..., description="Time period")
    metrics: ProgressMetrics = Field(..., description="Calculated metrics")
    course_progress: List[Dict[str, Any]] = Field(..., description="Course progress details")
    xp_timeline: List[Dict[str, Any]] = Field(..., description="XP earning timeline")


class OrganizationOverview(BaseModel):
    """Organization overview metrics."""
    total_users: int = Field(..., description="Total users in organization")
    active_learners: int = Field(..., description="Active learners in period")
    engagement_rate: float = Field(..., description="Engagement rate (0-1)")


class OrganizationInsightsResponse(BaseModel):
    """Response model for organization insights."""
    organization_id: str = Field(..., description="Organization ID")
    period: str = Field(..., description="Time period")
    overview: OrganizationOverview = Field(..., description="Overview metrics")
    course_performance: List[Dict[str, Any]] = Field(..., description="Course performance data")
    top_performers: List[Dict[str, Any]] = Field(..., description="Top performing users")


class TrendData(BaseModel):
    """Learning trend data."""
    daily_engagement: List[Dict[str, Any]] = Field(..., description="Daily engagement trends")
    completion_rates: List[Dict[str, Any]] = Field(..., description="Completion rates by category")
    popular_topics: List[Dict[str, Any]] = Field(..., description="Popular learning topics")


class LearningTrendsResponse(BaseModel):
    """Response model for learning trends."""
    period: str = Field(..., description="Time period")
    trends: TrendData = Field(..., description="Trend analysis data")
    raw_data: List[Dict[str, Any]] = Field(..., description="Raw analytics data")


class ReportSummary(BaseModel):
    """Report summary metrics."""
    total_activities: int = Field(..., description="Total learning activities")
    unique_users: int = Field(..., description="Number of unique active users")
    average_daily_engagement: float = Field(..., description="Average daily engagement")


class EngagementReportResponse(BaseModel):
    """Response model for engagement reports."""
    report_type: str = Field(..., description="Type of report")
    period: Dict[str, str] = Field(..., description="Report period")
    organization_id: str = Field(..., description="Organization ID")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    summary: ReportSummary = Field(..., description="Report summary")
    detailed_data: List[Dict[str, Any]] = Field(..., description="Detailed engagement data")


class LearningAnalytic(BaseModel):
    """Learning analytics record."""
    id: str = Field(..., description="Analytics record ID")
    user_id: str = Field(..., description="User ID")
    course_id: Optional[str] = Field(None, description="Course ID if applicable")
    lesson_id: Optional[str] = Field(None, description="Lesson ID if applicable")
    metric_name: str = Field(..., description="Name of the metric")
    metric_value: float = Field(..., description="Metric value")
    metric_unit: Optional[str] = Field(None, description="Unit of measurement")
    recorded_at: datetime = Field(..., description="When the metric was recorded")
    org_id: str = Field(..., description="Organization ID")


class InterventionAlert(BaseModel):
    """Intervention alert for at-risk learners."""
    id: str = Field(..., description="Alert ID")
    user_id: str = Field(..., description="User ID")
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(..., description="Alert severity level")
    message: str = Field(..., description="Alert message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional alert data")
    is_resolved: bool = Field(default=False, description="Whether alert is resolved")
    created_at: datetime = Field(..., description="Alert creation timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution timestamp")


class CreateAnalyticRequest(BaseModel):
    """Request to create analytics record."""
    metric_name: str = Field(..., description="Name of the metric")
    metric_value: float = Field(..., description="Metric value")
    metric_unit: Optional[str] = Field(None, description="Unit of measurement")
    course_id: Optional[str] = Field(None, description="Course ID if applicable")
    lesson_id: Optional[str] = Field(None, description="Lesson ID if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metric data")


class AnalyticsHealthResponse(BaseModel):
    """Health check response for analytics service."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp") 