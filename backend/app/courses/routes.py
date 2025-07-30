"""
Course management routes for K-Orbit API.
Handles course CRUD operations, enrollments, and progress tracking.
"""

import os
import math
from datetime import datetime
from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends, Query, BackgroundTasks
from supabase import create_client, Client

from app.auth.middleware import get_current_user, require_sme, require_manager
from app.courses.models import (
    CreateCourseRequest,
    UpdateCourseRequest,
    CourseResponse,
    LessonRequest,
    LessonResponse,
    EnrollmentResponse,
    LessonProgressResponse,
    CourseSearchRequest,
    CourseSearchResponse,
    CourseRatingRequest,
    CourseRatingResponse,
    UpdateLessonProgressRequest
)

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()


@router.get("/", response_model=CourseSearchResponse)
async def search_courses(
    query: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty"),
    status: Optional[str] = Query("published", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user: dict = Depends(get_current_user)
):
    """
    Search and filter courses.
    """
    try:
        # Build query
        query_builder = supabase.table("courses").select(
            "id, title, description, category, difficulty_level, estimated_duration, "
            "tags, prerequisites, learning_objectives, is_mandatory, status, "
            "author_id, thumbnail_url, created_at, updated_at, published_at, "
            "profiles!courses_author_id_fkey(full_name)"
        ).eq("org_id", user["org_id"])

        # Apply filters
        if query:
            query_builder = query_builder.or_(
                f"title.ilike.%{query}%,"
                f"description.ilike.%{query}%,"
                f"category.ilike.%{query}%"
            )
        
        if category:
            query_builder = query_builder.eq("category", category)
            
        if difficulty_level:
            query_builder = query_builder.eq("difficulty_level", difficulty_level)
            
        # Status filter - regular users only see published courses
        if user["role"] in ["admin", "sme"] and status:
            query_builder = query_builder.eq("status", status)
        else:
            query_builder = query_builder.eq("status", "published")

        # Get total count
        count_response = query_builder.execute()
        total = len(count_response.data) if count_response.data else 0
        
        # Apply pagination
        offset = (page - 1) * limit
        paginated_response = query_builder.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        courses = []
        if paginated_response.data:
            for course_data in paginated_response.data:
                # Get course statistics
                stats = await _get_course_stats(course_data["id"])
                
                courses.append(CourseResponse(
                    id=course_data["id"],
                    title=course_data["title"],
                    description=course_data["description"],
                    category=course_data["category"],
                    difficulty_level=course_data["difficulty_level"],
                    estimated_duration=course_data["estimated_duration"],
                    tags=course_data.get("tags", []),
                    prerequisites=course_data.get("prerequisites", []),
                    learning_objectives=course_data.get("learning_objectives", []),
                    is_mandatory=course_data["is_mandatory"],
                    auto_enroll_roles=course_data.get("auto_enroll_roles", []),
                    status=course_data["status"],
                    author_id=course_data["author_id"],
                    author_name=course_data.get("profiles", {}).get("full_name", "Unknown"),
                    thumbnail_url=course_data.get("thumbnail_url"),
                    total_lessons=stats["total_lessons"],
                    total_enrollments=stats["total_enrollments"],
                    avg_rating=stats["avg_rating"],
                    created_at=datetime.fromisoformat(course_data["created_at"]),
                    updated_at=datetime.fromisoformat(course_data["updated_at"]) if course_data.get("updated_at") else None,
                    published_at=datetime.fromisoformat(course_data["published_at"]) if course_data.get("published_at") else None
                ))
        
        pages = math.ceil(total / limit) if total > 0 else 1
        
        return CourseSearchResponse(
            courses=courses,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error("Course search failed", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to search courses"
        )


@router.post("/", response_model=CourseResponse, dependencies=[Depends(require_sme)])
async def create_course(
    request: CreateCourseRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a new course (SME+ only).
    """
    try:
        course_data = {
            "title": request.title,
            "description": request.description,
            "category": request.category,
            "difficulty_level": request.difficulty_level,
            "estimated_duration": request.estimated_duration,
            "tags": request.tags,
            "prerequisites": request.prerequisites,
            "learning_objectives": request.learning_objectives,
            "is_mandatory": request.is_mandatory,
            "auto_enroll_roles": request.auto_enroll_roles,
            "status": "draft",
            "author_id": user["sub"],
            "org_id": user["org_id"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("courses").insert(course_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create course"
            )
        
        course = response.data[0]
        
        logger.info(
            "Course created",
            course_id=course["id"],
            title=course["title"],
            author_id=user["sub"]
        )
        
        return CourseResponse(
            id=course["id"],
            title=course["title"],
            description=course["description"],
            category=course["category"],
            difficulty_level=course["difficulty_level"],
            estimated_duration=course["estimated_duration"],
            tags=course.get("tags", []),
            prerequisites=course.get("prerequisites", []),
            learning_objectives=course.get("learning_objectives", []),
            is_mandatory=course["is_mandatory"],
            auto_enroll_roles=course.get("auto_enroll_roles", []),
            status=course["status"],
            author_id=course["author_id"],
            author_name=user.get("full_name", "Unknown"),
            thumbnail_url=course.get("thumbnail_url"),
            total_lessons=0,
            total_enrollments=0,
            avg_rating=None,
            created_at=datetime.fromisoformat(course["created_at"]),
            updated_at=datetime.fromisoformat(course["updated_at"]) if course.get("updated_at") else None,
            published_at=None
        )
        
    except Exception as e:
        logger.error("Course creation failed", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to create course"
        )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get course details.
    """
    try:
        # Get course with author info
        response = supabase.table("courses").select(
            "*, profiles!courses_author_id_fkey(full_name)"
        ).eq("id", course_id).eq("org_id", user["org_id"]).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course_data = response.data
        
        # Check access permissions
        if (course_data["status"] != "published" and 
            course_data["author_id"] != user["sub"] and 
            user["role"] not in ["admin"]):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get course statistics
        stats = await _get_course_stats(course_id)
        
        return CourseResponse(
            id=course_data["id"],
            title=course_data["title"],
            description=course_data["description"],
            category=course_data["category"],
            difficulty_level=course_data["difficulty_level"],
            estimated_duration=course_data["estimated_duration"],
            tags=course_data.get("tags", []),
            prerequisites=course_data.get("prerequisites", []),
            learning_objectives=course_data.get("learning_objectives", []),
            is_mandatory=course_data["is_mandatory"],
            auto_enroll_roles=course_data.get("auto_enroll_roles", []),
            status=course_data["status"],
            author_id=course_data["author_id"],
            author_name=course_data.get("profiles", {}).get("full_name", "Unknown"),
            thumbnail_url=course_data.get("thumbnail_url"),
            total_lessons=stats["total_lessons"],
            total_enrollments=stats["total_enrollments"],
            avg_rating=stats["avg_rating"],
            created_at=datetime.fromisoformat(course_data["created_at"]),
            updated_at=datetime.fromisoformat(course_data["updated_at"]) if course_data.get("updated_at") else None,
            published_at=datetime.fromisoformat(course_data["published_at"]) if course_data.get("published_at") else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get course", course_id=course_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve course"
        )


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    request: UpdateCourseRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update course (Author or Admin only).
    """
    try:
        # Check if user can edit this course
        course_response = supabase.table("courses").select("*").eq("id", course_id).eq("org_id", user["org_id"]).single().execute()
        
        if not course_response.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = course_response.data
        
        if course["author_id"] != user["sub"] and user["role"] not in ["admin"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Prepare update data
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Handle status changes
        if update_data.get("status") == "published" and course["status"] != "published":
            update_data["published_at"] = datetime.utcnow().isoformat()
        
        # Update course
        updated_response = supabase.table("courses").update(update_data).eq("id", course_id).execute()
        
        if not updated_response.data:
            raise HTTPException(status_code=500, detail="Failed to update course")
        
        logger.info(
            "Course updated",
            course_id=course_id,
            updated_by=user["sub"],
            updated_fields=list(update_data.keys())
        )
        
        # Return updated course
        return await get_course(course_id, user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Course update failed", course_id=course_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update course"
        )


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Enroll user in a course.
    """
    try:
        # Check if course exists and is published
        course_response = supabase.table("courses").select("*").eq("id", course_id).eq("org_id", user["org_id"]).single().execute()
        
        if not course_response.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = course_response.data
        
        if course["status"] != "published":
            raise HTTPException(status_code=400, detail="Course is not available for enrollment")
        
        # Check if already enrolled
        existing_enrollment = supabase.table("course_enrollments").select("*").eq(
            "course_id", course_id
        ).eq("user_id", user["sub"]).execute()
        
        if existing_enrollment.data:
            raise HTTPException(status_code=409, detail="Already enrolled in this course")
        
        # Create enrollment
        enrollment_data = {
            "course_id": course_id,
            "user_id": user["sub"],
            "status": "not_started",
            "progress_percentage": 0.0,
            "time_spent": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        enrollment_response = supabase.table("course_enrollments").insert(enrollment_data).execute()
        
        if not enrollment_response.data:
            raise HTTPException(status_code=500, detail="Failed to create enrollment")
        
        enrollment = enrollment_response.data[0]
        
        logger.info(
            "User enrolled in course",
            user_id=user["sub"],
            course_id=course_id,
            course_title=course["title"]
        )
        
        return EnrollmentResponse(
            id=enrollment["id"],
            course_id=enrollment["course_id"],
            user_id=enrollment["user_id"],
            status=enrollment["status"],
            progress_percentage=enrollment["progress_percentage"],
            current_lesson_id=enrollment.get("current_lesson_id"),
            completed_lessons=enrollment.get("completed_lessons", []),
            time_spent=enrollment["time_spent"],
            started_at=datetime.fromisoformat(enrollment["started_at"]) if enrollment.get("started_at") else None,
            completed_at=datetime.fromisoformat(enrollment["completed_at"]) if enrollment.get("completed_at") else None,
            last_accessed=datetime.fromisoformat(enrollment["last_accessed"]) if enrollment.get("last_accessed") else None,
            created_at=datetime.fromisoformat(enrollment["created_at"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Enrollment failed", course_id=course_id, user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to enroll in course"
        )


@router.get("/{course_id}/lessons", response_model=List[LessonResponse])
async def get_course_lessons(
    course_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get lessons for a course.
    """
    try:
        # Verify access to course
        course_response = supabase.table("courses").select("*").eq("id", course_id).eq("org_id", user["org_id"]).single().execute()
        
        if not course_response.data:
            raise HTTPException(status_code=404, detail="Course not found")
        
        course = course_response.data
        
        # Check access permissions
        if (course["status"] != "published" and 
            course["author_id"] != user["sub"] and 
            user["role"] not in ["admin"]):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get lessons
        lessons_response = supabase.table("lessons").select("*").eq("course_id", course_id).order("order_index").execute()
        
        lessons = []
        for lesson_data in lessons_response.data:
            lessons.append(LessonResponse(
                id=lesson_data["id"],
                course_id=lesson_data["course_id"],
                title=lesson_data["title"],
                content=lesson_data["content"],
                lesson_type=lesson_data["lesson_type"],
                order_index=lesson_data["order_index"],
                duration=lesson_data["duration"],
                is_required=lesson_data["is_required"],
                metadata=lesson_data.get("metadata"),
                created_at=datetime.fromisoformat(lesson_data["created_at"]),
                updated_at=datetime.fromisoformat(lesson_data["updated_at"]) if lesson_data.get("updated_at") else None
            ))
        
        return lessons
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get course lessons", course_id=course_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve lessons"
        )


async def _get_course_stats(course_id: str) -> dict:
    """Helper function to get course statistics."""
    try:
        # Get lesson count
        lessons_response = supabase.table("lessons").select("id").eq("course_id", course_id).execute()
        total_lessons = len(lessons_response.data) if lessons_response.data else 0
        
        # Get enrollment count
        enrollments_response = supabase.table("course_enrollments").select("id").eq("course_id", course_id).execute()
        total_enrollments = len(enrollments_response.data) if enrollments_response.data else 0
        
        # Get average rating
        ratings_response = supabase.table("course_ratings").select("rating").eq("course_id", course_id).execute()
        avg_rating = None
        if ratings_response.data:
            ratings = [r["rating"] for r in ratings_response.data]
            avg_rating = round(sum(ratings) / len(ratings), 2)
        
        return {
            "total_lessons": total_lessons,
            "total_enrollments": total_enrollments,
            "avg_rating": avg_rating
        }
        
    except Exception as e:
        logger.error("Failed to get course stats", course_id=course_id, error=str(e))
        return {
            "total_lessons": 0,
            "total_enrollments": 0,
            "avg_rating": None
        } 