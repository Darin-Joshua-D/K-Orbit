"""
Pydantic models for forum functionality.
Handles questions, answers, voting, and moderation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CreateQuestionRequest(BaseModel):
    """Request model for creating a forum question."""
    title: str = Field(..., min_length=5, max_length=255, description="Question title")
    content: str = Field(..., min_length=10, description="Question content")
    tags: List[str] = Field(default=[], max_items=5, description="Question tags")
    course_id: Optional[str] = Field(None, description="Related course ID")


class UpdateQuestionRequest(BaseModel):
    """Request model for updating a forum question."""
    title: Optional[str] = Field(None, min_length=5, max_length=255, description="Question title")
    content: Optional[str] = Field(None, min_length=10, description="Question content")
    tags: Optional[List[str]] = Field(None, max_items=5, description="Question tags")
    is_resolved: Optional[bool] = Field(None, description="Question resolution status")


class QuestionResponse(BaseModel):
    """Response model for forum question."""
    id: str = Field(..., description="Question ID")
    title: str = Field(..., description="Question title")
    content: str = Field(..., description="Question content")
    tags: List[str] = Field(..., description="Question tags")
    user_id: str = Field(..., description="Question author ID")
    user_name: str = Field(..., description="Question author name")
    user_avatar: Optional[str] = Field(None, description="Question author avatar")
    course_id: Optional[str] = Field(None, description="Related course ID")
    course_title: Optional[str] = Field(None, description="Related course title")
    is_resolved: bool = Field(..., description="Question resolution status")
    view_count: int = Field(..., description="Number of views")
    upvotes: int = Field(..., description="Number of upvotes")
    downvotes: int = Field(..., description="Number of downvotes")
    answer_count: int = Field(default=0, description="Number of answers")
    created_at: datetime = Field(..., description="Question creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class CreateAnswerRequest(BaseModel):
    """Request model for creating a forum answer."""
    content: str = Field(..., min_length=10, description="Answer content")


class UpdateAnswerRequest(BaseModel):
    """Request model for updating a forum answer."""
    content: str = Field(..., min_length=10, description="Answer content")


class AnswerResponse(BaseModel):
    """Response model for forum answer."""
    id: str = Field(..., description="Answer ID")
    question_id: str = Field(..., description="Question ID")
    content: str = Field(..., description="Answer content")
    user_id: str = Field(..., description="Answer author ID")
    user_name: str = Field(..., description="Answer author name")
    user_avatar: Optional[str] = Field(None, description="Answer author avatar")
    is_helpful: bool = Field(..., description="Whether answer is marked as helpful")
    is_accepted: bool = Field(..., description="Whether answer is accepted by question author")
    upvotes: int = Field(..., description="Number of upvotes")
    downvotes: int = Field(..., description="Number of downvotes")
    created_at: datetime = Field(..., description="Answer creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class QuestionDetailResponse(BaseModel):
    """Detailed response model for forum question with answers."""
    question: QuestionResponse = Field(..., description="Question details")
    answers: List[AnswerResponse] = Field(..., description="Question answers")
    user_vote: Optional[str] = Field(None, description="Current user's vote on question")


class VoteRequest(BaseModel):
    """Request model for voting."""
    vote_type: str = Field(..., description="Vote type (upvote/downvote)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "vote_type": "upvote"
            }
        }
    }


class VoteResponse(BaseModel):
    """Response model for voting."""
    target_id: str = Field(..., description="Target ID (question or answer)")
    target_type: str = Field(..., description="Target type (question or answer)")
    vote_type: str = Field(..., description="Vote type")
    upvotes: int = Field(..., description="Total upvotes")
    downvotes: int = Field(..., description="Total downvotes")


class ForumSearchRequest(BaseModel):
    """Request model for forum search."""
    query: Optional[str] = Field(None, description="Search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    course_id: Optional[str] = Field(None, description="Filter by course")
    is_resolved: Optional[bool] = Field(None, description="Filter by resolution status")
    user_id: Optional[str] = Field(None, description="Filter by user")
    sort_by: Optional[str] = Field(default="created_at", description="Sort field")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class ForumSearchResponse(BaseModel):
    """Response model for forum search."""
    questions: List[QuestionResponse] = Field(..., description="Forum questions")
    total: int = Field(..., description="Total number of questions")
    page: int = Field(..., description="Current page")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")


class ForumStatsResponse(BaseModel):
    """Response model for forum statistics."""
    total_questions: int = Field(..., description="Total questions")
    total_answers: int = Field(..., description="Total answers")
    resolved_questions: int = Field(..., description="Resolved questions")
    resolution_rate: float = Field(..., description="Resolution rate percentage")
    active_users: int = Field(..., description="Active users this month")
    popular_tags: List[dict] = Field(..., description="Popular tags with counts")


class UserForumStatsResponse(BaseModel):
    """Response model for user forum statistics."""
    user_id: str = Field(..., description="User ID")
    questions_asked: int = Field(..., description="Questions asked")
    answers_given: int = Field(..., description="Answers given")
    helpful_answers: int = Field(..., description="Helpful answers")
    accepted_answers: int = Field(..., description="Accepted answers")
    total_upvotes: int = Field(..., description="Total upvotes received")
    reputation_score: int = Field(..., description="Calculated reputation score")


class ModerationActionRequest(BaseModel):
    """Request model for moderation actions."""
    action: str = Field(..., description="Moderation action")
    reason: Optional[str] = Field(None, description="Reason for action")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "action": "mark_helpful",
                "reason": "Provides accurate and useful information"
            }
        }
    }


class TagResponse(BaseModel):
    """Response model for forum tag."""
    name: str = Field(..., description="Tag name")
    usage_count: int = Field(..., description="Number of questions with this tag")
    description: Optional[str] = Field(None, description="Tag description")


class PopularTagsResponse(BaseModel):
    """Response model for popular tags."""
    tags: List[TagResponse] = Field(..., description="Popular tags")
    period: str = Field(..., description="Time period for popularity")


class NotificationPreferencesRequest(BaseModel):
    """Request model for notification preferences."""
    email_on_answer: bool = Field(default=True, description="Email when question is answered")
    email_on_helpful: bool = Field(default=True, description="Email when answer marked helpful")
    email_on_accepted: bool = Field(default=True, description="Email when answer is accepted")
    email_digest: bool = Field(default=False, description="Weekly digest email")


class NotificationPreferencesResponse(BaseModel):
    """Response model for notification preferences."""
    user_id: str = Field(..., description="User ID")
    email_on_answer: bool = Field(..., description="Email when question is answered")
    email_on_helpful: bool = Field(..., description="Email when answer marked helpful")
    email_on_accepted: bool = Field(..., description="Email when answer is accepted")
    email_digest: bool = Field(..., description="Weekly digest email")
    updated_at: datetime = Field(..., description="Last update timestamp") 