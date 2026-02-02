# =============================================================================
# admin_routes.py - Admin API Endpoints
# =============================================================================
# Admin routes for user management. All endpoints require Admin role.
#
# ENDPOINTS:
# - GET    /api/admin/users           - List all users
# - POST   /api/admin/users           - Create user with role
# - PUT    /api/admin/users/{user_id} - Update user role/status
# - DELETE /api/admin/users/{user_id} - Delete user
#
# ROLE REQUIREMENT: Admin only (enforced via require_admin dependency)
#
# AVAILABLE ROLES:
# - Admin: Full access to all resources and user management
# - DevOps Engineer: Manage instances, view monitoring
# - User: View/manage only their own instances
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from .db import get_db
from .models import User
from .auth import get_password_hash, get_current_user, UserRead


# =============================================================================
# ROUTER SETUP
# =============================================================================
router = APIRouter(prefix="/api/admin", tags=["Admin"])


# =============================================================================
# SCHEMAS
# =============================================================================
class AdminUserCreate(BaseModel):
    """
    Admin creates user with specified role.
    
    Fields:
        email: User's email address
        password: Initial password
        role: One of "Admin", "DevOps Engineer", "User"
    """
    email: EmailStr
    password: str
    role: str = "User"  # Default role


class AdminUserUpdate(BaseModel):
    """
    Admin updates user role or status.
    
    Fields:
        role: New role (optional)
        is_active: Account status (optional)
    """
    role: Optional[str] = None
    is_active: Optional[bool] = None


# =============================================================================
# HELPER - require_admin Dependency
# =============================================================================
def require_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency to require Admin role.
    
    Usage:
        @router.get("/admin-only")
        def admin_route(admin: User = Depends(require_admin)):
            ...
    
    Raises:
        403 Forbidden: If user is not an Admin
    """
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# =============================================================================
# GET /api/admin/users - List All Users
# =============================================================================
@router.get("/users", response_model=list[UserRead])
async def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    List all users in the system.
    
    REQUIRES: Admin role
    
    RESPONSE:
        [
            {"id": 1, "email": "admin@example.com", "role": "Admin", "is_active": true},
            {"id": 2, "email": "user@example.com", "role": "User", "is_active": true}
        ]
    
    RETURNS:
        200: List of all users
        403: Not an Admin
    """
    return db.query(User).all()


# =============================================================================
# POST /api/admin/users - Create User
# =============================================================================
@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Create a new user with specified role.
    
    REQUIRES: Admin role
    
    REQUEST BODY:
        {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "role": "DevOps Engineer"
        }
    
    VALID ROLES: Admin, DevOps Engineer, User
    
    RETURNS:
        201: User created successfully
        400: Invalid role
        403: Not an Admin
        409: Email already registered
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Validate role
    valid_roles = ["Admin", "DevOps Engineer", "User"]
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    # Create user with hashed password
    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# =============================================================================
# PUT /api/admin/users/{user_id} - Update User
# =============================================================================
@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Update user role or active status.
    
    REQUIRES: Admin role
    
    REQUEST BODY (all fields optional):
        {
            "role": "DevOps Engineer",
            "is_active": false
        }
    
    RESTRICTIONS:
    - Cannot disable your own account
    
    RETURNS:
        200: User updated successfully
        400: Invalid role or self-disable attempt
        403: Not an Admin
        404: User not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from disabling themselves
    if user.id == admin.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )
    
    # Update role if provided
    if user_data.role is not None:
        valid_roles = ["Admin", "DevOps Engineer", "User"]
        if user_data.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
        user.role = user_data.role
    
    # Update active status if provided
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


# =============================================================================
# DELETE /api/admin/users/{user_id} - Delete User
# =============================================================================
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Delete a user permanently.
    
    REQUIRES: Admin role
    
    RESTRICTIONS:
    - Cannot delete your own account
    
    RETURNS:
        200: User deleted successfully
        400: Self-delete attempt
        403: Not an Admin
        404: User not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.email} deleted successfully"}
