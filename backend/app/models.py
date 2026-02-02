# =============================================================================
# models.py - SQLAlchemy ORM Models
# =============================================================================
# Database models for CloudSim application.
#
# MODELS:
# - User: Authentication and authorization (email, password, role)
# - Instance: AWS EC2 instances synced to local database
#
# ROLES (User.role):
# - Admin: Full access to all resources and user management
# - DevOps Engineer: Manage instances, view monitoring, no user management
# - User: View/manage only their own instances
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from datetime import datetime

from .db import Base


# =============================================================================
# USER MODEL
# =============================================================================
class User(Base):
    """
    User model for authentication and authorization.
    
    DESIGN DECISIONS:
    - email as unique identifier (not username) - more common in modern apps
    - hashed_password: NEVER store plain text passwords
    - is_active: Allows soft-disable without deleting user data
    - role: User role for access control (Admin, DevOps Engineer, User)
    
    COLUMNS:
    - id: Primary key (auto-increment)
    - email: Unique email address for login
    - hashed_password: bcrypt-hashed password
    - role: User role (Admin, DevOps Engineer, User)
    - is_active: Whether account is active
    - created_at: Account creation timestamp
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="User")  # Admin, DevOps Engineer, User
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# INSTANCE MODEL
# =============================================================================
class Instance(Base):
    """
    EC2 Instance model synced from AWS.
    
    DESIGN DECISIONS:
    - Primary key is AWS instance_id (e.g., i-0834eaf5fc105be28)
    - Data is synced from AWS on each API call
    - Local copy allows for faster queries and offline display
    
    COLUMNS:
    - instance_id: AWS instance ID (primary key)
    - name: Instance name (from Name tag)
    - instance_type: EC2 type (t2.micro, t2.small, etc.)
    - state: Instance state (running, stopped, terminated, pending)
    - public_ip: Public IPv4 address (if assigned)
    - private_ip: Private IPv4 address
    - availability_zone: AWS AZ (us-east-1a, etc.)
    - launch_time: When instance was launched
    - last_synced: When we last synced from AWS
    - created_by_user_id: CloudSim user who created this instance
    """
    __tablename__ = "instances"

    instance_id = Column(String, primary_key=True, index=True)  # AWS instance ID
    name = Column(String, nullable=True)  # Name tag
    instance_type = Column(String, nullable=False)  # t2.micro, etc.
    state = Column(String, default="pending")  # running, stopped, terminated, pending
    public_ip = Column(String, nullable=True)
    private_ip = Column(String, nullable=True)
    availability_zone = Column(String, nullable=True)
    launch_time = Column(DateTime, nullable=True)
    
    # Sync metadata
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_by_user_id = Column(Integer, nullable=True)  # User who created it
