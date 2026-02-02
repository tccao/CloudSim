# =============================================================================
# main.py - FastAPI Application Entry Point
# =============================================================================
# Main FastAPI application with middleware, routers, and startup configuration.
#
# FEATURES:
# - Security headers middleware (XSS, CSRF protection)
# - Dynamic CORS configuration from settings
# - Health check endpoints for load balancers
# - Automatic database table creation on startup
#
# API ROUTERS:
# - /api/auth/*  - Authentication (login, register, me)
# - /api/admin/* - Admin user management
# - /api/ec2/*   - EC2 instance operations
#
# STARTUP:
#   uvicorn app.main:app --reload
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .auth_routes import router as auth_router
from .admin_routes import router as admin_router
from .ec2_routes import router as ec2_router
from .db import engine, Base


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
# Create all database tables on startup (if they don't exist)
Base.metadata.create_all(bind=engine)


# =============================================================================
# SECURITY HEADERS MIDDLEWARE
# =============================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff (prevent MIME sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (XSS filter)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: Disable unnecessary browser features
    """
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


# =============================================================================
# APPLICATION SETUP
# =============================================================================
app = FastAPI(
    title="CloudSim API",
    version="1.0.0",
    description="Cloud infrastructure management API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================
@app.get("/health")
def health_check():
    """
    Basic health check for load balancers.
    
    Returns:
        status: "healthy"
        environment: Current environment (development/production)
    """
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================
# Auth routes: /api/auth/login, /api/auth/register, /api/auth/me
app.include_router(auth_router)

# Admin routes: /api/admin/users (CRUD)
app.include_router(admin_router)

# EC2 routes: /api/ec2/instances, /api/ec2/costs, etc.
app.include_router(ec2_router)


# =============================================================================
# STARTUP EVENT
# =============================================================================
@app.on_event("startup")
async def startup_event():
    """
    Log startup configuration.
    
    Logs:
    - Environment mode (development/production)
    - Configured CORS origins
    """
    import logging
    logger = logging.getLogger("uvicorn")
    
    logger.info(f"CloudSim API starting in {settings.environment} mode")
    logger.info(f"CORS origins: {settings.cors_origins}")
