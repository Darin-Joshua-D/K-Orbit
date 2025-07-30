"""
K-Orbit Backend API
FastAPI application with Supabase integration, WebSocket support, and AI capabilities.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.auth.middleware import AuthMiddleware
from app.auth.routes import router as auth_router
from app.users.routes import router as users_router
from app.courses.routes import router as courses_router
from app.gamification.routes import router as gamification_router
from app.ai_agent.routes import router as ai_agent_router
from app.resources.routes import router as resources_router
from app.forum.routes import router as forum_router
from app.analytics.routes import router as analytics_router
from app.realtime.websocket import websocket_router

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    logger.info("K-Orbit API starting up...")
    
    # Initialize services
    try:
        # Add any startup logic here (DB connections, cache warming, etc.)
        logger.info("Application startup complete")
        yield
    finally:
        # Cleanup logic
        logger.info("K-Orbit API shutting down...")


# Create FastAPI application
app = FastAPI(
    title="K-Orbit API",
    description="AI-powered corporate onboarding & knowledge hub",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan
)

# Security middleware
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.getenv("ALLOWED_HOSTS", "").split(",")
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware (custom)
app.add_middleware(AuthMiddleware)


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging."""
    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "http_error"}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured logging."""
    logger.error(
        "Unexpected error occurred",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "server_error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}


# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(courses_router, prefix="/api/courses", tags=["Courses"])
app.include_router(gamification_router, prefix="/api/gamification", tags=["Gamification"])
app.include_router(ai_agent_router, prefix="/api/ai", tags=["AI Agent"])
app.include_router(resources_router, prefix="/api/resources", tags=["Resources"])
app.include_router(forum_router, prefix="/api/forum", tags=["Forum"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])

# WebSocket routes
app.include_router(websocket_router, prefix="/ws")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT") != "production",
        log_config=None  # Use structlog instead
    ) 