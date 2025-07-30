"""
Pydantic models for course management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator


class CourseStatus(str, Enum):
    """Course status enumeration."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EnrollmentStatus(str, Enum):
    """Enrollment status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"


class LessonType(str, Enum):
    """Lesson type enumeration."""
    VIDEO = "video"
    READING = "reading"
    QUIZ = "quiz"
    INTERACTIVE = "interactive"
    ASSIGNMENT = "assignment"


class CreateCourseRequest(BaseModel):
    """Create course request model."""
    title: str = Field(..., min_length=3, max_length=200, description="Course title")
    description: str = Field(..., min_length=10, description="Course description")
    category: str = Field(..., description="Course category")
    difficulty_level: str = Field(..., description="Course difficulty level")
    estimated_duration: int = Field(..., gt=0, description="Estimated duration in minutes")
    tags: List[str] = Field(default=[], description="Course tags")
    prerequisites: List[str] = Field(default=[], description="Course prerequisites")
    learning_objectives: List[str] = Field(default=[], description="Learning objectives")
    is_mandatory: bool = Field(default=False, description="Whether course is mandatory")
    auto_enroll_roles: List[str] = Field(default=[], description="Roles to auto-enroll")
    
    @validator("difficulty_level")
    def validate_difficulty(cls, v):
        allowed_levels = ["beginner", "intermediate", "advanced"]
        if v not in allowed_levels:
            raise ValueError(f"Difficulty level must be one of: {allowed_levels}")
        return v


class UpdateCourseRequest(BaseModel):
    """Update course request model."""
    title: Optional[str] = Field(None, min_length=3, max_length=200, description="Course title")
    description: Optional[str] = Field(None, min_length=10, description="Course description")
    category: Optional[str] = Field(None, description="Course category")
    difficulty_level: Optional[str] = Field(None, description="Course difficulty level")
    estimated_duration: Optional[int] = Field(None, gt=0, description="Estimated duration in minutes")
    tags: Optional[List[str]] = Field(None, description="Course tags")
    prerequisites: Optional[List[str]] = Field(None, description="Course prerequisites")
    learning_objectives: Optional[List[str]] = Field(None, description="Learning objectives")
    is_mandatory: Optional[bool] = Field(None, description="Whether course is mandatory")
    auto_enroll_roles: Optional[List[str]] = Field(None, description="Roles to auto-enroll")
    status: Optional[CourseStatus] = Field(None, description="Course status")


class LessonRequest(BaseModel):
    """Lesson request model."""
    title: str = Field(..., min_length=3, max_length=200, description="Lesson title")
    content: str = Field(..., description="Lesson content")
    lesson_type: LessonType = Field(..., description="Lesson type")
    order_index: int = Field(..., ge=0, description="Lesson order in course")
    duration: int = Field(..., gt=0, description="Lesson duration in minutes")
    is_required: bool = Field(default=True, description="Whether lesson is required")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Lesson metadata")


class CourseResponse(BaseModel):
    """Course response model."""
    id: str = Field(..., description="Course ID")
    title: str = Field(..., description="Course title")
    description: str = Field(..., description="Course description")
    category: str = Field(..., description="Course category")
    difficulty_level: str = Field(..., description="Course difficulty level")
    estimated_duration: int = Field(..., description="Estimated duration in minutes")
    tags: List[str] = Field(..., description="Course tags")
    prerequisites: List[str] = Field(..., description="Course prerequisites")
    learning_objectives: List[str] = Field(..., description="Learning objectives")
    is_mandatory: bool = Field(..., description="Whether course is mandatory")
    auto_enroll_roles: List[str] = Field(..., description="Roles to auto-enroll")
    status: CourseStatus = Field(..., description="Course status")
    author_id: str = Field(..., description="Course author ID")
    author_name: str = Field(..., description="Course author name")
    thumbnail_url: Optional[str] = Field(None, description="Course thumbnail URL")
    total_lessons: int = Field(default=0, description="Total number of lessons")
    total_enrollments: int = Field(default=0, description="Total number of enrollments")
    avg_rating: Optional[float] = Field(None, description="Average course rating")
    created_at: datetime = Field(..., description="Course creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    published_at: Optional[datetime] = Field(None, description="Course publication timestamp")


class LessonResponse(BaseModel):
    """Lesson response model."""
    id: str = Field(..., description="Lesson ID")
    course_id: str = Field(..., description="Course ID")
    title: str = Field(..., description="Lesson title")
    content: str = Field(..., description="Lesson content")
    lesson_type: LessonType = Field(..., description="Lesson type")
    order_index: int = Field(..., description="Lesson order in course")
    duration: int = Field(..., description="Lesson duration in minutes")
    is_required: bool = Field(..., description="Whether lesson is required")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Lesson metadata")
    created_at: datetime = Field(..., description="Lesson creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class EnrollmentResponse(BaseModel):
    """Course enrollment response model."""
    id: str = Field(..., description="Enrollment ID")
    course_id: str = Field(..., description="Course ID")
    user_id: str = Field(..., description="User ID")
    status: EnrollmentStatus = Field(..., description="Enrollment status")
    progress_percentage: float = Field(default=0.0, description="Course progress percentage")
    current_lesson_id: Optional[str] = Field(None, description="Current lesson ID")
    completed_lessons: List[str] = Field(default=[], description="List of completed lesson IDs")
    time_spent: int = Field(default=0, description="Time spent on course in minutes")
    started_at: Optional[datetime] = Field(None, description="Course start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Course completion timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    created_at: datetime = Field(..., description="Enrollment creation timestamp")


class LessonProgressResponse(BaseModel):
    """Lesson progress response model."""
    lesson_id: str = Field(..., description="Lesson ID")
    user_id: str = Field(..., description="User ID")
    status: str = Field(..., description="Lesson status (not_started, in_progress, completed)")
    progress_percentage: float = Field(default=0.0, description="Lesson progress percentage")
    time_spent: int = Field(default=0, description="Time spent on lesson in minutes")
    completed_at: Optional[datetime] = Field(None, description="Lesson completion timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")


class CourseSearchRequest(BaseModel):
    """Course search request model."""
    query: Optional[str] = Field(None, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    difficulty_level: Optional[str] = Field(None, description="Filter by difficulty level")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    status: Optional[CourseStatus] = Field(None, description="Filter by status")
    author_id: Optional[str] = Field(None, description="Filter by author")
    is_mandatory: Optional[bool] = Field(None, description="Filter by mandatory status")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")


class CourseSearchResponse(BaseModel):
    """Course search response model."""
    courses: List[CourseResponse] = Field(..., description="List of courses")
    total: int = Field(..., description="Total number of courses")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class CourseRatingRequest(BaseModel):
    """Course rating request model."""
    rating: int = Field(..., ge=1, le=5, description="Course rating (1-5)")
    review: Optional[str] = Field(None, max_length=1000, description="Course review text")


class CourseRatingResponse(BaseModel):
    """Course rating response model."""
    id: str = Field(..., description="Rating ID")
    course_id: str = Field(..., description="Course ID")
    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    rating: int = Field(..., description="Course rating")
    review: Optional[str] = Field(None, description="Course review text")
    created_at: datetime = Field(..., description="Rating creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class UpdateLessonProgressRequest(BaseModel):
    """Update lesson progress request model."""
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    time_spent: int = Field(..., ge=0, description="Time spent in minutes")
    completed: bool = Field(default=False, description="Whether lesson is completed") 