from sqlalchemy import Column, String, Integer, DateTime, Boolean
from datetime import datetime
from .db import Base


# ============================================================================
# USER MODEL - Authentication
# ============================================================================
class User(Base):
    """
    User model for authentication.
    
    Design decisions:
    - email as unique identifier (not username) - more common in modern apps
    - hashed_password: NEVER store plain text passwords
    - is_active: Allows soft-disable without deleting user data
    - role: User role for access control (Admin, DevOps Engineer, User)
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="User")  # Admin, DevOps Engineer, User
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# INSTANCE MODEL - AWS EC2 instances synced to local DB
# ============================================================================
class Instance(Base):
    """
    Instance model synced from AWS EC2.
    
    Primary key is AWS instance_id (e.g., i-0834eaf5fc105be28).
    Data is synced from AWS on each API call.
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

