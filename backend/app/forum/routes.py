"""
Forum routes for K-Orbit API.
Handles questions, answers, voting, and forum moderation.
"""

import os
import math
from datetime import datetime, timedelta
from typing import List, Optional
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends, Query, BackgroundTasks
from supabase import create_client, Client

from app.auth.middleware import get_current_user, require_sme, require_manager
from app.forum.models import (
    CreateQuestionRequest,
    UpdateQuestionRequest,
    QuestionResponse,
    CreateAnswerRequest,
    UpdateAnswerRequest,
    AnswerResponse,
    QuestionDetailResponse,
    VoteRequest,
    VoteResponse,
    ForumSearchRequest,
    ForumSearchResponse,
    ForumStatsResponse,
    UserForumStatsResponse,
    ModerationActionRequest
)

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()


@router.get("/questions", response_model=ForumSearchResponse)
async def search_questions(
    query: Optional[str] = Query(None, description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    course_id: Optional[str] = Query(None, description="Filter by course"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user: dict = Depends(get_current_user)
):
    """
    Search forum questions.
    """
    try:
        # Build query
        query_builder = supabase.table("forum_questions").select(
            "*, profiles!forum_questions_user_id_fkey(full_name, avatar_url), "
            "courses(title)"
        ).eq("org_id", user["org_id"])

        # Apply filters
        if query:
            query_builder = query_builder.or_(
                f"title.ilike.%{query}%,"
                f"content.ilike.%{query}%"
            )
        
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
            # Use PostgreSQL array contains operator
            query_builder = query_builder.contains("tags", tag_list)
        
        if course_id:
            query_builder = query_builder.eq("course_id", course_id)
            
        if is_resolved is not None:
            query_builder = query_builder.eq("is_resolved", is_resolved)

        # Get total count
        count_response = query_builder.execute()
        total = len(count_response.data) if count_response.data else 0
        
        # Apply sorting and pagination
        if sort_order == "asc":
            query_builder = query_builder.order(sort_by)
        else:
            query_builder = query_builder.order(sort_by, desc=True)
        
        offset = (page - 1) * limit
        paginated_response = query_builder.range(offset, offset + limit - 1).execute()
        
        questions = []
        if paginated_response.data:
            for q_data in paginated_response.data:
                # Get answer count
                answer_count = await _get_answer_count(q_data["id"])
                
                questions.append(QuestionResponse(
                    id=q_data["id"],
                    title=q_data["title"],
                    content=q_data["content"],
                    tags=q_data.get("tags", []),
                    user_id=q_data["user_id"],
                    user_name=q_data.get("profiles", {}).get("full_name", "Unknown"),
                    user_avatar=q_data.get("profiles", {}).get("avatar_url"),
                    course_id=q_data.get("course_id"),
                    course_title=q_data.get("courses", {}).get("title") if q_data.get("courses") else None,
                    is_resolved=q_data["is_resolved"],
                    view_count=q_data["view_count"],
                    upvotes=q_data["upvotes"],
                    downvotes=q_data["downvotes"],
                    answer_count=answer_count,
                    created_at=datetime.fromisoformat(q_data["created_at"]),
                    updated_at=datetime.fromisoformat(q_data["updated_at"]) if q_data.get("updated_at") else None
                ))
        
        pages = math.ceil(total / limit) if total > 0 else 1
        
        return ForumSearchResponse(
            questions=questions,
            total=total,
            page=page,
            limit=limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error("Forum search failed", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to search forum questions"
        )


@router.post("/questions", response_model=QuestionResponse)
async def create_question(
    request: CreateQuestionRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Create a new forum question.
    """
    try:
        question_data = {
            "title": request.title,
            "content": request.content,
            "tags": request.tags,
            "user_id": user["sub"],
            "course_id": request.course_id,
            "org_id": user["org_id"],
            "is_resolved": False,
            "view_count": 0,
            "upvotes": 0,
            "downvotes": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("forum_questions").insert(question_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create question")
        
        question = response.data[0]
        
        # Award XP for asking question
        background_tasks.add_task(_award_forum_xp, user["sub"], "forum_question", question["id"])
        
        logger.info(
            "Forum question created",
            question_id=question["id"],
            title=question["title"],
            user_id=user["sub"]
        )
        
        return QuestionResponse(
            id=question["id"],
            title=question["title"],
            content=question["content"],
            tags=question.get("tags", []),
            user_id=question["user_id"],
            user_name=user.get("full_name", "Unknown"),
            user_avatar=user.get("avatar_url"),
            course_id=question.get("course_id"),
            course_title=None,  # Will be populated if needed
            is_resolved=question["is_resolved"],
            view_count=question["view_count"],
            upvotes=question["upvotes"],
            downvotes=question["downvotes"],
            answer_count=0,
            created_at=datetime.fromisoformat(question["created_at"]),
            updated_at=None
        )
        
    except Exception as e:
        logger.error("Question creation failed", error=str(e), user_id=user["sub"])
        raise HTTPException(
            status_code=500,
            detail="Failed to create question"
        )


@router.get("/questions/{question_id}", response_model=QuestionDetailResponse)
async def get_question_detail(
    question_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get detailed question with answers.
    """
    try:
        # Get question with user and course info
        question_response = supabase.table("forum_questions").select(
            "*, profiles!forum_questions_user_id_fkey(full_name, avatar_url), "
            "courses(title)"
        ).eq("id", question_id).eq("org_id", user["org_id"]).single().execute()
        
        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        q_data = question_response.data
        
        # Increment view count
        supabase.table("forum_questions").update({
            "view_count": q_data["view_count"] + 1
        }).eq("id", question_id).execute()
        
        # Get answers
        answers_response = supabase.table("forum_answers").select(
            "*, profiles!forum_answers_user_id_fkey(full_name, avatar_url)"
        ).eq("question_id", question_id).order("created_at").execute()
        
        answers = []
        for a_data in answers_response.data or []:
            answers.append(AnswerResponse(
                id=a_data["id"],
                question_id=a_data["question_id"],
                content=a_data["content"],
                user_id=a_data["user_id"],
                user_name=a_data.get("profiles", {}).get("full_name", "Unknown"),
                user_avatar=a_data.get("profiles", {}).get("avatar_url"),
                is_helpful=a_data["is_helpful"],
                is_accepted=a_data["is_accepted"],
                upvotes=a_data["upvotes"],
                downvotes=a_data["downvotes"],
                created_at=datetime.fromisoformat(a_data["created_at"]),
                updated_at=datetime.fromisoformat(a_data["updated_at"]) if a_data.get("updated_at") else None
            ))
        
        # Get user's vote on question
        user_vote = await _get_user_vote(user["sub"], "question", question_id)
        
        question = QuestionResponse(
            id=q_data["id"],
            title=q_data["title"],
            content=q_data["content"],
            tags=q_data.get("tags", []),
            user_id=q_data["user_id"],
            user_name=q_data.get("profiles", {}).get("full_name", "Unknown"),
            user_avatar=q_data.get("profiles", {}).get("avatar_url"),
            course_id=q_data.get("course_id"),
            course_title=q_data.get("courses", {}).get("title") if q_data.get("courses") else None,
            is_resolved=q_data["is_resolved"],
            view_count=q_data["view_count"] + 1,  # Updated count
            upvotes=q_data["upvotes"],
            downvotes=q_data["downvotes"],
            answer_count=len(answers),
            created_at=datetime.fromisoformat(q_data["created_at"]),
            updated_at=datetime.fromisoformat(q_data["updated_at"]) if q_data.get("updated_at") else None
        )
        
        return QuestionDetailResponse(
            question=question,
            answers=answers,
            user_vote=user_vote
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get question detail", question_id=question_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve question"
        )


@router.post("/questions/{question_id}/answers", response_model=AnswerResponse)
async def create_answer(
    question_id: str,
    request: CreateAnswerRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """
    Create an answer to a question.
    """
    try:
        # Verify question exists and user has access
        question_response = supabase.table("forum_questions").select("*").eq(
            "id", question_id
        ).eq("org_id", user["org_id"]).single().execute()
        
        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        answer_data = {
            "question_id": question_id,
            "content": request.content,
            "user_id": user["sub"],
            "is_helpful": False,
            "is_accepted": False,
            "upvotes": 0,
            "downvotes": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        answer_response = supabase.table("forum_answers").insert(answer_data).execute()
        
        if not answer_response.data:
            raise HTTPException(status_code=500, detail="Failed to create answer")
        
        answer = answer_response.data[0]
        
        # Award XP for answering
        background_tasks.add_task(_award_forum_xp, user["sub"], "forum_answer", answer["id"])
        
        logger.info(
            "Forum answer created",
            answer_id=answer["id"],
            question_id=question_id,
            user_id=user["sub"]
        )
        
        return AnswerResponse(
            id=answer["id"],
            question_id=answer["question_id"],
            content=answer["content"],
            user_id=answer["user_id"],
            user_name=user.get("full_name", "Unknown"),
            user_avatar=user.get("avatar_url"),
            is_helpful=answer["is_helpful"],
            is_accepted=answer["is_accepted"],
            upvotes=answer["upvotes"],
            downvotes=answer["downvotes"],
            created_at=datetime.fromisoformat(answer["created_at"]),
            updated_at=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Answer creation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to create answer"
        )


@router.post("/questions/{question_id}/vote", response_model=VoteResponse)
async def vote_on_question(
    question_id: str,
    request: VoteRequest,
    user: dict = Depends(get_current_user)
):
    """
    Vote on a question (upvote/downvote).
    """
    try:
        if request.vote_type not in ["upvote", "downvote"]:
            raise HTTPException(status_code=400, detail="Invalid vote type")
        
        # Check if question exists
        question_response = supabase.table("forum_questions").select("*").eq(
            "id", question_id
        ).eq("org_id", user["org_id"]).single().execute()
        
        if not question_response.data:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Check existing vote
        existing_vote = supabase.table("forum_votes").select("*").eq(
            "user_id", user["sub"]
        ).eq("target_type", "question").eq("target_id", question_id).execute()
        
        if existing_vote.data:
            # Update existing vote
            if existing_vote.data[0]["vote_type"] == request.vote_type:
                # Same vote - remove it
                supabase.table("forum_votes").delete().eq("id", existing_vote.data[0]["id"]).execute()
                vote_delta = -1 if request.vote_type == "upvote" else -1
                vote_field = "upvotes" if request.vote_type == "upvote" else "downvotes"
            else:
                # Different vote - update it
                supabase.table("forum_votes").update({
                    "vote_type": request.vote_type
                }).eq("id", existing_vote.data[0]["id"]).execute()
                
                # Adjust both counters
                old_vote = existing_vote.data[0]["vote_type"]
                if old_vote == "upvote":
                    supabase.table("forum_questions").update({
                        "upvotes": question_response.data["upvotes"] - 1,
                        "downvotes": question_response.data["downvotes"] + 1
                    }).eq("id", question_id).execute()
                else:
                    supabase.table("forum_questions").update({
                        "upvotes": question_response.data["upvotes"] + 1,
                        "downvotes": question_response.data["downvotes"] - 1
                    }).eq("id", question_id).execute()
        else:
            # Create new vote
            vote_data = {
                "user_id": user["sub"],
                "target_type": "question",
                "target_id": question_id,
                "vote_type": request.vote_type,
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("forum_votes").insert(vote_data).execute()
            
            # Update question vote count
            vote_field = "upvotes" if request.vote_type == "upvote" else "downvotes"
            current_count = question_response.data[vote_field]
            supabase.table("forum_questions").update({
                vote_field: current_count + 1
            }).eq("id", question_id).execute()
        
        # Get updated vote counts
        updated_question = supabase.table("forum_questions").select("upvotes, downvotes").eq("id", question_id).single().execute()
        
        return VoteResponse(
            target_id=question_id,
            target_type="question",
            vote_type=request.vote_type,
            upvotes=updated_question.data["upvotes"],
            downvotes=updated_question.data["downvotes"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Voting failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process vote"
        )


@router.post("/answers/{answer_id}/vote", response_model=VoteResponse)
async def vote_on_answer(
    answer_id: str,
    request: VoteRequest,
    user: dict = Depends(get_current_user)
):
    """
    Vote on an answer (upvote/downvote).
    """
    try:
        if request.vote_type not in ["upvote", "downvote"]:
            raise HTTPException(status_code=400, detail="Invalid vote type")
        
        # Check if answer exists
        answer_response = supabase.table("forum_answers").select("*").eq("id", answer_id).single().execute()
        
        if not answer_response.data:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        # Verify access through question
        question_response = supabase.table("forum_questions").select("org_id").eq(
            "id", answer_response.data["question_id"]
        ).single().execute()
        
        if not question_response.data or question_response.data["org_id"] != user["org_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Similar voting logic as questions
        existing_vote = supabase.table("forum_votes").select("*").eq(
            "user_id", user["sub"]
        ).eq("target_type", "answer").eq("target_id", answer_id).execute()
        
        if existing_vote.data:
            # Handle existing vote update/removal
            if existing_vote.data[0]["vote_type"] == request.vote_type:
                # Remove vote
                supabase.table("forum_votes").delete().eq("id", existing_vote.data[0]["id"]).execute()
                vote_field = "upvotes" if request.vote_type == "upvote" else "downvotes"
                current_count = answer_response.data[vote_field]
                supabase.table("forum_answers").update({
                    vote_field: current_count - 1
                }).eq("id", answer_id).execute()
            else:
                # Change vote
                supabase.table("forum_votes").update({
                    "vote_type": request.vote_type
                }).eq("id", existing_vote.data[0]["id"]).execute()
                
                old_vote = existing_vote.data[0]["vote_type"]
                if old_vote == "upvote":
                    supabase.table("forum_answers").update({
                        "upvotes": answer_response.data["upvotes"] - 1,
                        "downvotes": answer_response.data["downvotes"] + 1
                    }).eq("id", answer_id).execute()
                else:
                    supabase.table("forum_answers").update({
                        "upvotes": answer_response.data["upvotes"] + 1,
                        "downvotes": answer_response.data["downvotes"] - 1
                    }).eq("id", answer_id).execute()
        else:
            # Create new vote
            vote_data = {
                "user_id": user["sub"],
                "target_type": "answer",
                "target_id": answer_id,
                "vote_type": request.vote_type,
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("forum_votes").insert(vote_data).execute()
            
            vote_field = "upvotes" if request.vote_type == "upvote" else "downvotes"
            current_count = answer_response.data[vote_field]
            supabase.table("forum_answers").update({
                vote_field: current_count + 1
            }).eq("id", answer_id).execute()
        
        # Get updated counts
        updated_answer = supabase.table("forum_answers").select("upvotes, downvotes").eq("id", answer_id).single().execute()
        
        return VoteResponse(
            target_id=answer_id,
            target_type="answer",
            vote_type=request.vote_type,
            upvotes=updated_answer.data["upvotes"],
            downvotes=updated_answer.data["downvotes"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Answer voting failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to process vote"
        )


async def _get_answer_count(question_id: str) -> int:
    """Get the number of answers for a question."""
    try:
        response = supabase.table("forum_answers").select("id").eq("question_id", question_id).execute()
        return len(response.data) if response.data else 0
    except:
        return 0


async def _get_user_vote(user_id: str, target_type: str, target_id: str) -> Optional[str]:
    """Get user's vote on a target."""
    try:
        response = supabase.table("forum_votes").select("vote_type").eq(
            "user_id", user_id
        ).eq("target_type", target_type).eq("target_id", target_id).execute()
        
        if response.data:
            return response.data[0]["vote_type"]
        return None
    except:
        return None


async def _award_forum_xp(user_id: str, source: str, source_id: str):
    """Background task to award XP for forum activity."""
    try:
        xp_amounts = {
            "forum_question": 15,
            "forum_answer": 25,
            "forum_helpful_answer": 50
        }
        
        xp_earned = xp_amounts.get(source, 0)
        if xp_earned > 0:
            xp_data = {
                "user_id": user_id,
                "xp_earned": xp_earned,
                "source": source,
                "source_id": source_id,
                "description": f"Forum activity: {source.replace('_', ' ')}",
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("xp_transactions").insert(xp_data).execute()
            
            logger.info(
                "Forum XP awarded",
                user_id=user_id,
                source=source,
                xp_earned=xp_earned
            )
    except Exception as e:
        logger.error("Failed to award forum XP", user_id=user_id, error=str(e)) 