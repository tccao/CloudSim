# =============================================================================
# models.py - SQLAlchemy ORM Models
# =============================================================================
# Database models for CloudSim application.
#
# MODELS:
# - User: Authentication and authorization (email, password, role)
# - Instance: AWS EC2 instances synced to local database
# - Metric: CloudWatch metric snapshots persisted locally
#
# ROLES (User.role):
# - Admin: Full access to all resources AND user management (CRUD users)
# - DevOps Engineer: Full EC2 access (create, start, stop, terminate) but NO user management
# - User: View/manage only their own instances
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, CheckConstraint, Index
from datetime import datetime, timezone

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
    __table_args__ = (
        CheckConstraint(
            "role IN ('Admin', 'DevOps Engineer', 'User')",
            name="ck_users_role_valid",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="User", nullable=False)  # Admin, DevOps Engineer, User
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


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
    __table_args__ = (
        # Composite index: speeds up queries that filter by state AND sort by last_synced.
        # Example query this helps: "show all running instances, newest sync first"
        # Without this index, Postgres reads every row (full table scan).
        # With it, Postgres jumps directly to matching rows via B-tree lookup.
        Index("ix_instances_state_synced", "state", "last_synced"),
    )

    instance_id = Column(String, primary_key=True, index=True)  # AWS instance ID
    name = Column(String, nullable=True)  # Name tag
    instance_type = Column(String, nullable=False)  # t2.micro, etc.
    state = Column(String, default="pending")  # running, stopped, terminated, pending
    public_ip = Column(String, nullable=True)
    private_ip = Column(String, nullable=True)
    availability_zone = Column(String, nullable=True)
    launch_time = Column(DateTime, nullable=True)
    
    # Sync metadata
    last_synced = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_user_id = Column(Integer, nullable=True)  # User who created it


# =============================================================================
# METRIC MODEL
# =============================================================================
class Metric(Base):
    """
    CloudWatch metric snapshots persisted to local Postgres.

    WHY store metrics locally?
    - Reduces AWS API calls (CloudWatch charges per request at scale)
    - Keeps historical data available even if AWS is temporarily unreachable
    - Enables future features: trend queries, threshold alerts, cost analysis

    HOW IT WORKS:
    - Every time the Monitoring page loads, we fetch live data from CloudWatch
    - We then write each datapoint into this table as a side effect
    - The 'recorded_at' column is the CloudWatch timestamp (when AWS measured it)
    - The 'collected_at' column is when WE wrote the row (audit trail)

    COLUMNS:
    - id: Auto-increment primary key
    - instance_id: Which EC2 instance this reading belongs to
    - metric_name: e.g. "CPUUtilization", "NetworkIn", "NetworkOut"
    - value: The numeric reading (e.g. 45.5 for 45.5% CPU)
    - unit: AWS unit string ("Percent", "Bytes", "Count")
    - recorded_at: Timestamp from CloudWatch (when AWS measured it)
    - collected_at: When we wrote this row into our DB
    """
    __tablename__ = "metrics"
    __table_args__ = (
        # Composite index: fast lookup for "give me all CPU readings for instance X
        # in the last hour, sorted by time".
        # All 3 columns are needed: instance narrows the search,
        # metric_name picks the right metric, recorded_at lets us sort/filter by time.
        Index("ix_metrics_instance_name_recorded", "instance_id", "metric_name", "recorded_at"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String, nullable=False, index=True)  # e.g. i-0abc123
    metric_name = Column(String, nullable=False)              # CPUUtilization, NetworkIn, ...
    value       = Column(Float,  nullable=False)              # the numeric reading
    unit        = Column(String, nullable=True)               # Percent, Bytes, Count
    recorded_at = Column(DateTime, nullable=False)            # timestamp from CloudWatch
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)  # when we stored it
