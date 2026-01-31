"""
EC2 API routes for CloudSim.

Endpoints:
- GET /api/ec2/instances - List all EC2 instances
- GET /api/ec2/instances/{instance_id} - Get specific instance
- POST /api/ec2/instances - Create new instance
- POST /api/ec2/instances/{instance_id}/start - Start instance
- POST /api/ec2/instances/{instance_id}/stop - Stop instance
- DELETE /api/ec2/instances/{instance_id} - Terminate instance
- GET /api/ec2/instance-types - Get available instance types
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .auth import get_current_user
from .models import User, Instance
from .db import get_db
from . import aws_service

router = APIRouter(prefix="/api/ec2", tags=["EC2"])


# ============================================================================
# SCHEMAS
# ============================================================================
class Tag(BaseModel):
    Key: str
    Value: str


class SecurityGroup(BaseModel):
    GroupId: str
    GroupName: str


class BlockDevice(BaseModel):
    device_name: str
    volume_id: str
    size: int
    volume_type: str
    iops: Optional[int] = 0
    throughput: Optional[int] = 0
    encrypted: bool
    delete_on_termination: bool


class InstanceResponse(BaseModel):
    instance_id: str
    name: str
    instance_type: str
    state: str
    public_ip: Optional[str]
    private_ip: Optional[str]
    launch_time: Optional[str]
    availability_zone: str


class InstanceDetailResponse(InstanceResponse):
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
    name: str
    instance_type: str = "t2.micro"


class ActionResponse(BaseModel):
    message: str
    instance_id: str


# ============================================================================
# SYNC HELPER
# ============================================================================
def sync_instances_to_db(aws_instances: list, db: Session):
    """Sync AWS EC2 instances to local PostgreSQL database."""
    for inst in aws_instances:
        db_instance = db.query(Instance).filter(Instance.instance_id == inst["instance_id"]).first()
        launch_time = None
        if inst.get("launch_time"):
            try:
                launch_time = datetime.fromisoformat(inst["launch_time"].replace("Z", "+00:00"))
            except:
                pass
        
        if db_instance:
            # Update existing
            db_instance.name = inst.get("name", "")
            db_instance.instance_type = inst["instance_type"]
            db_instance.state = inst["state"]
            db_instance.public_ip = inst.get("public_ip")
            db_instance.private_ip = inst.get("private_ip")
            db_instance.availability_zone = inst.get("availability_zone", "")
            db_instance.launch_time = launch_time
            db_instance.last_synced = datetime.utcnow()
        else:
            # Create new
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


# ============================================================================
# HELPER: Filter instances by user ownership
# ============================================================================
def _filter_instances_for_user(instances: list, user: User) -> list:
    """
    Filter instances based on user role.
    - Admin/DevOps: See all instances
    - User: See only instances they created (CreatedBy tag matches user ID)
    """
    if user.role in ["Admin", "DevOps Engineer"]:
        return instances
    
    # For User role, filter by CreatedBy tag
    filtered = []
    for inst in instances:
        # Check if instance was created by this user
        created_by = None
        # list_instances returns flat dict, get_instance returns nested tags
        if "tags" in inst:
            for tag in inst.get("tags", []):
                if tag.get("Key") == "CreatedBy":
                    created_by = tag.get("Value")
                    break
        
        if created_by == str(user.id):
            filtered.append(inst)
    
    return filtered


# ============================================================================
# ENDPOINTS
# ============================================================================
@router.get("/instances", response_model=list[InstanceResponse])
async def list_instances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List EC2 instances.
    - Admin/DevOps: See all instances
    - User: See only instances they created
    """
    try:
        instances = aws_service.list_instances()
        sync_instances_to_db(instances, db)
        
        # Filter based on user role
        filtered_instances = _filter_instances_for_user(instances, current_user)
        return filtered_instances
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instances/{instance_id}", response_model=InstanceDetailResponse)
async def get_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific EC2 instance.
    Users can only view instances they created.
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
                raise HTTPException(status_code=403, detail="You can only view instances you created")
        
        return instance
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances", response_model=ActionResponse)
async def create_instance(
    request: CreateInstanceRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new EC2 instance. Requires DevOps or Admin role."""
    # Check role
    if current_user.role not in ["Admin", "DevOps Engineer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions to create instances")
    
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

def _check_instance_ownership(instance_id: str, user: User) -> bool:
    """
    Check if user owns the instance (by CreatedBy tag).
    Admins and DevOps can access any instance.
    """
    if user.role in ["Admin", "DevOps Engineer"]:
        return True
    
    # For User role, check ownership
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


@router.post("/instances/{instance_id}/start", response_model=ActionResponse)
async def start_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Start a stopped EC2 instance. Users can only start their own instances."""
    # Check ownership for User role
    if current_user.role == "User":
        if not _check_instance_ownership(instance_id, current_user):
            raise HTTPException(status_code=403, detail="You can only start instances you created")
    
    try:
        return aws_service.start_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/{instance_id}/stop", response_model=ActionResponse)
async def stop_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop a running EC2 instance. Users can only stop their own instances."""
    # Check ownership for User role
    if current_user.role == "User":
        if not _check_instance_ownership(instance_id, current_user):
            raise HTTPException(status_code=403, detail="You can only stop instances you created")
    
    try:
        return aws_service.stop_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instances/{instance_id}/reboot", response_model=ActionResponse)
async def reboot_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Reboot an EC2 instance."""
    try:
        return aws_service.reboot_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/instances/{instance_id}", response_model=ActionResponse)
async def terminate_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user)
):
    """Terminate an EC2 instance. Requires Admin role."""
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required to terminate instances")
    
    try:
        return aws_service.terminate_instance(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instance-types")
async def get_instance_types(current_user: User = Depends(get_current_user)):
    """Get available instance types."""
    return {"instance_types": aws_service.get_available_instance_types()}


# ============================================================================
# CLOUDWATCH METRICS ENDPOINTS
# ============================================================================
@router.get("/instances/{instance_id}/metrics")
async def get_instance_metrics(
    instance_id: str,
    period: int = 60,
    current_user: User = Depends(get_current_user)
):
    """
    Get CloudWatch metrics for an instance.
    
    Args:
        instance_id: EC2 instance ID
        period: Minutes of history to fetch (default 60)
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
    """Get current (latest) metrics for an instance."""
    try:
        return aws_service.get_instance_current_metrics(instance_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COST EXPLORER ENDPOINTS
# ============================================================================
@router.get("/costs/daily")
async def get_daily_costs(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get daily cost breakdown for the last N days."""
    try:
        return aws_service.get_daily_costs(days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs/summary")
async def get_cost_summary(
    current_user: User = Depends(get_current_user)
):
    """Get current month cost summary with projection."""
    try:
        return aws_service.get_monthly_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


