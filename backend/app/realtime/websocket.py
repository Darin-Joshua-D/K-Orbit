"""
WebSocket implementation for real-time notifications and updates.
Handles real-time XP updates, forum notifications, and system alerts.
"""

import json
import os
from typing import Dict, Set, List
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.websockets import WebSocketState
import jwt
from supabase import create_client, Client
from datetime import datetime

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        # Active connections: user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Connection metadata: WebSocket -> user info
        self.connection_metadata: Dict[WebSocket, dict] = {}
        # Room subscriptions: room_name -> Set[user_id]
        self.room_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, user_info: dict):
        """Accept new WebSocket connection."""
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = user_info
        
        logger.info(
            "WebSocket connection established",
            user_id=user_id,
            email=user_info.get("email"),
            total_connections=sum(len(conns) for conns in self.active_connections.values())
        )
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "message": "Connected to K-Orbit real-time updates",
            "user_id": user_id
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        user_info = self.connection_metadata.get(websocket)
        if not user_info:
            # Try to find and remove the websocket from active connections even without metadata
            for user_id, connections in list(self.active_connections.items()):
                if websocket in connections:
                    connections.discard(websocket)
                    if not connections:
                        del self.active_connections[user_id]
                    break
            return
        
        user_id = user_info["sub"]
        
        # Remove from active connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from connection metadata
        self.connection_metadata.pop(websocket, None)
        
        # Remove from room subscriptions
        for room_users in self.room_subscriptions.values():
            room_users.discard(user_id)
        
        logger.info(
            "WebSocket connection closed",
            user_id=user_id,
            email=user_info.get("email"),
            remaining_connections=sum(len(conns) for conns in self.active_connections.values())
        )
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket connection."""
        try:
            # Check if WebSocket is still connected and in active connections
            if (websocket.client_state == WebSocketState.CONNECTED and 
                websocket in self.connection_metadata):
                await websocket.send_text(json.dumps(message))
            else:
                # Clean up disconnected WebSocket
                self.disconnect(websocket)
        except Exception as e:
            logger.error("Failed to send WebSocket message", error=str(e))
            # Clean up the connection if send fails
            self.disconnect(websocket)
    
    async def send_message_to_user(self, message: dict, user_id: str):
        """Send message to all connections of a specific user."""
        if user_id in self.active_connections:
            disconnected_sockets = []
            for websocket in self.active_connections[user_id].copy():
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(json.dumps(message))
                    else:
                        disconnected_sockets.append(websocket)
                except Exception as e:
                    logger.error("Failed to send message to user", user_id=user_id, error=str(e))
                    disconnected_sockets.append(websocket)
            
            # Clean up disconnected sockets
            for websocket in disconnected_sockets:
                self.disconnect(websocket)
    
    async def send_message_to_room(self, message: dict, room: str):
        """Send message to all users in a room."""
        if room in self.room_subscriptions:
            for user_id in self.room_subscriptions[room].copy():
                await self.send_message_to_user(message, user_id)
    
    async def subscribe_to_room(self, user_id: str, room: str):
        """Subscribe user to a room."""
        if room not in self.room_subscriptions:
            self.room_subscriptions[room] = set()
        self.room_subscriptions[room].add(user_id)
        
        logger.info("User subscribed to room", user_id=user_id, room=room)
    
    async def unsubscribe_from_room(self, user_id: str, room: str):
        """Unsubscribe user from a room."""
        if room in self.room_subscriptions:
            self.room_subscriptions[room].discard(user_id)
            if not self.room_subscriptions[room]:
                del self.room_subscriptions[room]
        
        logger.info("User unsubscribed from room", user_id=user_id, room=room)
    
    def get_active_users(self) -> List[dict]:
        """Get list of active users."""
        active_users = []
        for user_id, connections in self.active_connections.items():
            if connections:  # Has active connections
                # Get user info from any connection
                websocket = next(iter(connections))
                user_info = self.connection_metadata.get(websocket, {})
                active_users.append({
                    "user_id": user_id,
                    "email": user_info.get("email"),
                    "full_name": user_info.get("full_name"),
                    "connections": len(connections)
                })
        return active_users


# Global connection manager
manager = ConnectionManager()


async def verify_websocket_token(token: str) -> dict:
    """Verify WebSocket authentication token."""
    try:
        # Verify token with Supabase (simplified to avoid DB pool issues)
        response = supabase.auth.get_user(token)
        if response.user:
            user_data = {
                "sub": response.user.id,
                "email": response.user.email,
                "role": "learner",  # Simplified - avoid DB query for now
                "org_id": None,
                "full_name": response.user.email,
            }
            
            return user_data
    except Exception as e:
        logger.error("WebSocket token verification failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")
    
    raise HTTPException(status_code=401, detail="Invalid token")


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time notifications.
    URL: /ws/notifications?token=<jwt_token>
    """
    try:
        # Verify authentication
        user_info = await verify_websocket_token(token)
        user_id = user_info["sub"]
        
        # Connect to manager
        await manager.connect(websocket, user_id, user_info)
        
        # Auto-subscribe to user's personal room
        await manager.subscribe_to_room(user_id, f"user_{user_id}")
        
        # Auto-subscribe to organization room
        if user_info.get("org_id"):
            await manager.subscribe_to_room(user_id, f"org_{user_info['org_id']}")
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(websocket, user_info, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Only send error if connection is still active
                if websocket.client_state == WebSocketState.CONNECTED:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }, websocket)
            except Exception as e:
                logger.error("Error handling WebSocket message", error=str(e))
                # Only send error if connection is still active
                if websocket.client_state == WebSocketState.CONNECTED:
                    await manager.send_personal_message({
                        "type": "error", 
                        "message": "Message processing failed"
                    }, websocket)
                
    except HTTPException as e:
        await websocket.close(code=4001, reason=e.detail)
    except Exception as e:
        logger.error("WebSocket connection error", error=str(e))
        await websocket.close(code=4000, reason="Connection error")
    finally:
        manager.disconnect(websocket)


