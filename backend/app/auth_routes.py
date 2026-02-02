# =============================================================================
# auth_routes.py - Authentication API Endpoints
# =============================================================================
# Authentication routes for user registration, login, and profile access.
#
# ENDPOINTS:
# - POST /api/auth/register - Create new user account
# - POST /api/auth/login    - Authenticate and get JWT token
# - GET  /api/auth/me       - Get current user info (protected)
#
# DESIGN DECISIONS:
# - Separate router for auth: Clean separation of concerns
# - OAuth2PasswordRequestForm: Standard form for username/password submission
# - Email used as "username": More intuitive for users
#
# SECURITY:
# - Same error message for invalid email or password (prevents enumeration)
# - Passwords are hashed with bcrypt before storage
# - JWT tokens expire after 30 minutes (configurable)
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .auth import (
    Token,
    UserCreate,
    UserRead,
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)


# =============================================================================
# ROUTER SETUP
# =============================================================================
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# =============================================================================
# POST /api/auth/register - User Registration
# =============================================================================
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    REQUEST BODY:
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }
    
    PROCESS:
    1. Check if email already exists (409 Conflict if so)
    2. Hash the password (never store plain text!)
    3. Create user record in database with default "User" role
    4. Return user data (without password)
    
    SECURITY NOTE:
    We return 409 for existing emails. In high-security apps,
    you might return 201 always to prevent email enumeration attacks.
    
    RETURNS:
        201: User created successfully
        409: Email already registered
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# =============================================================================
# POST /api/auth/login - User Login
# =============================================================================
@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT token.
    
    REQUEST (form-urlencoded):
        username=user@example.com&password=securepassword123
    
    NOTE: OAuth2 spec uses "username" field, we accept email here.
    
    RESPONSE:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "token_type": "bearer"
        }
    
    USAGE:
    Include token in subsequent requests:
        Authorization: Bearer <access_token>
    
    SECURITY:
    Same error message for invalid email or password to prevent user enumeration.
    
    RETURNS:
        200: Login successful, token returned
        401: Incorrect email or password
        403: Account is disabled
    """
    # Find user by email (username field contains email)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Validate credentials (same message for both failures)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create access token with user email as subject
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}


# =============================================================================
# GET /api/auth/me - Get Current User
# =============================================================================
@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    
    REQUIRES: Valid JWT token in Authorization header
    
    USAGE:
        curl -H "Authorization: Bearer <token>" http://localhost:8000/api/auth/me
    
    RESPONSE:
        {
            "id": 1,
            "email": "user@example.com",
            "role": "User",
            "is_active": true
        }
    
    RETURNS:
        200: User data returned
        401: Invalid or missing token
    """
    return current_user
