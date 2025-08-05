"""
Authentication routes for K-Orbit API.
Handles user login, registration, token refresh, and profile management.
"""

import os
from datetime import datetime
from typing import Dict, Any
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends, status, WebSocket
from supabase import create_client, Client

from app.auth.models import (
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    UpdatePasswordRequest,
    UserProfile,
    InviteUserRequest,
    UpdateProfileRequest,
    VerifyEmailRequest
)
from app.auth.middleware import get_current_user, require_admin, require_manager

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)
supabase_admin: Client = create_client(supabase_url, supabase_service_key)

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password.
    Returns JWT tokens and user profile.
    """
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Get user profile
        profile_response = supabase.table("profiles").select("*").eq("id", auth_response.user.id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )
        
        # Update last active timestamp
        supabase.table("profiles").update({
            "last_active": datetime.utcnow().isoformat()
        }).eq("id", auth_response.user.id).execute()
        
        user_profile = UserProfile(
            id=auth_response.user.id,
            email=auth_response.user.email,
            full_name=profile_response.data["full_name"],
            role=profile_response.data["role"],
            org_id=profile_response.data["org_id"],
            avatar_url=profile_response.data.get("avatar_url"),
            department=profile_response.data.get("department"),
            position=profile_response.data.get("position"),
            manager_id=profile_response.data.get("manager_id"),
            onboarding_completed=profile_response.data.get("onboarding_completed", False),
            last_active=datetime.fromisoformat(profile_response.data["last_active"]) if profile_response.data.get("last_active") else None,
            created_at=datetime.fromisoformat(profile_response.data["created_at"]),
            updated_at=datetime.fromisoformat(profile_response.data["updated_at"]) if profile_response.data.get("updated_at") else None
        )
        
        logger.info(
            "User logged in successfully",
            user_id=auth_response.user.id,
            email=request.email,
            role=profile_response.data["role"]
        )
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            expires_in=auth_response.session.expires_in or 3600,
            user=user_profile
        )
        
    except Exception as e:
        logger.error("Login failed", email=request.email, error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user account.
    Creates user in Supabase Auth and profile in database.
    """
    try:
        # Check if organization exists (you might want to validate org_id)
        # This is a simplified version - in production, validate org_id
        
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "full_name": request.full_name,
                    "role": request.role,
                    "org_id": request.org_id
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=400,
                detail="Failed to create user account"
            )
        
        # Create user profile
        profile_data = {
            "id": auth_response.user.id,
            "email": request.email,
            "full_name": request.full_name,
            "role": request.role,
            "org_id": request.org_id,
            "onboarding_completed": False,
            "created_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat()
        }
        
        profile_response = supabase.table("profiles").insert(profile_data).execute()
        
        if not profile_response.data:
            # Cleanup: delete the auth user if profile creation failed
            supabase_admin.auth.admin.delete_user(auth_response.user.id)
            raise HTTPException(
                status_code=500,
                detail="Failed to create user profile"
            )
        
        user_profile = UserProfile(
            id=auth_response.user.id,
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            org_id=request.org_id,
            onboarding_completed=False,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        
        logger.info(
            "User registered successfully",
            user_id=auth_response.user.id,
            email=request.email,
            role=request.role,
            org_id=request.org_id
        )
        
        # Return tokens if session exists (email confirmation might be required)
        if auth_response.session:
            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                expires_in=auth_response.session.expires_in or 3600,
                user=user_profile
            )
        else:
            # Email confirmation required
            raise HTTPException(
                status_code=201,
                detail="Registration successful. Please check your email to verify your account."
            )
        
    except Exception as e:
        logger.error("Registration failed", email=request.email, error=str(e))
        if "already registered" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="Email address is already registered"
            )
        raise HTTPException(
            status_code=400,
            detail="Registration failed"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh JWT access token using refresh token.
    """
    try:
        auth_response = supabase.auth.refresh_session(request.refresh_token)
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        
        # Get updated user profile
        profile_response = supabase.table("profiles").select("*").eq("id", auth_response.user.id).single().execute()
        
        user_profile = UserProfile(
            id=auth_response.user.id,
            email=auth_response.user.email,
            full_name=profile_response.data["full_name"],
            role=profile_response.data["role"],
            org_id=profile_response.data["org_id"],
            avatar_url=profile_response.data.get("avatar_url"),
            department=profile_response.data.get("department"),
            position=profile_response.data.get("position"),
            manager_id=profile_response.data.get("manager_id"),
            onboarding_completed=profile_response.data.get("onboarding_completed", False),
            last_active=datetime.fromisoformat(profile_response.data["last_active"]) if profile_response.data.get("last_active") else None,
            created_at=datetime.fromisoformat(profile_response.data["created_at"]),
            updated_at=datetime.fromisoformat(profile_response.data["updated_at"]) if profile_response.data.get("updated_at") else None
        )
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            expires_in=auth_response.session.expires_in or 3600,
            user=user_profile
        )
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Failed to refresh token"
        )


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout user and invalidate session.
    """
    try:
        supabase.auth.sign_out()
        
        logger.info("User logged out successfully", user_id=user["sub"])
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error("Logout failed", user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Logout failed"
        )


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Send password reset email to user.
    """
    try:
        supabase.auth.reset_password_email(request.email)
        
        logger.info("Password reset email sent", email=request.email)
        
        return {"message": "Password reset email sent"}
        
    except Exception as e:
        logger.error("Password reset failed", email=request.email, error=str(e))
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/update-password")
async def update_password(
    request: UpdatePasswordRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update user password (requires current password).
    """
    try:
        # Verify current password by attempting to sign in
        try:
            supabase.auth.sign_in_with_password({
                "email": user["email"],
                "password": request.current_password
            })
        except:
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )
        
        # Update password
        supabase.auth.update_user({"password": request.new_password})
        
        logger.info("Password updated successfully", user_id=user["sub"])
        
        return {"message": "Password updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password update failed", user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update password"
        )


