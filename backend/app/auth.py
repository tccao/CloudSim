# =============================================================================
# auth.py - Authentication Core Module
# =============================================================================
# Core authentication utilities for CloudSim.
#
# PROVIDES:
# - Password hashing (bcrypt)
# - JWT token creation and validation
# - OAuth2 password flow setup
# - get_current_user dependency
#
# DESIGN DECISIONS:
# - JWT (JSON Web Tokens): Stateless, scalable, mobile-friendly
# - bcrypt: Slow by design, salt included, configurable work factor
# - OAuth2 Password Flow: Simple for first-party apps
#
# SECURITY NOTES:
# - SECRET_KEY must be in environment variables in production
# - Token expiration: 30 minutes (configurable)
# - Access tokens only; refresh tokens can be added later
#
# USAGE:
#   from .auth import get_current_user, create_access_token, verify_password
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from .db import get_db
from .config import settings


# =============================================================================
# CONFIGURATION
# =============================================================================
# Load from settings (which reads from .env)
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


# =============================================================================
# PASSWORD HASHING
# =============================================================================
# CryptContext handles the complexity of password hashing
# - schemes: List of allowed hashing algorithms (bcrypt is recommended)
# - deprecated: "auto" marks old schemes for migration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# OAUTH2 SETUP
# =============================================================================
# OAuth2PasswordBearer extracts token from Authorization header
# tokenUrl is where clients POST username/password to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================
class Token(BaseModel):
    """Response model for login endpoint."""
    access_token: str
    token_type: str  # Always "bearer" for JWT


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    email: Optional[str] = None


class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr  # Validates email format
    password: str


class UserRead(BaseModel):
    """
    Response model for user data (excludes password).
    
    Used when returning user information to the client.
    Never includes hashed_password.
    """
    id: int
    email: str
    role: str  # Admin, DevOps Engineer, User
    is_active: bool

    class Config:
        from_attributes = True  # Allows ORM model conversion


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        plain_password: The password entered by user
        hashed_password: The stored bcrypt hash
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Automatically generates a random salt.
    
    Args:
        password: Plain text password
        
    Returns:
        bcrypt hash string
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload to encode (typically {"sub": user_email})
        expires_delta: Token lifetime (defaults to ACCESS_TOKEN_EXPIRE_MINUTES)
    
    Returns:
        Encoded JWT string
        
    Example:
        token = create_access_token(data={"sub": "user@example.com"})
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =============================================================================
# DEPENDENCY - get_current_user
# =============================================================================
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Dependency to get the current authenticated user from JWT token.
    
    Used as: current_user = Depends(get_current_user)
    
    Process:
    1. Extract token from Authorization header (via oauth2_scheme)
    2. Decode and validate JWT token
    3. Extract user email from token payload
    4. Fetch user from database
    5. Return user object
    
    Raises:
        HTTPException 401: If token is invalid or user not found
        
    Example:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user": current_user.email}
    """
    from .models import User  # Import here to avoid circular imports
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Fetch user from database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user