async def handle_websocket_message(websocket: WebSocket, user_info: dict, message: dict):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    user_id = user_info["sub"]
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": message.get("timestamp")
        }, websocket)
    
    elif message_type == "subscribe":
        # Subscribe to a room
        room = message.get("room")
        if room:
            # Validate room access (implement your authorization logic)
            if await can_access_room(user_info, room):
                await manager.subscribe_to_room(user_id, room)
                await manager.send_personal_message({
                    "type": "subscribed",
                    "room": room
                }, websocket)
            else:
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Access denied to room: {room}"
                }, websocket)
    
    elif message_type == "unsubscribe":
        # Unsubscribe from a room
        room = message.get("room")
        if room:
            await manager.unsubscribe_from_room(user_id, room)
            await manager.send_personal_message({
                "type": "unsubscribed",
                "room": room
            }, websocket)
    
    elif message_type == "get_active_users":
        # Get list of active users (admin/manager only)
        if user_info.get("role") in ["admin", "manager"]:
            active_users = manager.get_active_users()
            await manager.send_personal_message({
                "type": "active_users",
                "users": active_users
            }, websocket)
    
    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }, websocket)


async def can_access_room(user_info: dict, room: str) -> bool:
    """Check if user can access a specific room."""
    # Implement your room access logic here
    # Examples:
    # - user_<user_id>: Only the user themselves
    # - org_<org_id>: Users in the same organization
    # - course_<course_id>: Users enrolled in the course
    # - forum_<topic_id>: Users with access to the forum topic
    
    if room.startswith(f"user_{user_info['sub']}"):
        return True
    
    if room.startswith(f"org_{user_info.get('org_id')}"):
        return True
    
    if room.startswith("course_"):
        # Check if user is enrolled in the course
        course_id = room.split("_")[1]
        try:
            enrollment = supabase.table("course_enrollments").select("id").eq(
                "user_id", user_info["sub"]
            ).eq("course_id", course_id).single().execute()
            return enrollment.data is not None
        except:
            return False
    
    if room.startswith("forum_"):
        # For forum rooms, allow access if user is in the organization
        return user_info.get("org_id") is not None
    
    # Default to deny access
    return False


# Utility functions for sending notifications

async def send_xp_notification(user_id: str, xp_earned: int, source: str, level_up: bool = False):
    """Send XP earned notification to user."""
    message = {
        "type": "xp_earned",
        "xp_earned": xp_earned,
        "source": source,
        "level_up": level_up,
        "timestamp": json.dumps(datetime.utcnow().isoformat())
    }
    
    await manager.send_message_to_user(message, user_id)


async def send_badge_notification(user_id: str, badge_name: str, badge_description: str):
    """Send badge earned notification to user."""
    message = {
        "type": "badge_earned",
        "badge_name": badge_name,
        "badge_description": badge_description,
        "timestamp": json.dumps(datetime.utcnow().isoformat())
    }
    
    await manager.send_message_to_user(message, user_id)


async def send_forum_notification(user_id: str, notification_type: str, question_title: str, question_id: str):
    """Send forum notification to user."""
    message = {
        "type": "forum_notification",
        "notification_type": notification_type,  # "new_answer", "question_answered", etc.
        "question_title": question_title,
        "question_id": question_id,
        "timestamp": json.dumps(datetime.utcnow().isoformat())
    }
    
    await manager.send_message_to_user(message, user_id)


async def send_course_notification(user_id: str, course_title: str, course_id: str, notification_type: str):
    """Send course-related notification to user."""
    message = {
        "type": "course_notification",
        "notification_type": notification_type,  # "new_course", "course_completed", etc.
        "course_title": course_title,
        "course_id": course_id,
        "timestamp": json.dumps(datetime.utcnow().isoformat())
    }
    
    await manager.send_message_to_user(message, user_id)


async def send_system_notification(room: str, title: str, message: str, priority: str = "normal"):
    """Send system notification to a room."""
    notification = {
        "type": "system_notification",
        "title": title,
        "message": message,
        "priority": priority,  # "low", "normal", "high", "urgent"
        "timestamp": json.dumps(datetime.utcnow().isoformat())
    }
    
    await manager.send_message_to_room(notification, room)


# Export the router as websocket_router for main.py
websocket_router = router

# Export the manager for use in other modules
__all__ = ["websocket_router", "manager", "send_xp_notification", "send_badge_notification", 
           "send_forum_notification", "send_course_notification", "send_system_notification"] 