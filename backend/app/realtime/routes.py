"""
API routes for real-time features management and testing.
Provides endpoints for triggering real-time events and managing live features.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from app.auth.middleware import get_current_user
from app.realtime.websocket import manager
from app.realtime.features import get_realtime_features
from app.realtime.streaming import (
    get_streaming_manager, 
    get_typing_indicator,
    get_progress_tracker,
    get_collaboration_manager
)

logger = structlog.get_logger()

router = APIRouter()


# ===============================================
# REQUEST MODELS
# ===============================================

class SendAnnouncementRequest(BaseModel):
    message: str
    target_role: str = None
    priority: str = "normal"


class CreateStudySessionRequest(BaseModel):
    course_id: str
    topic: str
    max_participants: int = 5


class HelpRequestModel(BaseModel):
    course_id: str
    lesson_id: str
    question: str
    urgency: str = "normal"


class HelpResponseModel(BaseModel):
    request_id: str
    response: str


class ProgressUpdateRequest(BaseModel):
    lesson_id: str
    progress: float
    checkpoint: str = None


class TestStreamingRequest(BaseModel):
    conversation_id: str
    message: str
    use_streaming: bool = True


# ===============================================
# REAL-TIME MANAGEMENT ENDPOINTS
# ===============================================

@router.get("/stats")
async def get_realtime_stats(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Get real-time system statistics."""
    try:
        # Check if user has admin privileges
        if user.get("role") not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        realtime_features = get_realtime_features(manager)
        connection_stats = {
            "total_connections": sum(len(conns) for conns in manager.active_connections.values()),
            "active_users": len(manager.active_connections),
            "room_subscriptions": len(manager.room_subscriptions)
        }
        
        return {
            "connection_stats": connection_stats,
            "realtime_features_stats": realtime_features.get_statistics(),
            "websocket_manager_stats": {
                "rooms": list(manager.room_subscriptions.keys())[:10],  # First 10 rooms
                "total_rooms": len(manager.room_subscriptions)
            }
        }
        
    except Exception as e:
        logger.error("Failed to get real-time stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.post("/announcement")
async def send_announcement(
    request: SendAnnouncementRequest,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Send system-wide announcement."""
    try:
        # Check permissions
        if user.get("role") not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        realtime_features = get_realtime_features(manager)
        
        await realtime_features.send_system_announcement(
            message=request.message,
            target_role=request.target_role,
            org_id=user.get("org_id"),
            priority=request.priority
        )
        
        logger.info("System announcement sent",
                   user_id=user["sub"],
                   message=request.message[:100])
        
        return {"message": "Announcement sent successfully"}
        
    except Exception as e:
        logger.error("Failed to send announcement", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to send announcement")


# ===============================================
# AI STREAMING ENDPOINTS
# ===============================================

@router.post("/ai/test-streaming")
async def test_ai_streaming(
    request: TestStreamingRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Test AI response streaming."""
    try:
        streaming_manager = get_streaming_manager(manager)
        
        if request.use_streaming:
            # Start streaming in background
            background_tasks.add_task(
                _stream_test_response,
                streaming_manager,
                request.conversation_id,
                user["sub"],
                request.message
            )
            return {"message": "Streaming started", "conversation_id": request.conversation_id}
        else:
            # Send immediate response
            realtime_features = get_realtime_features(manager)
            await realtime_features.stream_ai_response(
                request.conversation_id,
                f"Test response to: {request.message}",
                True
            )
            return {"message": "Response sent", "conversation_id": request.conversation_id}
        
    except Exception as e:
        logger.error("AI streaming test failed", error=str(e))
        raise HTTPException(status_code=500, detail="Streaming test failed")


async def _stream_test_response(streaming_manager, conversation_id: str, 
                              user_id: str, message: str):
    """Background task for streaming test response."""
    try:
        context = "You are a helpful AI assistant for K-Orbit learning platform. "
        
        async for chunk in streaming_manager.stream_ai_response(
            conversation_id, user_id, message, context
        ):
            # Chunks are automatically sent via WebSocket
            pass
            
    except Exception as e:
        logger.error("Streaming test failed", error=str(e))


@router.post("/ai/typing/start")
async def start_typing_indicator(
    conversation_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Start typing indicator for user."""
    try:
        typing_indicator = get_typing_indicator(manager)
        
        await typing_indicator.start_user_typing(
            conversation_id=conversation_id,
            user_id=user["sub"],
            user_name=user.get("full_name", "User")
        )
        
        return {"message": "Typing indicator started"}
        
    except Exception as e:
        logger.error("Failed to start typing indicator", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start typing indicator")


@router.post("/ai/typing/stop")
async def stop_typing_indicator(
    conversation_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Stop typing indicator for user."""
    try:
        typing_indicator = get_typing_indicator(manager)
        
        await typing_indicator.stop_user_typing(
            conversation_id=conversation_id,
            user_id=user["sub"]
        )
        
        return {"message": "Typing indicator stopped"}
        
    except Exception as e:
        logger.error("Failed to stop typing indicator", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to stop typing indicator")


# ===============================================
# LEARNING PROGRESS ENDPOINTS
# ===============================================

@router.post("/progress/lesson/start")
async def start_lesson_tracking(
    lesson_id: str,
    lesson_title: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Start tracking lesson progress."""
    try:
        progress_tracker = get_progress_tracker(manager)
        
        lesson_data = {
            "id": lesson_id,
            "title": lesson_title
        }
        
        await progress_tracker.start_lesson_session(
            user_id=user["sub"],
            lesson_id=lesson_id,
            lesson_data=lesson_data
        )
        
        return {"message": "Lesson tracking started", "lesson_id": lesson_id}
        
    except Exception as e:
        logger.error("Failed to start lesson tracking", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start lesson tracking")


@router.post("/progress/lesson/update")
async def update_lesson_progress(
    request: ProgressUpdateRequest,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Update lesson progress."""
    try:
        progress_tracker = get_progress_tracker(manager)
        
        await progress_tracker.update_lesson_progress(
            user_id=user["sub"],
            lesson_id=request.lesson_id,
            progress=request.progress,
            checkpoint=request.checkpoint
        )
        
        return {"message": "Progress updated", "progress": request.progress}
        
    except Exception as e:
        logger.error("Failed to update progress", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update progress")


@router.post("/progress/lesson/complete")
async def complete_lesson(
    lesson_id: str,
    final_score: float = None,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Complete lesson and send notifications."""
    try:
        progress_tracker = get_progress_tracker(manager)
        
        await progress_tracker.complete_lesson_session(
            user_id=user["sub"],
            lesson_id=lesson_id,
            final_score=final_score
        )
        
        return {"message": "Lesson completed", "lesson_id": lesson_id}
        
    except Exception as e:
        logger.error("Failed to complete lesson", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to complete lesson")


# ===============================================
# GAMIFICATION ENDPOINTS
# ===============================================

@router.post("/gamification/xp/award")
async def award_xp(
    amount: int,
    source: str,
    target_user_id: str = None,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Award XP to user (admin only)."""
    try:
        # Check permissions
        if user.get("role") not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        realtime_features = get_realtime_features(manager)
        
        recipient_id = target_user_id or user["sub"]
        
        await realtime_features.notify_xp_earned(
            user_id=recipient_id,
            xp_amount=amount,
            source=source
        )
        
        return {"message": f"Awarded {amount} XP", "recipient": recipient_id}
        
    except Exception as e:
        logger.error("Failed to award XP", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to award XP")


@router.post("/gamification/badge/unlock")
async def unlock_badge(
    badge_name: str,
    badge_description: str,
    target_user_id: str = None,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Unlock badge for user (admin only)."""
    try:
        # Check permissions
        if user.get("role") not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        realtime_features = get_realtime_features(manager)
        
        recipient_id = target_user_id or user["sub"]
        
        badge_data = {
            "name": badge_name,
            "description": badge_description,
            "icon_url": "/badges/default.png",
            "rarity": "common"
        }
        
        await realtime_features.notify_badge_unlocked(
            user_id=recipient_id,
            badge_data=badge_data
        )
        
        return {"message": f"Badge '{badge_name}' unlocked", "recipient": recipient_id}
        
    except Exception as e:
        logger.error("Failed to unlock badge", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to unlock badge")


# ===============================================
# COLLABORATIVE LEARNING ENDPOINTS
# ===============================================

@router.post("/collaboration/study-session/create")
async def create_study_session(
    request: CreateStudySessionRequest,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Create a new study session."""
    try:
        collaboration_manager = get_collaboration_manager(manager)
        
        session_id = await collaboration_manager.create_study_session(
            creator_id=user["sub"],
            course_id=request.course_id,
            topic=request.topic,
            max_participants=request.max_participants
        )
        
        return {"message": "Study session created", "session_id": session_id}
        
    except Exception as e:
        logger.error("Failed to create study session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create study session")


@router.post("/collaboration/study-session/{session_id}/join")
async def join_study_session(
    session_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Join an existing study session."""
    try:
        collaboration_manager = get_collaboration_manager(manager)
        
        success = await collaboration_manager.join_study_session(
            session_id=session_id,
            user_id=user["sub"],
            user_name=user.get("full_name", "User")
        )
        
        if success:
            return {"message": "Joined study session", "session_id": session_id}
        else:
            raise HTTPException(status_code=400, detail="Unable to join session")
        
    except Exception as e:
        logger.error("Failed to join study session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to join study session")


@router.post("/collaboration/help/request")
async def request_peer_help(
    request: HelpRequestModel,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Request help from peers."""
    try:
        collaboration_manager = get_collaboration_manager(manager)
        
        request_id = await collaboration_manager.request_peer_help(
            user_id=user["sub"],
            course_id=request.course_id,
            lesson_id=request.lesson_id,
            question=request.question,
            urgency=request.urgency
        )
        
        return {"message": "Help request sent", "request_id": request_id}
        
    except Exception as e:
        logger.error("Failed to request help", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to request help")


@router.post("/collaboration/help/respond")
async def respond_to_help_request(
    request: HelpResponseModel,
    user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    """Respond to a peer help request."""
    try:
        collaboration_manager = get_collaboration_manager(manager)
        
        await collaboration_manager.respond_to_help_request(
            request_id=request.request_id,
            helper_id=user["sub"],
            helper_name=user.get("full_name", "User"),
            response=request.response
        )
        
        return {"message": "Help response sent"}
        
    except Exception as e:
        logger.error("Failed to respond to help request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to respond to help request")


# ===============================================
# USER PRESENCE ENDPOINTS
# ===============================================

@router.post("/presence/online")
async def set_user_online(user: dict = Depends(get_current_user)) -> Dict[str, str]:
    """Set user as online."""
    try:
        realtime_features = get_realtime_features(manager)
        
        await realtime_features.notify_user_online(
            user_id=user["sub"],
            user_info={
                "full_name": user.get("full_name"),
                "avatar_url": user.get("avatar_url"),
                "org_id": user.get("org_id"),
                "role": user.get("role")
            }
        )
        
        return {"message": "User set as online"}
        
    except Exception as e:
        logger.error("Failed to set user online", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to set user online")


@router.post("/presence/offline")
async def set_user_offline(user: dict = Depends(get_current_user)) -> Dict[str, str]:
    """Set user as offline."""
    try:
        realtime_features = get_realtime_features(manager)
        
        await realtime_features.notify_user_offline(user_id=user["sub"])
        
        return {"message": "User set as offline"}
        
    except Exception as e:
        logger.error("Failed to set user offline", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to set user offline") 