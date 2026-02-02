# =============================================================================
# ec2_routes.py - EC2 API Endpoints
# =============================================================================
# EC2 instance management API routes for CloudSim.
#
# INSTANCE ENDPOINTS:
# - GET    /api/ec2/instances                    - List instances
# - GET    /api/ec2/instances/{id}               - Get instance details
# - POST   /api/ec2/instances                    - Create instance
# - POST   /api/ec2/instances/{id}/start         - Start instance
# - POST   /api/ec2/instances/{id}/stop          - Stop instance
# - POST   /api/ec2/instances/{id}/reboot        - Reboot instance
# - DELETE /api/ec2/instances/{id}               - Terminate instance
# - GET    /api/ec2/instance-types               - List available types
#
# METRICS ENDPOINTS:
# - GET    /api/ec2/instances/{id}/metrics       - CloudWatch metrics history
# - GET    /api/ec2/instances/{id}/metrics/current - Current metrics
#
# COST ENDPOINTS:
# - GET    /api/ec2/costs/daily                  - Daily cost breakdown
# - GET    /api/ec2/costs/summary                - Monthly cost summary
#
# ACCESS CONTROL:
# - Admin: Full access to all instances
# - DevOps Engineer: Full access to all instances
# - User: Access only to instances they created (via CreatedBy tag)
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .auth import get_current_user
from .models import User, Instance
from .db import get_db
from . import aws_service


# =============================================================================
# ROUTER SETUP
# =============================================================================
router = APIRouter(prefix="/api/ec2", tags=["EC2"])


# =============================================================================
# SCHEMAS - Request/Response Models
# =============================================================================
class Tag(BaseModel):
    """AWS resource tag."""
    Key: str
    Value: str


class SecurityGroup(BaseModel):
    """EC2 security group reference."""
    GroupId: str
    GroupName: str


class BlockDevice(BaseModel):
    """EBS volume attached to instance."""
    device_name: str
    volume_id: str
    size: int
    volume_type: str
    iops: Optional[int] = 0
    throughput: Optional[int] = 0
    encrypted: bool
    delete_on_termination: bool


class InstanceResponse(BaseModel):
    """
    Instance summary for list endpoint.
    
    Used by: GET /api/ec2/instances
    """
    instance_id: str
    name: str
    instance_type: str
    state: str
    public_ip: Optional[str]
    private_ip: Optional[str]
    launch_time: Optional[str]
    availability_zone: str


class InstanceDetailResponse(InstanceResponse):
    """
    Full instance details.
    
    Used by: GET /api/ec2/instances/{id}
    """
    key_name: Optional[str] = None
    platform: str
    tenancy: str
    ami_id: str
    monitoring: str
    
    # Network
    public_dns: Optional[str]
    private_dns: Optional[str]
    vpc_id: Optional[str]
    subnet_id: Optional[str]
    security_groups: list[SecurityGroup] = []
    
    # Storage
    block_devices: list[BlockDevice] = []
    
    # Metadata
    tags: list[Tag] = []
    iam_role: Optional[str] = None


class CreateInstanceRequest(BaseModel):
    """
    Request body for creating instance.
    
    Used by: POST /api/ec2/instances
    """
    name: str
    instance_type: str = "t2.micro"


class ActionResponse(BaseModel):
    """
    Response for instance actions (start, stop, terminate).
    
    Used by: POST/DELETE instance action endpoints
    """
    message: str
    instance_id: str


# =============================================================================
# HELPER - Sync Instances to Database
# =============================================================================
def sync_instances_to_db(aws_instances: list, db: Session):
    """
    Sync AWS EC2 instances to local PostgreSQL database.
    
    Creates new records for new instances, updates existing ones.
    This allows for faster local queries and offline display.
    
    Args:
        aws_instances: List of instance dicts from AWS
        db: SQLAlchemy database session
    """
    for inst in aws_instances:
        db_instance = db.query(Instance).filter(
            Instance.instance_id == inst["instance_id"]
        ).first()
        
        # Parse launch time
        launch_time = None
        if inst.get("launch_time"):
            try:
                launch_time = datetime.fromisoformat(
                    inst["launch_time"].replace("Z", "+00:00")
                )
            except:
                pass
        
        if db_instance:
            # Update existing instance
            db_instance.name = inst.get("name", "")
            db_instance.instance_type = inst["instance_type"]
            db_instance.state = inst["state"]
            db_instance.public_ip = inst.get("public_ip")
            db_instance.private_ip = inst.get("private_ip")
            db_instance.availability_zone = inst.get("availability_zone", "")
            db_instance.launch_time = launch_time
            db_instance.last_synced = datetime.utcnow()
        else:
            # Create new instance record
            db_instance = Instance(
                instance_id=inst["instance_id"],
                name=inst.get("name", ""),
                instance_type=inst["instance_type"],
                state=inst["state"],
                public_ip=inst.get("public_ip"),
                private_ip=inst.get("private_ip"),
                availability_zone=inst.get("availability_zone", ""),
                launch_time=launch_time,
                last_synced=datetime.utcnow(),
            )
            db.add(db_instance)
    
    db.commit()


