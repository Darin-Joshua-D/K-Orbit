"""
Pydantic models for AI agent functionality.
Handles chat conversations, knowledge queries, and AI responses.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the AI")


class ChatMessageResponse(BaseModel):
    """Response model for AI chat message."""
    id: str = Field(..., description="Message ID")
    conversation_id: str = Field(..., description="Conversation ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    created_at: datetime = Field(..., description="Message timestamp")


class ConversationResponse(BaseModel):
    """Response model for conversation details."""
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    summary: Optional[str] = Field(None, description="Conversation summary")
    message_count: int = Field(..., description="Number of messages")
    last_message_at: datetime = Field(..., description="Last message timestamp")
    created_at: datetime = Field(..., description="Conversation creation timestamp")


class KnowledgeQueryRequest(BaseModel):
    """Request model for knowledge base queries."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


class KnowledgeResult(BaseModel):
    """Model for knowledge search result."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content excerpt")
    source_type: str = Field(..., description="Source type (course, lesson, upload, etc.)")
    source_id: Optional[str] = Field(None, description="Source entity ID")
    similarity_score: float = Field(..., description="Similarity score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")


class KnowledgeQueryResponse(BaseModel):
    """Response model for knowledge queries."""
    query: str = Field(..., description="Original query")
    results: List[KnowledgeResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    processing_time_ms: int = Field(..., description="Query processing time in milliseconds")


class DocumentEmbeddingRequest(BaseModel):
    """Request model for creating document embeddings."""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    source_type: str = Field(..., description="Source type")
    source_id: Optional[str] = Field(None, description="Source entity ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DocumentEmbeddingResponse(BaseModel):
    """Response model for document embedding creation."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    status: str = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Creation timestamp")


class AIInsightRequest(BaseModel):
    """Request model for AI-generated insights."""
    scope: str = Field(..., description="Insight scope (user, course, organization)")
    target_id: str = Field(..., description="Target ID for insights")
    insight_type: str = Field(..., description="Type of insight requested")
    time_range: Optional[str] = Field(None, description="Time range for analysis")


class AIInsight(BaseModel):
    """Model for AI-generated insight."""
    type: str = Field(..., description="Insight type")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    recommendations: List[str] = Field(default=[], description="Actionable recommendations")
    data: Optional[Dict[str, Any]] = Field(None, description="Supporting data")


class AIInsightResponse(BaseModel):
    """Response model for AI insights."""
    insights: List[AIInsight] = Field(..., description="Generated insights")
    summary: str = Field(..., description="Summary of insights")
    generated_at: datetime = Field(..., description="Generation timestamp")
    processing_time_ms: int = Field(..., description="Processing time")


class LearningPathRequest(BaseModel):
    """Request model for AI-generated learning paths."""
    user_id: Optional[str] = Field(None, description="Target user ID")
    role: Optional[str] = Field(None, description="Target role")
    goals: List[str] = Field(default=[], description="Learning goals")
    current_skills: List[str] = Field(default=[], description="Current skills")
    time_commitment: Optional[int] = Field(None, description="Available time per week (hours)")
    difficulty_preference: Optional[str] = Field(None, description="Preferred difficulty level")


class LearningPathStep(BaseModel):
    """Model for a step in a learning path."""
    order: int = Field(..., description="Step order")
    course_id: str = Field(..., description="Course ID")
    course_title: str = Field(..., description="Course title")
    estimated_duration: int = Field(..., description="Estimated duration in hours")
    difficulty: str = Field(..., description="Difficulty level")
    prerequisites: List[str] = Field(default=[], description="Prerequisites")
    reasoning: str = Field(..., description="Why this step is recommended")


class LearningPathResponse(BaseModel):
    """Response model for AI-generated learning paths."""
    id: str = Field(..., description="Learning path ID")
    title: str = Field(..., description="Path title")
    description: str = Field(..., description="Path description")
    estimated_duration: int = Field(..., description="Total estimated duration in hours")
    difficulty: str = Field(..., description="Overall difficulty level")
    steps: List[LearningPathStep] = Field(..., description="Learning path steps")
    rationale: str = Field(..., description="Why this path was recommended")
    generated_at: datetime = Field(..., description="Generation timestamp")


class ContentSuggestionRequest(BaseModel):
    """Request model for AI content suggestions."""
    content_type: str = Field(..., description="Type of content to suggest")
    topic: str = Field(..., description="Content topic")
    target_audience: str = Field(..., description="Target audience")
    difficulty_level: str = Field(..., description="Difficulty level")
    duration: Optional[int] = Field(None, description="Desired duration in minutes")
    format_preferences: List[str] = Field(default=[], description="Preferred content formats")


class ContentSuggestion(BaseModel):
    """Model for AI content suggestion."""
    title: str = Field(..., description="Suggested title")
    description: str = Field(..., description="Content description")
    outline: List[str] = Field(..., description="Content outline")
    format: str = Field(..., description="Recommended format")
    estimated_duration: int = Field(..., description="Estimated duration")
    difficulty: str = Field(..., description="Difficulty level")
    resources: List[str] = Field(default=[], description="Suggested resources")


class ContentSuggestionResponse(BaseModel):
    """Response model for content suggestions."""
    suggestions: List[ContentSuggestion] = Field(..., description="Content suggestions")
    topic: str = Field(..., description="Original topic")
    rationale: str = Field(..., description="Why these suggestions were made")
    generated_at: datetime = Field(..., description="Generation timestamp")


class QuizGenerationRequest(BaseModel):
    """Request model for AI quiz generation."""
    content: str = Field(..., description="Content to generate quiz from")
    num_questions: int = Field(default=5, ge=1, le=20, description="Number of questions")
    question_types: List[str] = Field(default=["multiple_choice"], description="Types of questions")
    difficulty: str = Field(default="intermediate", description="Question difficulty")


class QuizQuestion(BaseModel):
    """Model for a generated quiz question."""
    question: str = Field(..., description="Question text")
    type: str = Field(..., description="Question type")
    options: Optional[List[str]] = Field(None, description="Answer options (for multiple choice)")
    correct_answer: str = Field(..., description="Correct answer")
    explanation: str = Field(..., description="Answer explanation")
    difficulty: str = Field(..., description="Question difficulty")


class QuizGenerationResponse(BaseModel):
    """Response model for quiz generation."""
    questions: List[QuizQuestion] = Field(..., description="Generated questions")
    metadata: Dict[str, Any] = Field(default={}, description="Quiz metadata")
    generated_at: datetime = Field(..., description="Generation timestamp")


class AIFeedbackRequest(BaseModel):
    """Request model for AI feedback on user responses."""
    question: str = Field(..., description="Original question")
    user_answer: str = Field(..., description="User's answer")
    correct_answer: str = Field(..., description="Correct answer")
    context: Optional[str] = Field(None, description="Additional context")


class AIFeedbackResponse(BaseModel):
    """Response model for AI feedback."""
    feedback: str = Field(..., description="Feedback message")
    is_correct: bool = Field(..., description="Whether answer is correct")
    score: Optional[float] = Field(None, description="Answer score (0-1)")
    suggestions: List[str] = Field(default=[], description="Improvement suggestions")
    additional_resources: List[str] = Field(default=[], description="Additional learning resources")


class StreamingChatResponse(BaseModel):
    """Response model for streaming chat."""
    chunk: str = Field(..., description="Text chunk")
    is_complete: bool = Field(..., description="Whether this is the final chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Chunk metadata") 