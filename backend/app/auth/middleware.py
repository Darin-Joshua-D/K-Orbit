"""
Authentication middleware for Supabase JWT verification.
Handles token validation and user context injection.
"""

import os
from typing import Optional
import jwt
import structlog
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from supabase import Client

from app.database.supabase_client import supabase_admin, supabase

logger = structlog.get_logger()

# Security scheme for extracting bearer token
http_bearer = HTTPBearer(auto_error=False)

# Public routes that don't require authentication
PUBLIC_ROUTES = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/reset-password",
    "/ws",
    "/static",
    "/favicon.ico",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Custom authentication middleware for Supabase JWT verification."""

    async def dispatch(self, request: Request, call_next: callable) -> Response:
        """
        Processes the request, verifies authentication, and injects user context.
        """
        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Extract and verify token
        try:
            user = await self._verify_token(request)
            if user:
                user["sub"] = user.get("sub") or user.get("id")
                request.state.user = user
                request.state.user_id = user["sub"]
                request.state.org_id = user.get("org_id")
            else:
                raise HTTPException(status_code=401, detail="Invalid or missing authentication token")
        except HTTPException as e:
            logger.warning(
                "Authentication failed",
                path=request.url.path,
                method=request.method,
                error=e.detail,
                ip=request.client.host if request.client else "unknown"
            )
            return Response(content=f'{{"detail":"{e.detail}"}}', status_code=e.status_code, media_type="application/json")

        return await call_next(request)

    def _is_public_route(self, path: str) -> bool:
        """Check if the route is public."""
        return path in PUBLIC_ROUTES or any(path.startswith(prefix) for prefix in ["/ws/", "/static/"])

    async def _verify_token(self, request: Request) -> Optional[dict]:
        """Verify the JWT token from the request."""
        credentials = await http_bearer(request)
        if not credentials or not credentials.credentials:
            return None

        token = credentials.credentials
        try:
            # First, try to validate with Supabase client (standard user JWTs)
            user_data = supabase.auth.get_user(token)
            if user_data:
                return user_data.user.dict()
        except Exception:
            # If Supabase client fails, try admin client for service roles
            try:
                user_data = supabase_admin.auth.get_user(token)
                if user_data:
                    return user_data.user.dict()
            except Exception as e:
                logger.warning("Token validation failed for both user and admin", error=str(e))
                return None
        
        return None


async def get_current_user(request: Request) -> dict:
    """Dependency to get current user from request state."""
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return request.state.user


async def get_current_user_id(request: Request) -> str:
    """Dependency to get current user ID from request state."""
    user = await get_current_user(request)
    return user["sub"]


def require_role(required_roles: list[str]):
    """Dependency factory to require specific roles."""
    async def role_checker(request: Request) -> dict:
        user = request.state.user
        if not user or user.get("role") not in required_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {required_roles}"
            )
        return user
    return role_checker


# Role-specific dependencies
async def require_admin(request: Request) -> dict:
    """Require admin role."""
    return await require_role(["admin", "super_admin"])(request)


async def require_manager(request: Request) -> dict:
    """Require manager or higher role."""
    return await require_role(["manager", "admin", "super_admin"])(request)


async def require_sme(request: Request) -> dict:
    """Require SME or higher role."""
    return await require_role(["sme", "manager", "admin", "super_admin"])(request)