# =============================================================================
# HELPER - Filter Instances by Ownership
# =============================================================================
def _filter_instances_for_user(instances: list, user: User) -> list:
    """
    Filter instances based on user role.
    
    Access Control:
    - Admin/DevOps: See all instances
    - User: See only instances they created (CreatedBy tag matches user ID)
    
    Args:
        instances: List of instance dicts from AWS
        user: Current authenticated user
        
    Returns:
        Filtered list of instances
    """
    # Admin and DevOps can see all instances
    if user.role in ["Admin", "DevOps Engineer"]:
        return instances
    
    # For User role, filter by CreatedBy tag
    filtered = []
    for inst in instances:
        # Check if instance was created by this user
        created_by = None
        if "tags" in inst:
            for tag in inst.get("tags", []):
                if tag.get("Key") == "CreatedBy":
                    created_by = tag.get("Value")
                    break
        
        if created_by == str(user.id):
            filtered.append(inst)
    
    return filtered


# =============================================================================
# HELPER - Check Instance Ownership
# =============================================================================
def _check_instance_ownership(instance_id: str, user: User) -> bool:
    """
    Check if user owns the instance (by CreatedBy tag).
    
    Used for instance actions (start, stop, reboot, terminate).
    Admins and DevOps can access any instance.
    
    Args:
        instance_id: EC2 instance ID
        user: Current authenticated user
        
    Returns:
        True if user can access this instance
    """
    # Admin and DevOps can access any instance
    if user.role in ["Admin", "DevOps Engineer"]:
        return True
    
    # For User role, check ownership via CreatedBy tag
    try:
        instance = aws_service.get_instance(instance_id)
        if not instance:
            return False
        
        # Check CreatedBy tag
        for tag in instance.get("tags", []):
            if tag.get("Key") == "CreatedBy" and tag.get("Value") == str(user.id):
                return True
        
        return False
    except Exception:
        return False


# =============================================================================
# ENDPOINT - List Instances
# =============================================================================
@router.get("/instances", response_model=list[InstanceResponse])
async def list_instances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List EC2 instances.
    
    ACCESS CONTROL:
    - Admin/DevOps: See all instances
    - User: See only instances they created
    
    RETURNS:
        200: List of instances
        401: Not authenticated
        500: AWS API error
    """
    try:
        # Fetch from AWS
        instances = aws_service.list_instances()
        
        # Sync to local database
        sync_instances_to_db(instances, db)
        
        # Filter based on user role
        filtered_instances = _filter_instances_for_user(instances, current_user)
        return filtered_instances
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Get Instance Details
# =============================================================================
@router.get("/instances/{instance_id}", response_model=InstanceDetailResponse)
async def get_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information for a specific EC2 instance.
    
    ACCESS CONTROL:
    - Admin/DevOps: View any instance
    - User: View only instances they created
    
    RETURNS:
        200: Instance details
        403: Access denied (not your instance)
        404: Instance not found
        500: AWS API error
    """
    try:
        instance = aws_service.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
        
        # Check ownership for User role
        if current_user.role == "User":
            created_by = None
            for tag in instance.get("tags", []):
                if tag.get("Key") == "CreatedBy":
                    created_by = tag.get("Value")
                    break
            
            if created_by != str(current_user.id):
                raise HTTPException(
                    status_code=403, 
                    detail="You can only view instances you created"
                )
        
        return instance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Create Instance
