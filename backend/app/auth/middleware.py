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
from supabase import create_client, Client

logger = structlog.get_logger()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase_secret = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([supabase_url, supabase_key]):
    raise ValueError("Missing required Supabase environment variables")

supabase: Client = create_client(supabase_url, supabase_key)
supabase_admin: Client = create_client(supabase_url, supabase_secret)

# Security scheme
security = HTTPBearer(auto_error=False)

# Public routes that don't require authentication
PUBLIC_ROUTES = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/reset-password",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Custom authentication middleware for Supabase JWT verification."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and verify authentication."""
        
        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)
        
        # Extract and verify token
        user = await self._verify_token(request)
        
        if user:
            # Inject user into request state
            request.state.user = user
            request.state.user_id = user.get("sub")
            request.state.org_id = user.get("org_id")
        else:
            # Return 401 for protected routes without valid token
            logger.warning(
                "Unauthorized access attempt",
                path=request.url.path,
                method=request.method,
                ip=request.client.host if request.client else None
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing authentication token"
            )
        
        response = await call_next(request)
        return response
    
    def _is_public_route(self, path: str) -> bool:
        """Check if the route is public and doesn't require authentication."""
        # Exact match
        if path in PUBLIC_ROUTES:
            return True
        
        # Prefix match for WebSocket and static files
        public_prefixes = ["/ws", "/static", "/favicon.ico"]
        return any(path.startswith(prefix) for prefix in public_prefixes)
    
    async def _verify_token(self, request: Request) -> Optional[dict]:
        """Extract and verify JWT token from request."""
        try:
            # Get token from Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            token = authorization.split(" ")[1]
            
            # Verify JWT token with Supabase
            try:
                # Use Supabase to verify the token
                response = supabase.auth.get_user(token)
                if response.user:
                    # Get additional user profile data
                    profile_response = supabase.table("profiles").select("*").eq("id", response.user.id).single().execute()
                    
                    user_data = {
                        "sub": response.user.id,
                        "email": response.user.email,
                        "role": profile_response.data.get("role") if profile_response.data else "learner",
                        "org_id": profile_response.data.get("org_id") if profile_response.data else None,
                        "full_name": profile_response.data.get("full_name") if profile_response.data else None,
                    }
                    
                    logger.info(
                        "User authenticated successfully",
                        user_id=user_data["sub"],
                        email=user_data["email"],
                        role=user_data["role"]
                    )
                    
                    return user_data
                    
            except Exception as e:
                logger.error("Supabase token verification failed", error=str(e))
                return None
                
        except Exception as e:
            logger.error("Token extraction/verification failed", error=str(e))
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


async def require_role(required_roles: list[str]):
    """Dependency factory to require specific roles."""
    def role_checker(request: Request) -> dict:
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