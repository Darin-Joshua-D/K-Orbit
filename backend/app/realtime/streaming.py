"""
AI Response Streaming System for K-Orbit.
Provides real-time streaming of AI responses with typing indicators and chunk delivery.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional
import structlog
import google.generativeai as genai
from datetime import datetime

from app.realtime.features import RealTimeFeatures, get_realtime_features

logger = structlog.get_logger()


class AIStreamingManager:
    """
    Manages streaming AI responses for real-time chat experience.
    """
    
    def __init__(self, realtime_features: RealTimeFeatures):
        self.realtime_features = realtime_features
        self.active_streams: Dict[str, Dict] = {}
    
    async def stream_ai_response(self, conversation_id: str, user_id: str, 
                               prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """
        Stream AI response in real-time chunks.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID requesting the response
            prompt: User prompt
            context: Additional context for AI
            
        Yields:
            Response chunks as they're generated
        """
        stream_id = f"{conversation_id}_{int(time.time())}"
        
        try:
            # Start typing indicator
            await self.realtime_features.start_ai_typing_indicator(conversation_id, user_id)
            
            # Track active stream
            self.active_streams[stream_id] = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "started_at": time.time(),
                "chunks_sent": 0
            }
            
            # Small delay to show typing indicator
            await asyncio.sleep(0.5)
            
            # Stop typing indicator before streaming
            await self.realtime_features.stop_ai_typing_indicator(conversation_id)
            
            # Generate streaming response
            full_response = ""
            chunk_buffer = ""
            
            async for chunk in self._generate_streaming_response(prompt, context):
                chunk_buffer += chunk
                full_response += chunk
                
                # Send chunks in word boundaries for better readability
                if len(chunk_buffer) >= 20 or chunk.endswith((' ', '.', '!', '?', '\n')):
                    await self.realtime_features.stream_ai_response(
                        conversation_id, chunk_buffer, False
                    )
                    
                    self.active_streams[stream_id]["chunks_sent"] += 1
                    chunk_buffer = ""
                    
                    # Small delay between chunks for natural feel
                    await asyncio.sleep(0.1)
                    
                    yield chunk
            
            # Send any remaining buffer
            if chunk_buffer:
                await self.realtime_features.stream_ai_response(
                    conversation_id, chunk_buffer, False
                )
                yield chunk_buffer
            
            # Send completion signal
            await self.realtime_features.stream_ai_response(
                conversation_id, "", True
            )
            
            logger.info("AI response streaming completed",
                       conversation_id=conversation_id,
                       chunks_sent=self.active_streams[stream_id]["chunks_sent"],
                       response_length=len(full_response))
            
        except Exception as e:
            logger.error("AI streaming failed", 
                        conversation_id=conversation_id,
                        error=str(e))
            
            # Send error to client
            await self.realtime_features.stream_ai_response(
                conversation_id, 
                "I apologize, but I encountered an error. Please try again.", 
                True
            )
            
        finally:
            # Cleanup
            self.active_streams.pop(stream_id, None)
            await self.realtime_features.stop_ai_typing_indicator(conversation_id)
    
    async def _generate_streaming_response(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """
        Generate AI response using streaming API.
        
        Args:
            prompt: User prompt
            context: Additional context
            
        Yields:
            Response chunks
        """
        try:
            # Prepare the full prompt with context
            full_prompt = f"{context}\n\nUser: {prompt}\nAssistant:"
            
            # Configure Gemini for streaming
            model = genai.GenerativeModel('gemini-pro')
            
            # Generate streaming response
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                    stream=True  # Enable streaming
                )
            )
            
            # Stream the response
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error("Gemini streaming failed", error=str(e))
            
            # Fallback to non-streaming response
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=1000,
                    )
                )
                
                if response.text:
                    # Simulate streaming by yielding words
                    words = response.text.split(' ')
                    for i, word in enumerate(words):
                        if i == len(words) - 1:
                            yield word
                        else:
                            yield word + ' '
                        await asyncio.sleep(0.05)  # Simulate typing speed
                        
            except Exception as fallback_error:
                logger.error("Fallback response generation failed", error=str(fallback_error))
                yield "I apologize, but I'm having trouble generating a response right now. Please try again in a moment."


class LiveTypingIndicator:
    """
    Manages typing indicators for real-time chat.
    """
    
    def __init__(self, realtime_features: RealTimeFeatures):
        self.realtime_features = realtime_features
        self.typing_sessions: Dict[str, Dict] = {}
    
    async def start_user_typing(self, conversation_id: str, user_id: str, user_name: str):
        """Start user typing indicator."""
        session_id = f"{conversation_id}_{user_id}"
        
        # Store typing session
        self.typing_sessions[session_id] = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_name": user_name,
            "started_at": time.time()
        }
        
        # Notify other participants
        message = {
            "type": "user_typing_start",
            "payload": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "user_name": user_name,
                "message": f"{user_name} is typing..."
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.realtime_features.connection_manager.broadcast_to_room(
            message, f"conversation:{conversation_id}"
        )
        
        # Auto-stop typing after 10 seconds
        asyncio.create_task(self._auto_stop_typing(session_id))
    
    async def stop_user_typing(self, conversation_id: str, user_id: str):
        """Stop user typing indicator."""
        session_id = f"{conversation_id}_{user_id}"
        
        if session_id in self.typing_sessions:
            session = self.typing_sessions.pop(session_id)
            
            message = {
                "type": "user_typing_stop",
                "payload": {
                    "conversation_id": conversation_id,
                    "user_id": user_id
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.realtime_features.connection_manager.broadcast_to_room(
                message, f"conversation:{conversation_id}"
            )
    
    async def _auto_stop_typing(self, session_id: str):
        """Automatically stop typing indicator after timeout."""
        await asyncio.sleep(10)  # 10 seconds timeout
        
        if session_id in self.typing_sessions:
            session = self.typing_sessions[session_id]
            await self.stop_user_typing(
                session["conversation_id"], 
                session["user_id"]
            )


class LiveProgressTracker:
    """
    Tracks and broadcasts live learning progress updates.
    """
    
    def __init__(self, realtime_features: RealTimeFeatures):
        self.realtime_features = realtime_features
        self.progress_sessions: Dict[str, Dict] = {}
    
    async def start_lesson_session(self, user_id: str, lesson_id: str, lesson_data: Dict[str, Any]):
        """Start tracking lesson progress."""
        session_id = f"{user_id}_{lesson_id}"
        
        self.progress_sessions[session_id] = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "lesson_data": lesson_data,
            "started_at": time.time(),
            "progress": 0.0,
            "checkpoints": []
        }
        
        # Notify lesson start
        await self.realtime_features.notify_lesson_started(
            user_id, lesson_id, lesson_data["title"]
        )
    
    async def update_lesson_progress(self, user_id: str, lesson_id: str, 
                                   progress: float, checkpoint: Optional[str] = None):
        """Update lesson progress in real-time."""
        session_id = f"{user_id}_{lesson_id}"
        
        if session_id in self.progress_sessions:
            session = self.progress_sessions[session_id]
            session["progress"] = progress
            
            if checkpoint:
                session["checkpoints"].append({
                    "checkpoint": checkpoint,
                    "timestamp": time.time(),
                    "progress": progress
                })
            
            # Send progress update
            message = {
                "type": "lesson_progress_update",
                "payload": {
                    "lesson_id": lesson_id,
                    "progress": progress,
                    "checkpoint": checkpoint,
                    "session_duration": time.time() - session["started_at"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.realtime_features.connection_manager.send_personal_message(
                message, user_id
            )
    
    async def complete_lesson_session(self, user_id: str, lesson_id: str, 
                                    final_score: Optional[float] = None):
        """Complete lesson session and send notifications."""
        session_id = f"{user_id}_{lesson_id}"
        
        if session_id in self.progress_sessions:
            session = self.progress_sessions.pop(session_id)
            
            # Calculate session metrics
            duration = time.time() - session["started_at"]
            checkpoints_completed = len(session["checkpoints"])
            
            # Notify lesson completion
            await self.realtime_features.notify_lesson_completed(
                user_id,
                lesson_id,
                session["lesson_data"]["title"],
                xp_earned=50,  # Base XP, should be calculated based on lesson
                new_progress=100.0
            )
            
            # Send detailed completion data
            message = {
                "type": "lesson_session_complete",
                "payload": {
                    "lesson_id": lesson_id,
                    "duration": duration,
                    "checkpoints_completed": checkpoints_completed,
                    "final_score": final_score,
                    "lesson_data": session["lesson_data"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.realtime_features.connection_manager.send_personal_message(
                message, user_id
            )


class LiveCollaborationManager:
    """
    Manages live collaborative features like study groups and peer help.
    """
    
    def __init__(self, realtime_features: RealTimeFeatures):
        self.realtime_features = realtime_features
        self.active_sessions: Dict[str, Dict] = {}
        self.help_requests: Dict[str, Dict] = {}
    
    async def create_study_session(self, creator_id: str, course_id: str, 
                                 topic: str, max_participants: int = 5) -> str:
        """Create a new study session."""
        session_id = f"study_{int(time.time())}"
        
        session_data = {
            "id": session_id,
            "creator_id": creator_id,
            "course_id": course_id,
            "topic": topic,
            "max_participants": max_participants,
            "participants": [creator_id],
            "created_at": time.time(),
            "status": "open"
        }
        
        self.active_sessions[session_id] = session_data
        
        # Broadcast session creation to course participants
        message = {
            "type": "study_session_created",
            "payload": session_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.realtime_features.connection_manager.broadcast_to_room(
            message, f"course:{course_id}"
        )
        
        return session_id
    
    async def join_study_session(self, session_id: str, user_id: str, user_name: str):
        """Join an existing study session."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            if len(session["participants"]) < session["max_participants"]:
                session["participants"].append(user_id)
                
                # Notify all participants
                message = {
                    "type": "study_session_participant_joined",
                    "payload": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "user_name": user_name,
                        "total_participants": len(session["participants"])
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await self.realtime_features.connection_manager.broadcast_to_room(
                    message, f"study_session:{session_id}"
                )
                
                return True
        
        return False
    
    async def request_peer_help(self, user_id: str, course_id: str, lesson_id: str, 
                              question: str, urgency: str = "normal") -> str:
        """Request help from peers."""
        request_id = f"help_{int(time.time())}"
        
        help_data = {
            "id": request_id,
            "user_id": user_id,
            "course_id": course_id,
            "lesson_id": lesson_id,
            "question": question,
            "urgency": urgency,
            "created_at": time.time(),
            "responses": []
        }
        
        self.help_requests[request_id] = help_data
        
        # Broadcast help request to course participants
        await self.realtime_features.request_peer_help(
            user_id, course_id, lesson_id, question, "org_id"  # Get from user context
        )
        
        return request_id
    
    async def respond_to_help_request(self, request_id: str, helper_id: str, 
                                    helper_name: str, response: str):
        """Respond to a peer help request."""
        if request_id in self.help_requests:
            help_request = self.help_requests[request_id]
            
            response_data = {
                "helper_id": helper_id,
                "helper_name": helper_name,
                "response": response,
                "timestamp": time.time()
            }
            
            help_request["responses"].append(response_data)
            
            # Notify the person who requested help
            message = {
                "type": "peer_help_response",
                "payload": {
                    "request_id": request_id,
                    "helper_name": helper_name,
                    "response": response,
                    "total_responses": len(help_request["responses"])
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.realtime_features.connection_manager.send_personal_message(
                message, help_request["user_id"]
            )


# Global managers
_streaming_manager: Optional[AIStreamingManager] = None
_typing_indicator: Optional[LiveTypingIndicator] = None
_progress_tracker: Optional[LiveProgressTracker] = None
_collaboration_manager: Optional[LiveCollaborationManager] = None


def get_streaming_manager(connection_manager) -> AIStreamingManager:
    """Get the AI streaming manager."""
    global _streaming_manager
    if _streaming_manager is None:
        realtime_features = get_realtime_features(connection_manager)
        _streaming_manager = AIStreamingManager(realtime_features)
    return _streaming_manager


def get_typing_indicator(connection_manager) -> LiveTypingIndicator:
    """Get the typing indicator manager."""
    global _typing_indicator
    if _typing_indicator is None:
        realtime_features = get_realtime_features(connection_manager)
        _typing_indicator = LiveTypingIndicator(realtime_features)
    return _typing_indicator


def get_progress_tracker(connection_manager) -> LiveProgressTracker:
    """Get the progress tracker."""
    global _progress_tracker
    if _progress_tracker is None:
        realtime_features = get_realtime_features(connection_manager)
        _progress_tracker = LiveProgressTracker(realtime_features)
    return _progress_tracker


def get_collaboration_manager(connection_manager) -> LiveCollaborationManager:
    """Get the collaboration manager."""
    global _collaboration_manager
    if _collaboration_manager is None:
        realtime_features = get_realtime_features(connection_manager)
        _collaboration_manager = LiveCollaborationManager(realtime_features)
    return _collaboration_manager 