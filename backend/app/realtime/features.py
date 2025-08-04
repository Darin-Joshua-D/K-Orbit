"""
Enhanced real-time features for K-Orbit.
Implements AI chat streaming, live progress tracking, collaborative features, and real-time analytics.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import structlog
from datetime import datetime

from app.database import get_db_manager, get_db_metrics

logger = structlog.get_logger()


class EventType(Enum):
    """Real-time event types."""
    
    # AI Chat Events
    AI_TYPING_START = "ai_typing_start"
    AI_TYPING_STOP = "ai_typing_stop"
    AI_RESPONSE_STREAM = "ai_response_stream"
    AI_RESPONSE_COMPLETE = "ai_response_complete"
    
    # Learning Progress Events
    LESSON_STARTED = "lesson_started"
    LESSON_COMPLETED = "lesson_completed"
    COURSE_PROGRESS_UPDATE = "course_progress_update"
    XP_EARNED = "xp_earned"
    BADGE_UNLOCKED = "badge_unlocked"
    LEVEL_UP = "level_up"
    
    # Collaborative Learning Events
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    STUDY_GROUP_ACTIVITY = "study_group_activity"
    PEER_HELP_REQUEST = "peer_help_request"
    COLLABORATIVE_SESSION = "collaborative_session"
    
    # Forum & Social Events
    FORUM_NEW_QUESTION = "forum_new_question"
    FORUM_NEW_ANSWER = "forum_new_answer"
    FORUM_ANSWER_ACCEPTED = "forum_answer_accepted"
    FORUM_UPVOTE = "forum_upvote"
    
    # Administrative Events
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    MAINTENANCE_ALERT = "maintenance_alert"
    PERFORMANCE_ALERT = "performance_alert"
    USER_ACTIVITY_ALERT = "user_activity_alert"
    
    # Gamification Events
    LEADERBOARD_UPDATE = "leaderboard_update"
    ACHIEVEMENT_CELEBRATION = "achievement_celebration"
    STREAK_UPDATE = "streak_update"
    COMPETITION_UPDATE = "competition_update"
    
    # Document Processing Events
    DOCUMENT_UPLOAD_PROGRESS = "document_upload_progress"
    DOCUMENT_PROCESSED = "document_processed"
    KNOWLEDGE_BASE_UPDATE = "knowledge_base_update"


@dataclass
class RealTimeEvent:
    """Real-time event data structure."""
    event_type: EventType
    user_id: Optional[str]
    target_users: Optional[List[str]]
    room: Optional[str]
    payload: Dict[str, Any]
    timestamp: str = None
    priority: str = "normal"  # low, normal, high, urgent
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class RealTimeFeatures:
    """
    Enhanced real-time features manager for K-Orbit.
    """
    
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self.active_ai_sessions: Dict[str, Dict] = {}  # conversation_id -> session_info
        self.active_users: Dict[str, Dict] = {}  # user_id -> user_info
        self.study_groups: Dict[str, Set[str]] = {}  # group_id -> user_ids
        self.typing_indicators: Dict[str, str] = {}  # room -> user_id
        
        # Performance tracking
        self.event_stats = {
            "events_sent": 0,
            "events_failed": 0,
            "active_streams": 0
        }
    
    # ===============================================
    # AI CHAT REAL-TIME FEATURES
    # ===============================================
    
    async def start_ai_typing_indicator(self, conversation_id: str, user_id: str):
        """Start AI typing indicator for a conversation."""
        event = RealTimeEvent(
            event_type=EventType.AI_TYPING_START,
            user_id=user_id,
            target_users=[user_id],
            room=f"conversation:{conversation_id}",
            payload={
                "conversation_id": conversation_id,
                "message": "AI is thinking..."
            }
        )
        
        await self._send_event(event)
        
        # Track active AI session
        self.active_ai_sessions[conversation_id] = {
            "user_id": user_id,
            "started_at": time.time(),
            "typing": True
        }
    
    async def stop_ai_typing_indicator(self, conversation_id: str):
        """Stop AI typing indicator."""
        if conversation_id in self.active_ai_sessions:
            session = self.active_ai_sessions[conversation_id]
            
            event = RealTimeEvent(
                event_type=EventType.AI_TYPING_STOP,
                user_id=session["user_id"],
                target_users=[session["user_id"]],
                room=f"conversation:{conversation_id}",
                payload={
                    "conversation_id": conversation_id
                }
            )
            
            await self._send_event(event)
            
            # Update session
            session["typing"] = False
    
    async def stream_ai_response(self, conversation_id: str, chunk: str, is_complete: bool = False):
        """Stream AI response in real-time chunks."""
        if conversation_id not in self.active_ai_sessions:
            return
        
        session = self.active_ai_sessions[conversation_id]
        
        event_type = EventType.AI_RESPONSE_COMPLETE if is_complete else EventType.AI_RESPONSE_STREAM
        
        event = RealTimeEvent(
            event_type=event_type,
            user_id=session["user_id"],
            target_users=[session["user_id"]],
            room=f"conversation:{conversation_id}",
            payload={
                "conversation_id": conversation_id,
                "chunk": chunk,
                "is_complete": is_complete,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        await self._send_event(event)
        
        if is_complete:
            # Clean up session
            self.active_ai_sessions.pop(conversation_id, None)
            self.event_stats["active_streams"] -= 1
    
    # ===============================================
    # LEARNING PROGRESS REAL-TIME FEATURES
    # ===============================================
    
    async def notify_lesson_started(self, user_id: str, lesson_id: str, lesson_title: str):
        """Notify when a user starts a lesson."""
        event = RealTimeEvent(
            event_type=EventType.LESSON_STARTED,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "lesson_id": lesson_id,
                "lesson_title": lesson_title,
                "message": f"Started learning: {lesson_title}"
            }
        )
        
        await self._send_event(event)
        
        # Notify study group members if user is in one
        await self._notify_study_group_activity(user_id, f"started lesson: {lesson_title}")
    
    async def notify_lesson_completed(self, user_id: str, lesson_id: str, lesson_title: str, 
                                    xp_earned: int, new_progress: float):
        """Notify when a user completes a lesson."""
        event = RealTimeEvent(
            event_type=EventType.LESSON_COMPLETED,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "lesson_id": lesson_id,
                "lesson_title": lesson_title,
                "xp_earned": xp_earned,
                "new_progress": new_progress,
                "message": f"Completed: {lesson_title}",
                "celebration": True
            },
            priority="high"
        )
        
        await self._send_event(event)
        
        # Send XP earned notification
        if xp_earned > 0:
            await self.notify_xp_earned(user_id, xp_earned, f"Lesson completion: {lesson_title}")
    
    async def notify_xp_earned(self, user_id: str, xp_amount: int, source: str):
        """Notify when user earns XP."""
        event = RealTimeEvent(
            event_type=EventType.XP_EARNED,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "xp_amount": xp_amount,
                "source": source,
                "animation": "xp_gained",
                "message": f"+{xp_amount} XP"
            }
        )
        
        await self._send_event(event)
    
    async def notify_badge_unlocked(self, user_id: str, badge_data: Dict[str, Any]):
        """Notify when user unlocks a badge."""
        event = RealTimeEvent(
            event_type=EventType.BADGE_UNLOCKED,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "badge": badge_data,
                "animation": "badge_celebration",
                "message": f"Badge unlocked: {badge_data['name']}",
                "celebration": True
            },
            priority="high"
        )
        
        await self._send_event(event)
        
        # Notify study group about achievement
        await self._notify_study_group_activity(
            user_id, 
            f"unlocked badge: {badge_data['name']}"
        )
    
    async def notify_level_up(self, user_id: str, new_level: int, total_xp: int):
        """Notify when user levels up."""
        event = RealTimeEvent(
            event_type=EventType.LEVEL_UP,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "new_level": new_level,
                "total_xp": total_xp,
                "animation": "level_up_celebration",
                "message": f"Level up! You're now level {new_level}",
                "celebration": True
            },
            priority="urgent"
        )
        
        await self._send_event(event)
    
    # ===============================================
    # COLLABORATIVE LEARNING FEATURES
    # ===============================================
    
    async def notify_user_online(self, user_id: str, user_info: Dict[str, Any]):
        """Notify when user comes online."""
        self.active_users[user_id] = {
            **user_info,
            "online_since": time.time(),
            "current_activity": "online"
        }
        
        # Notify organization members
        event = RealTimeEvent(
            event_type=EventType.USER_ONLINE,
            user_id=user_id,
            room=f"org:{user_info.get('org_id')}",
            payload={
                "user_id": user_id,
                "user_name": user_info.get("full_name"),
                "avatar_url": user_info.get("avatar_url"),
                "status": "online"
            }
        )
        
        await self._send_event(event)
    
    async def notify_user_offline(self, user_id: str):
        """Notify when user goes offline."""
        if user_id in self.active_users:
            user_info = self.active_users.pop(user_id)
            
            event = RealTimeEvent(
                event_type=EventType.USER_OFFLINE,
                user_id=user_id,
                room=f"org:{user_info.get('org_id')}",
                payload={
                    "user_id": user_id,
                    "user_name": user_info.get("full_name"),
                    "status": "offline",
                    "session_duration": time.time() - user_info.get("online_since", time.time())
                }
            )
            
            await self._send_event(event)
    
    async def create_study_group_session(self, group_id: str, creator_id: str, 
                                       topic: str, participants: List[str]):
        """Create a collaborative study session."""
        self.study_groups[group_id] = set(participants)
        
        event = RealTimeEvent(
            event_type=EventType.COLLABORATIVE_SESSION,
            user_id=creator_id,
            target_users=participants,
            room=f"study_group:{group_id}",
            payload={
                "group_id": group_id,
                "creator_id": creator_id,
                "topic": topic,
                "participants": participants,
                "action": "session_started",
                "message": f"Study session started: {topic}"
            }
        )
        
        await self._send_event(event)
    
    async def request_peer_help(self, user_id: str, course_id: str, lesson_id: str, 
                              question: str, org_id: str):
        """Request help from peers in the same course."""
        event = RealTimeEvent(
            event_type=EventType.PEER_HELP_REQUEST,
            user_id=user_id,
            room=f"course:{course_id}",
            payload={
                "user_id": user_id,
                "course_id": course_id,
                "lesson_id": lesson_id,
                "question": question,
                "help_type": "peer_assistance",
                "urgency": "normal"
            }
        )
        
        await self._send_event(event)
    
    async def _notify_study_group_activity(self, user_id: str, activity: str):
        """Notify study group members about user activity."""
        for group_id, members in self.study_groups.items():
            if user_id in members:
                other_members = [m for m in members if m != user_id]
                
                if other_members:
                    event = RealTimeEvent(
                        event_type=EventType.STUDY_GROUP_ACTIVITY,
                        user_id=user_id,
                        target_users=other_members,
                        room=f"study_group:{group_id}",
                        payload={
                            "user_id": user_id,
                            "activity": activity,
                            "group_id": group_id
                        }
                    )
                    
                    await self._send_event(event)
    
    # ===============================================
    # FORUM REAL-TIME FEATURES
    # ===============================================
    
    async def notify_new_forum_question(self, question_data: Dict[str, Any]):
        """Notify about new forum question."""
        event = RealTimeEvent(
            event_type=EventType.FORUM_NEW_QUESTION,
            user_id=question_data["user_id"],
            room=f"org:{question_data['org_id']}",
            payload={
                "question": question_data,
                "notification_text": f"New question: {question_data['title']}"
            }
        )
        
        await self._send_event(event)
    
    async def notify_new_forum_answer(self, answer_data: Dict[str, Any], question_data: Dict[str, Any]):
        """Notify about new forum answer."""
        # Notify question author
        event = RealTimeEvent(
            event_type=EventType.FORUM_NEW_ANSWER,
            user_id=answer_data["user_id"],
            target_users=[question_data["user_id"]],
            room=f"question:{question_data['id']}",
            payload={
                "answer": answer_data,
                "question": question_data,
                "notification_text": f"New answer to your question: {question_data['title']}"
            },
            priority="high"
        )
        
        await self._send_event(event)
    
    # ===============================================
    # ADMINISTRATIVE REAL-TIME FEATURES
    # ===============================================
    
    async def send_system_announcement(self, message: str, target_role: Optional[str] = None, 
                                     org_id: Optional[str] = None, priority: str = "normal"):
        """Send system-wide announcement."""
        room = f"org:{org_id}" if org_id else "global"
        
        event = RealTimeEvent(
            event_type=EventType.SYSTEM_ANNOUNCEMENT,
            user_id=None,
            room=room,
            payload={
                "message": message,
                "target_role": target_role,
                "announcement_type": "system",
                "dismissible": True
            },
            priority=priority
        )
        
        await self._send_event(event)
    
    async def send_performance_alert(self, alert_data: Dict[str, Any], admin_users: List[str]):
        """Send performance alert to administrators."""
        event = RealTimeEvent(
            event_type=EventType.PERFORMANCE_ALERT,
            user_id=None,
            target_users=admin_users,
            room="admin_alerts",
            payload={
                "alert": alert_data,
                "severity": alert_data.get("severity", "medium"),
                "action_required": True
            },
            priority="high"
        )
        
        await self._send_event(event)
    
    # ===============================================
    # DOCUMENT PROCESSING REAL-TIME FEATURES
    # ===============================================
    
    async def notify_document_upload_progress(self, user_id: str, file_id: str, 
                                            progress: float, status: str):
        """Notify about document upload/processing progress."""
        event = RealTimeEvent(
            event_type=EventType.DOCUMENT_UPLOAD_PROGRESS,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "file_id": file_id,
                "progress": progress,
                "status": status,
                "message": f"Processing... {progress:.1f}%"
            }
        )
        
        await self._send_event(event)
    
    async def notify_document_processed(self, user_id: str, file_data: Dict[str, Any]):
        """Notify when document processing is complete."""
        event = RealTimeEvent(
            event_type=EventType.DOCUMENT_PROCESSED,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "file": file_data,
                "message": f"Document '{file_data['name']}' processed successfully",
                "success": True
            }
        )
        
        await self._send_event(event)
    
    # ===============================================
    # LEADERBOARD & GAMIFICATION FEATURES
    # ===============================================
    
    async def update_leaderboard(self, org_id: str, leaderboard_data: List[Dict[str, Any]]):
        """Update real-time leaderboard."""
        event = RealTimeEvent(
            event_type=EventType.LEADERBOARD_UPDATE,
            user_id=None,
            room=f"leaderboard:{org_id}",
            payload={
                "leaderboard": leaderboard_data[:10],  # Top 10
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        await self._send_event(event)
    
    async def celebrate_achievement(self, user_id: str, achievement_data: Dict[str, Any]):
        """Celebrate user achievement with animation."""
        event = RealTimeEvent(
            event_type=EventType.ACHIEVEMENT_CELEBRATION,
            user_id=user_id,
            target_users=[user_id],
            room=f"user:{user_id}",
            payload={
                "achievement": achievement_data,
                "animation": "confetti",
                "duration": 3000,  # 3 seconds
                "sound": "achievement_unlock"
            },
            priority="high"
        )
        
        await self._send_event(event)
    
    # ===============================================
    # UTILITY METHODS
    # ===============================================
    
    async def _send_event(self, event: RealTimeEvent):
        """Send real-time event through WebSocket."""
        try:
            message = {
                "type": event.event_type.value,
                "payload": event.payload,
                "timestamp": event.timestamp,
                "priority": event.priority
            }
            
            if event.target_users:
                # Send to specific users
                for user_id in event.target_users:
                    await self.connection_manager.send_personal_message(message, user_id)
            elif event.room:
                # Send to room
                await self.connection_manager.broadcast_to_room(message, event.room)
            else:
                # Global broadcast
                await self.connection_manager.broadcast(message)
            
            self.event_stats["events_sent"] += 1
            
        except Exception as e:
            logger.error("Failed to send real-time event", 
                        event_type=event.event_type.value,
                        error=str(e))
            self.event_stats["events_failed"] += 1
    
    def get_active_users_count(self, org_id: str) -> int:
        """Get count of active users in organization."""
        return len([u for u in self.active_users.values() if u.get("org_id") == org_id])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get real-time features statistics."""
        return {
            "active_ai_sessions": len(self.active_ai_sessions),
            "active_users": len(self.active_users),
            "study_groups": len(self.study_groups),
            "event_stats": self.event_stats.copy()
        }


# Global instance
_realtime_features: Optional[RealTimeFeatures] = None


def get_realtime_features(connection_manager) -> RealTimeFeatures:
    """Get the global real-time features instance."""
    global _realtime_features
    
    if _realtime_features is None:
        _realtime_features = RealTimeFeatures(connection_manager)
    
    return _realtime_features 