@router.get("/profile", response_model=UserProfile)
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Get current user profile.
    """
    try:
        profile_response = supabase.table("profiles").select("*").eq("id", user["sub"]).single().execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )
        
        return UserProfile(
            id=user["sub"],
            email=user["email"],
            full_name=profile_response.data["full_name"],
            role=profile_response.data["role"],
            org_id=profile_response.data["org_id"],
            avatar_url=profile_response.data.get("avatar_url"),
            department=profile_response.data.get("department"),
            position=profile_response.data.get("position"),
            manager_id=profile_response.data.get("manager_id"),
            onboarding_completed=profile_response.data.get("onboarding_completed", False),
            last_active=datetime.fromisoformat(profile_response.data["last_active"]) if profile_response.data.get("last_active") else None,
            created_at=datetime.fromisoformat(profile_response.data["created_at"]),
            updated_at=datetime.fromisoformat(profile_response.data["updated_at"]) if profile_response.data.get("updated_at") else None
        )
        
    except Exception as e:
        logger.error("Failed to get user profile", user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to get user profile"
        )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    request: UpdateProfileRequest,
    user: dict = Depends(get_current_user)
):
    """
    Update current user profile.
    """
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        profile_response = supabase.table("profiles").update(update_data).eq("id", user["sub"]).execute()
        
        if not profile_response.data:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )
        
        updated_profile = profile_response.data[0]
        
        logger.info("User profile updated", user_id=user["sub"], updated_fields=list(update_data.keys()))
        
        return UserProfile(
            id=user["sub"],
            email=user["email"],
            full_name=updated_profile["full_name"],
            role=updated_profile["role"],
            org_id=updated_profile["org_id"],
            avatar_url=updated_profile.get("avatar_url"),
            department=updated_profile.get("department"),
            position=updated_profile.get("position"),
            manager_id=updated_profile.get("manager_id"),
            onboarding_completed=updated_profile.get("onboarding_completed", False),
            last_active=datetime.fromisoformat(updated_profile["last_active"]) if updated_profile.get("last_active") else None,
            created_at=datetime.fromisoformat(updated_profile["created_at"]),
            updated_at=datetime.fromisoformat(updated_profile["updated_at"]) if updated_profile.get("updated_at") else None
        )
        
    except Exception as e:
        logger.error("Failed to update user profile", user_id=user["sub"], error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to update user profile"
        )


@router.post("/invite", dependencies=[Depends(require_manager)])
async def invite_user(
    request: InviteUserRequest,
    user: dict = Depends(get_current_user)
):
    """
    Invite a new user to the organization (Manager+ only).
    """
    try:
        # Create user invitation
        invite_response = supabase.auth.admin.invite_user_by_email(
            request.email,
            options={
                "data": {
                    "full_name": request.full_name,
                    "role": request.role,
                    "org_id": user["org_id"],
                    "department": request.department,
                    "position": request.position,
                    "manager_id": request.manager_id,
                    "invited_by": user["sub"]
                }
            }
        )
        
        if not invite_response.user:
            raise HTTPException(
                status_code=400,
                detail="Failed to send invitation"
            )
        
        logger.info(
            "User invitation sent",
            invited_email=request.email,
            invited_by=user["sub"],
            role=request.role,
            org_id=user["org_id"]
        )
        
        return {"message": f"Invitation sent to {request.email}"}
        
    except Exception as e:
        logger.error("Failed to invite user", email=request.email, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to send invitation"
        )


from app.database.supabase_client import supabase

@router.get("/{user_id}")
async def get_user(user_id: str):
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    if response.error:
        raise HTTPException(status_code=500, detail="Error fetching user")
    return response.data


@router.websocket("/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Example: Send a message when a new user is added
    response = supabase.table("users").select("*").execute()
    await websocket.send_json(response.data)