# =============================================================================
@router.post("/instances", response_model=ActionResponse)
async def create_instance(
    request: CreateInstanceRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new EC2 instance.
    
    All authenticated users can create instances.
    Instances are tagged with CreatedBy to track ownership.
    
    REQUEST BODY:
        {
            "name": "my-web-server",
            "instance_type": "t2.micro"
        }
    
    ALLOWED INSTANCE TYPES:
        t2.nano, t2.micro, t2.small, t2.medium, t2.large
    
    RETURNS:
        200: Instance created successfully
        400: Invalid instance type
        500: AWS API error
    """
    # Validate instance type
    allowed_types = aws_service.get_available_instance_types()
    if request.instance_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid instance type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        result = aws_service.create_instance(
            name=request.name,
            instance_type=request.instance_type,
            user_id=current_user.id,
            user_email=current_user.email,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Start Instance
# =============================================================================
@router.post("/instances/{instance_id}/start", response_model=ActionResponse)
async def start_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Start a stopped EC2 instance.
    
    ACCESS CONTROL:
    - Admin/DevOps: Start any instance
    - User: Start only instances they created
    
    RETURNS:
        200: Instance starting
        403: Access denied (not your instance)
        500: AWS API error
    """
    # Check ownership for User role
    if current_user.role == "User":
        if not _check_instance_ownership(instance_id, current_user):
            raise HTTPException(
                status_code=403, 
                detail="You can only start instances you created"
            )
    
    try:
        return aws_service.start_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Stop Instance
# =============================================================================
@router.post("/instances/{instance_id}/stop", response_model=ActionResponse)
async def stop_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stop a running EC2 instance.
    
    ACCESS CONTROL:
    - Admin/DevOps: Stop any instance
    - User: Stop only instances they created
    
    RETURNS:
        200: Instance stopping
        403: Access denied (not your instance)
        500: AWS API error
    """
    # Check ownership for User role
    if current_user.role == "User":
        if not _check_instance_ownership(instance_id, current_user):
            raise HTTPException(
                status_code=403, 
                detail="You can only stop instances you created"
            )
    
    try:
        return aws_service.stop_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Reboot Instance
# =============================================================================
@router.post("/instances/{instance_id}/reboot", response_model=ActionResponse)
async def reboot_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Reboot an EC2 instance.
    
    ACCESS CONTROL:
    - Admin/DevOps: Reboot any instance
    - User: Reboot only instances they created
    
    RETURNS:
        200: Instance rebooting
        403: Access denied (not your instance)
        500: AWS API error
    """
    # Check ownership for User role
    if current_user.role == "User":
        if not _check_instance_ownership(instance_id, current_user):
            raise HTTPException(
                status_code=403, 
                detail="You can only reboot instances you created"
            )
    
    try:
        return aws_service.reboot_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Terminate Instance
# =============================================================================
@router.delete("/instances/{instance_id}", response_model=ActionResponse)
async def terminate_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Terminate (delete) an EC2 instance permanently.
    
    WARNING: This action is irreversible!
    
    ACCESS CONTROL:
    - Admin/DevOps: Terminate any instance
    - User: Terminate only instances they created
    
    RETURNS:
        200: Instance terminating
        403: Access denied (not your instance)
        500: AWS API error
    """
    # Check ownership for User role
    if current_user.role == "User":
        if not _check_instance_ownership(instance_id, current_user):
            raise HTTPException(
                status_code=403, 
                detail="You can only terminate instances you created"
            )
    
    try:
        return aws_service.terminate_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINT - Get Instance Types
# =============================================================================
@router.get("/instance-types")
async def get_instance_types(current_user: User = Depends(get_current_user)):
    """
    Get list of available EC2 instance types.
    
    RETURNS:
        200: {"instance_types": ["t2.nano", "t2.micro", ...]}
    """
    return {"instance_types": aws_service.get_available_instance_types()}


# =============================================================================
# CLOUDWATCH METRICS ENDPOINTS
# =============================================================================

@router.get("/instances/{instance_id}/metrics")
async def get_instance_metrics(
    instance_id: str,
    period: int = 60,
    current_user: User = Depends(get_current_user)
):
    """
    Get CloudWatch metrics history for an instance.
    
    QUERY PARAMS:
        period: Minutes of history to fetch (default: 60)
    
    RETURNS:
        {
            "instance_id": "i-xxx",
            "cpu_utilization": [...],
            "network_in": [...],
            "network_out": [...],
            "disk_read_ops": [...],
            "disk_write_ops": [...]
        }
    """
    try:
        return aws_service.get_instance_metrics(instance_id, period_minutes=period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/{instance_id}/metrics/current")
async def get_current_metrics(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get current (latest) metrics for an instance.
    
    Useful for dashboard quick stats.
    
    RETURNS:
        {
            "instance_id": "i-xxx",
            "cpu_percent": 15.5,
            "network_in_bytes": 1024,
            "network_out_bytes": 512
        }
    """
    try:
        return aws_service.get_instance_current_metrics(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COST EXPLORER ENDPOINTS
# =============================================================================

@router.get("/costs/daily")
async def get_daily_costs(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """
    Get daily cost breakdown for the last N days.
    
    QUERY PARAMS:
        days: Number of days to fetch (default: 7)
    
    RETURNS:
        [
            {"date": "2025-01-01", "compute": 1.5, "storage": 0.5, "network": 0.2, "total": 2.2},
            ...
        ]
    """
    try:
        return aws_service.get_daily_costs(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/summary")
async def get_cost_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Get current month cost summary with projection.
    
    RETURNS:
        {
            "month_to_date": 45.50,
            "projected_monthly": 120.00,
            "days_elapsed": 14
        }
    """
    try:
        return aws_service.get_monthly_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
