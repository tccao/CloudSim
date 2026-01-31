"""
Authentication module for CloudSim.

DESIGN DECISIONS:
-----------------
1. JWT (JSON Web Tokens) - Chosen over session-based auth because:
   - Stateless: No server-side session storage needed
   - Scalable: Works across multiple servers without shared session store
   - Mobile-friendly: Easy to use in mobile/SPA clients
   
2. bcrypt for password hashing - Industry standard because:
   - Slow by design: Resistant to brute-force attacks
   - Includes salt: Prevents rainbow table attacks
   - Configurable work factor: Can increase as hardware improves

3. OAuth2 Password Flow - Simple username/password exchange for token
   - Trade-off: Less secure than OAuth2 Authorization Code flow
   - Benefit: Simpler implementation for first-party apps

SECURITY NOTES:
- SECRET_KEY should be in environment variables in production
- Token expiration set to 30 minutes (balance between security and UX)
- Access tokens only; refresh tokens can be added later for better UX
"""

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

# ============================================================================
# CONFIGURATION (from .env via config.py)
# ============================================================================
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# ============================================================================
# PASSWORD HASHING
# ============================================================================
# CryptContext handles the complexity of password hashing
# - schemes: List of allowed hashing algorithms (bcrypt is recommended)
# - deprecated: "auto" marks old schemes for migration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# OAUTH2 SETUP
# ============================================================================
# OAuth2PasswordBearer extracts token from Authorization header
# tokenUrl is where clients POST username/password to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================================================
# PYDANTIC SCHEMAS FOR AUTH
# ============================================================================
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
    """Response model for user data (excludes password)."""
    id: int
    email: str
    role: str  # Admin, DevOps Engineer, User
    is_active: bool

    class Config:
        from_attributes = True  # Allows ORM model conversion


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    Uses constant-time comparison to prevent timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    Automatically generates a random salt.
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
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Dependency to get the current authenticated user from JWT token.
    
    Used as: current_user = Depends(get_current_user)
    
    Raises:
        HTTPException 401: If token is invalid or user not found
    """
    from .models import User  # Import here to avoid circular imports
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user
