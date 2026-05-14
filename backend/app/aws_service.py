# =============================================================================
# aws_service.py - AWS Service Layer
# =============================================================================
# Abstraction layer over Boto3 for EC2, CloudWatch, and Cost Explorer operations.
#
# PROVIDES:
# - EC2 instance management (list, get, create, start, stop, reboot, terminate)
# - CloudWatch metrics retrieval
# - Cost Explorer data retrieval
#
# CREDENTIAL CHAIN (in priority order):
# 1. Explicit credentials in .env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# 2. AWS profile in .env (AWS_PROFILE)
# 3. Default boto3 chain (~/.aws/credentials, IAM role, etc.)
#
# ROLE-BASED ACCESS:
# When ENABLE_ROLE_BASED_ACCESS=true in .env, users get AWS clients with
# permissions based on their CloudSim role (Admin, DevOps Engineer, User).
#
# DESIGN DECISIONS:
# 1. Centralized config via config.py
# 2. Flexible credential handling for different environments
# 3. Returns typed dictionaries for consistency
# 4. Optional role-based access via STS AssumeRole
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
import boto3
from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
)
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import settings


class AWSServiceError(Exception):
    """Base exception for CloudSim AWS integration failures."""


class AWSConfigurationError(AWSServiceError):
    """Raised when AWS credentials or endpoint configuration are invalid."""


def _handle_aws_exception(context: str, error: Exception) -> None:
    """Normalize boto3 failures into user-friendly application exceptions."""
    if isinstance(error, (NoCredentialsError, PartialCredentialsError)):
        raise AWSConfigurationError(
            "AWS credentials are not configured. Set AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY, or provide root-credentials/credentials."
        ) from error

    if isinstance(error, EndpointConnectionError):
        raise AWSConfigurationError(
            f"Unable to reach AWS endpoints for region {settings.aws_region}. "
            "Check network access and AWS region settings."
        ) from error

    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code", "Unknown")
        if error_code in {"AuthFailure", "InvalidClientTokenId", "UnrecognizedClientException"}:
            raise AWSConfigurationError(
                "AWS credentials were rejected. Check the configured access key, "
                "secret key, and AWS region."
            ) from error
        if error_code in {"AccessDenied", "UnauthorizedOperation"}:
            raise AWSConfigurationError(
                "AWS credentials do not have permission for this operation."
            ) from error
        raise AWSServiceError(f"{context}: {error}") from error

    raise AWSServiceError(f"{context}: {error}") from error


# =============================================================================
# BOTO3 SESSION SETUP
# =============================================================================
def _get_boto3_session() -> boto3.Session:
    """
    Create a boto3 session based on configuration.
    
    Credential Priority:
    1. Explicit credentials (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)
    2. Named profile (AWS_PROFILE)
    3. Default credential chain (~/.aws/credentials, instance role, etc.)
    
    Returns:
        Configured boto3 Session
    """
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        # Use explicit credentials from .env
        return boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            region_name=settings.aws_region,
        )
    elif settings.aws_profile:
        # Use named profile from ~/.aws/credentials
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        )
    else:
        # Use default credential chain
        return boto3.Session(region_name=settings.aws_region)


# =============================================================================
# DEFAULT CLIENTS
# =============================================================================
# Create session and default clients (used when role-based access is disabled)
_session = _get_boto3_session()
ec2 = _session.client("ec2")


# =============================================================================
# ROLE-BASED CLIENT FACTORIES
# =============================================================================
def get_ec2_client_for_user(user_role: Optional[str] = None, user_id: Optional[int] = None):
    """
    Get EC2 client based on user role.
    
    If ENABLE_ROLE_BASED_ACCESS is true, returns a client with assumed role.
    Otherwise, returns the default shared client.
    
    Args:
        user_role: CloudSim user role (Admin, DevOps Engineer, User)
        user_id: User ID for session naming
        
    Returns:
        boto3 EC2 client
    """
    if settings.enable_role_based_access and user_role and user_id is not None:
        from .aws_role_manager import get_aws_client_for_user
        role_client = get_aws_client_for_user('ec2', user_role, user_id)
        if role_client:
            return role_client
    
    # Fall back to default client
    return ec2


def get_cloudwatch_client_for_user(user_role: Optional[str] = None, user_id: Optional[int] = None):
    """
    Get CloudWatch client based on user role.
    
    Args:
        user_role: CloudSim user role
        user_id: User ID for session naming
        
    Returns:
        boto3 CloudWatch client
    """
    if settings.enable_role_based_access and user_role and user_id is not None:
        from .aws_role_manager import get_aws_client_for_user
        role_client = get_aws_client_for_user('cloudwatch', user_role, user_id)
        if role_client:
            return role_client
    
    return cloudwatch


def get_cost_explorer_client_for_user(user_role: Optional[str] = None, user_id: Optional[int] = None):
    """
    Get Cost Explorer client based on user role.
    
    Args:
        user_role: CloudSim user role
        user_id: User ID for session naming
        
    Returns:
        boto3 Cost Explorer client
    """
    if settings.enable_role_based_access and user_role and user_id is not None:
        from .aws_role_manager import get_aws_client_for_user
        role_client = get_aws_client_for_user('ce', user_role, user_id)
        if role_client:
            return role_client
    
    return cost_explorer


# =============================================================================
# EC2 OPERATIONS - List Instances
# =============================================================================
def list_instances(user_role: Optional[str] = None, user_id: Optional[int] = None) -> list[dict]:
    """
    List all EC2 instances in the configured region.
    
    Includes tags for ownership filtering (CreatedBy tag).

    Args:
        user_role: CloudSim user role (optional, for role-based access)
        user_id: User ID (optional, for role-based access)
    
    Returns:
        List of instance dicts with:
        - instance_id, name, instance_type, state
        - public_ip, private_ip, launch_time, availability_zone
        - tags (for ownership filtering)
    
    Raises:
        Exception: If AWS API call fails
    """
    try:
        # Get client with appropriate permissions
        client = get_ec2_client_for_user(user_role, user_id)
        response = client.describe_instances()
        instances = []
        
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                # Get all tags
                tags = instance.get("Tags", [])
                
                # Extract name from tags
                name = ""
                for tag in tags:
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
                
                instances.append({
                    "instance_id": instance["InstanceId"],
                    "name": name,
                    "instance_type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    "availability_zone": instance["Placement"]["AvailabilityZone"],
                    "tags": tags,  # Include tags for ownership filtering
                })
        
        return instances
    except Exception as e:
        _handle_aws_exception("Failed to list instances", e)


# =============================================================================
# EC2 OPERATIONS - Get Instance Details
# =============================================================================
def get_instance(
    instance_id: str,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[dict]:
    """
    Get detailed information for a specific EC2 instance.
    
    Includes network, storage, and metadata details.
    
    Args:
        instance_id: EC2 instance ID (e.g., i-0abc123def456)
        
    Returns:
        Instance dict with full details, or None if not found
        
    Raises:
        Exception: If AWS API call fails
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)
        response = client.describe_instances(InstanceIds=[instance_id])
        
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                # Extract name from tags
                name = ""
                tags = instance.get("Tags", [])
                for tag in tags:
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
                
                # Fetch volume details
                block_devices = []
                volume_ids = [
                    bd["Ebs"]["VolumeId"] 
                    for bd in instance.get("BlockDeviceMappings", []) 
                    if "Ebs" in bd
                ]
                
                if volume_ids:
                    try:
                        vol_response = client.describe_volumes(VolumeIds=volume_ids)
                        for vol in vol_response.get("Volumes", []):
                            # Find matching device name
                            device_name = "N/A"
                            for bd in instance.get("BlockDeviceMappings", []):
                                if "Ebs" in bd and bd["Ebs"]["VolumeId"] == vol["VolumeId"]:
                                    device_name = bd["DeviceName"]
                                    break
                                    
                            block_devices.append({
                                "device_name": device_name,
                                "volume_id": vol["VolumeId"],
                                "size": vol["Size"],
                                "volume_type": vol["VolumeType"],
                                "iops": vol.get("Iops", 0),
                                "throughput": vol.get("Throughput", 0),
                                "encrypted": vol.get("Encrypted", False),
                                "delete_on_termination": next(
                                    (bd["Ebs"]["DeleteOnTermination"] 
                                     for bd in instance.get("BlockDeviceMappings", []) 
                                     if "Ebs" in bd and bd["Ebs"]["VolumeId"] == vol["VolumeId"]),
                                    False
                                )
                            })
                    except ClientError:
                        pass  # Ignore volume errors if permissions missing
                
                return {
                    # Basic info
                    "instance_id": instance["InstanceId"],
                    "name": name,
                    "instance_type": instance["InstanceType"],
                    "state": instance["State"]["Name"],
                    "key_name": instance.get("KeyName"),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    "availability_zone": instance["Placement"]["AvailabilityZone"],
                    "tenancy": instance["Placement"].get("Tenancy", "default"),
                    "platform": instance.get("PlatformDetails", instance.get("Platform", "Linux/UNIX")),
                    "ami_id": instance["ImageId"],
                    "monitoring": instance.get("Monitoring", {}).get("State", "disabled"),
                    
                    # Network
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "public_dns": instance.get("PublicDnsName"),
                    "private_dns": instance.get("PrivateDnsName"),
                    "vpc_id": instance.get("VpcId"),
                    "subnet_id": instance.get("SubnetId"),
                    "security_groups": instance.get("SecurityGroups", []),
                    
                    # Storage
                    "block_devices": block_devices,
                    
                    # Metadata
                    "tags": tags,
                    "iam_role": (
                        instance.get("IamInstanceProfile", {}).get("Arn", "").split("/")[-1] 
                        if instance.get("IamInstanceProfile") else None
                    )
                }
        
        return None
    except Exception as e:
        _handle_aws_exception(f"Failed to get instance {instance_id}", e)


# =============================================================================
# EC2 OPERATIONS - Instance Lifecycle
# =============================================================================
def start_instance(
    instance_id: str,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Start a stopped EC2 instance.
    
    Args:
        instance_id: EC2 instance ID
        
    Returns:
        Action response with message and instance_id
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)
        client.start_instances(InstanceIds=[instance_id])
        return {"message": f"Starting instance {instance_id}", "instance_id": instance_id}
    except Exception as e:
        _handle_aws_exception("Failed to start instance", e)


def stop_instance(
    instance_id: str,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Stop a running EC2 instance.
    
    Args:
        instance_id: EC2 instance ID
        
    Returns:
        Action response with message and instance_id
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)
        client.stop_instances(InstanceIds=[instance_id])
        return {"message": f"Stopping instance {instance_id}", "instance_id": instance_id}
    except Exception as e:
        _handle_aws_exception("Failed to stop instance", e)


def reboot_instance(
    instance_id: str,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Reboot an EC2 instance.
    
    Args:
        instance_id: EC2 instance ID
        
    Returns:
        Action response with message and instance_id
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)
        client.reboot_instances(InstanceIds=[instance_id])
        return {"message": f"Rebooting instance {instance_id}", "instance_id": instance_id}
    except Exception as e:
        _handle_aws_exception("Failed to reboot instance", e)


def terminate_instance(
    instance_id: str,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Terminate (permanently delete) an EC2 instance.
    
    WARNING: This action is irreversible!
    
    Args:
        instance_id: EC2 instance ID
        
    Returns:
        Action response with message and instance_id
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)
        client.terminate_instances(InstanceIds=[instance_id])
        return {"message": f"Terminating instance {instance_id}", "instance_id": instance_id}
    except Exception as e:
        _handle_aws_exception("Failed to terminate instance", e)


# =============================================================================
# EC2 OPERATIONS - Create Instance
# =============================================================================
def _tag_value(tags: list[dict], key: str, default: str = "") -> str:
    """Return a tag value from an AWS tag list."""
    for tag in tags:
        if tag.get("Key") == key:
            return tag.get("Value", default)
    return default


def _find_latest_image(client, owners: list[str], filters: list[dict]) -> Optional[dict]:
    """Find the newest available AMI matching the provided filters."""
    response = client.describe_images(Owners=owners, Filters=filters)
    images = sorted(response.get("Images", []), key=lambda x: x["CreationDate"], reverse=True)
    return images[0] if images else None


def _resolve_image(client, image_id: Optional[str]) -> tuple[str, str]:
    """Resolve the AMI ID and root device name used for block-device overrides."""
    if image_id:
        response = client.describe_images(ImageIds=[image_id])
        images = response.get("Images", [])
        if not images:
            raise AWSServiceError(f"AMI {image_id} was not found")
        image = images[0]
    else:
        image = _find_latest_image(
            client,
            owners=["amazon"],
            filters=[
                {"Name": "name", "Values": ["al2023-ami-*-x86_64"]},
                {"Name": "architecture", "Values": ["x86_64"]},
                {"Name": "root-device-type", "Values": ["ebs"]},
                {"Name": "state", "Values": ["available"]},
            ],
        )
        if not image:
            raise AWSServiceError("No suitable Amazon Linux 2023 AMI found")

    return image["ImageId"], image.get("RootDeviceName", "/dev/xvda")


def create_instance(
    name: str,
    instance_type: str = "t2.micro",
    image_id: Optional[str] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    subnet_id: Optional[str] = None,
    security_group_ids: Optional[list[str]] = None,
    volume_size: int = 8,
    volume_type: str = "gp3",
    assign_public_ip: bool = True,
    delete_on_termination: bool = True,
    user_role: Optional[str] = None,
) -> dict:
    """
    Create a new EC2 instance.
    
    Automatically tags instance with:
    - Name: The provided name
    - CreatedBy: User ID (for ownership tracking)
    - CreatedByEmail: User email (for auditing)
    - ManagedBy: "CloudSim"
    
    Args:
        name: Name tag for the instance
        instance_type: EC2 instance type (default: t2.micro - free tier)
        image_id: AMI ID (defaults to latest Amazon Linux 2023)
        user_id: CloudSim user ID for instance ownership
        user_email: CloudSim user email for auditing
        subnet_id: VPC subnet to launch in (defaults from config)
        security_group_ids: Security groups to attach (defaults from config)
        volume_size: Root EBS volume size in GiB
        volume_type: Root EBS volume type
        assign_public_ip: Whether to request a public IP on the primary ENI
        delete_on_termination: Whether the root volume is deleted on termination
        user_role: CloudSim user role for optional role-based AWS access
        
    Returns:
        Action response with instance_id and details
        
    Raises:
        Exception: If no suitable AMI found or AWS API fails
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)
        image_id, root_device_name = _resolve_image(client, image_id)

        # Use CloudSim VPC settings if configured and not overridden by the UI
        if not subnet_id and settings.cloudsim_subnet_id:
            subnet_id = settings.cloudsim_subnet_id

        if not security_group_ids and settings.cloudsim_security_group_id:
            security_group_ids = [settings.cloudsim_security_group_id]

        tags = [{"Key": "Name", "Value": name}]

        if user_id is not None:
            tags.append({"Key": "CreatedBy", "Value": str(user_id)})

        if user_email:
            tags.append({"Key": "CreatedByEmail", "Value": user_email})

        tags.append({"Key": "ManagedBy", "Value": "CloudSim"})

        launch_params = {
            "ImageId": image_id,
            "InstanceType": instance_type,
            "MinCount": 1,
            "MaxCount": 1,
            "BlockDeviceMappings": [
                {
                    "DeviceName": root_device_name,
                    "Ebs": {
                        "VolumeSize": volume_size,
                        "VolumeType": volume_type,
                        "DeleteOnTermination": delete_on_termination,
                    },
                }
            ],
            "TagSpecifications": [
                {"ResourceType": "instance", "Tags": tags},
                {"ResourceType": "volume", "Tags": tags},
            ],
        }

        if subnet_id:
            network_interface = {
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "AssociatePublicIpAddress": assign_public_ip,
            }
            if security_group_ids:
                network_interface["Groups"] = security_group_ids
            launch_params["NetworkInterfaces"] = [network_interface]
        elif security_group_ids:
            launch_params["SecurityGroupIds"] = security_group_ids

        response = client.run_instances(**launch_params)
        instance = response["Instances"][0]
        instance_id = instance["InstanceId"]

        return {
            "message": f"Created instance {instance_id}",
            "instance_id": instance_id,
            "name": name,
            "instance_type": instance_type,
            "image_id": image_id,
            "subnet_id": subnet_id,
            "security_group_ids": security_group_ids,
            "volume_size": volume_size,
            "volume_type": volume_type,
        }
    except Exception as e:
        _handle_aws_exception("Failed to create instance", e)


# =============================================================================
# EC2 OPERATIONS - Instance Types
# =============================================================================
def get_available_instance_types() -> list[str]:
    """
    Return list of allowed instance types for CloudSim.
    
    Limited to t2 family to control costs.
    
    Returns:
        List of allowed instance type strings
    """
    return [
        "t2.nano",     
        "t2.micro",    
        "t2.small",
        "t2.medium",
        "t2.large",
    ]


def get_launch_options(
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Return launch wizard options from AWS/config instead of hardcoded UI values.

    AMIs are resolved to the latest matching image in the configured region.
    Network options prefer CloudSim-specific config values when present.
    """
    try:
        client = get_ec2_client_for_user(user_role, user_id)

        ami_queries = [
            (
                "Amazon Linux 2023 AMI",
                ["amazon"],
                [
                    {"Name": "name", "Values": ["al2023-ami-*-x86_64"]},
                    {"Name": "architecture", "Values": ["x86_64"]},
                    {"Name": "root-device-type", "Values": ["ebs"]},
                    {"Name": "state", "Values": ["available"]},
                ],
            ),
            (
                "Ubuntu Server 22.04 LTS",
                ["099720109477"],
                [
                    {"Name": "name", "Values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]},
                    {"Name": "architecture", "Values": ["x86_64"]},
                    {"Name": "root-device-type", "Values": ["ebs"]},
                    {"Name": "state", "Values": ["available"]},
                ],
            ),
            (
                "Windows Server 2022 Base",
                ["amazon"],
                [
                    {"Name": "name", "Values": ["Windows_Server-2022-English-Full-Base-*"]},
                    {"Name": "root-device-type", "Values": ["ebs"]},
                    {"Name": "state", "Values": ["available"]},
                ],
            ),
        ]

        amis = []
        for name, owners, filters in ami_queries:
            image = _find_latest_image(client, owners, filters)
            if image:
                amis.append({
                    "id": image["ImageId"],
                    "name": name,
                    "description": image.get("Description") or image.get("Name", ""),
                    "architecture": image.get("Architecture", "x86_64"),
                })

        if settings.cloudsim_vpc_id:
            vpc_response = client.describe_vpcs(VpcIds=[settings.cloudsim_vpc_id])
        else:
            vpc_response = client.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])
            if not vpc_response.get("Vpcs"):
                vpc_response = client.describe_vpcs()

        vpcs = [
            {
                "id": vpc["VpcId"],
                "name": _tag_value(vpc.get("Tags", []), "Name", vpc["VpcId"]),
                "is_default": vpc.get("IsDefault", False),
            }
            for vpc in vpc_response.get("Vpcs", [])[:20]
        ]
        vpc_ids = [vpc["id"] for vpc in vpcs]

        if settings.cloudsim_subnet_id:
            subnet_response = client.describe_subnets(SubnetIds=[settings.cloudsim_subnet_id])
        elif vpc_ids:
            subnet_response = client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": vpc_ids}])
        else:
            subnet_response = {"Subnets": []}

        subnets = [
            {
                "id": subnet["SubnetId"],
                "name": _tag_value(subnet.get("Tags", []), "Name", subnet["SubnetId"]),
                "vpc_id": subnet["VpcId"],
                "availability_zone": subnet.get("AvailabilityZone", ""),
                "default_for_az": subnet.get("DefaultForAz", False),
            }
            for subnet in subnet_response.get("Subnets", [])[:50]
        ]

        if settings.cloudsim_security_group_id:
            sg_response = client.describe_security_groups(GroupIds=[settings.cloudsim_security_group_id])
        elif vpc_ids:
            sg_response = client.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": vpc_ids}])
        else:
            sg_response = {"SecurityGroups": []}

        security_groups = [
            {
                "id": sg["GroupId"],
                "name": sg.get("GroupName", sg["GroupId"]),
                "vpc_id": sg.get("VpcId"),
                "description": sg.get("Description", ""),
            }
            for sg in sg_response.get("SecurityGroups", [])[:50]
        ]

        return {
            "instance_types": get_available_instance_types(),
            "amis": amis,
            "vpcs": vpcs,
            "subnets": subnets,
            "security_groups": security_groups,
            "defaults": {
                "instance_type": "t2.micro",
                "ami_id": amis[0]["id"] if amis else None,
                "vpc_id": settings.cloudsim_vpc_id or (vpcs[0]["id"] if vpcs else None),
                "subnet_id": settings.cloudsim_subnet_id or (subnets[0]["id"] if subnets else None),
                "security_group_id": settings.cloudsim_security_group_id or (
                    security_groups[0]["id"] if security_groups else None
                ),
                "volume_size": 8,
                "volume_type": "gp3",
                "assign_public_ip": True,
                "delete_on_termination": True,
            },
        }
    except Exception as e:
        _handle_aws_exception("Failed to load launch options", e)


# =============================================================================
# CLOUDWATCH METRICS
# =============================================================================
cloudwatch = _session.client("cloudwatch")


def get_instance_metrics(
    instance_id: str,
    period_minutes: int = 60,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Get CloudWatch metrics history for an EC2 instance.
    
    Metrics retrieved:
    - CPUUtilization (%)
    - NetworkIn (bytes)
    - NetworkOut (bytes)
    - DiskReadOps (count)
    - DiskWriteOps (count)
    
    Args:
        instance_id: EC2 instance ID
        period_minutes: How far back to fetch (default: 60 min)
    
    Returns:
        Dict with metric arrays, each containing {timestamp, value} objects
    """
    client = get_cloudwatch_client_for_user(user_role, user_id)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=period_minutes)
    
    def get_metric(metric_name: str, unit: str = "Percent") -> list:
        """Fetch a single metric from CloudWatch."""
        try:
            response = client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5-minute intervals
                Statistics=["Average"],
                Unit=unit,
            )
            # Sort by timestamp and format
            datapoints = sorted(response.get("Datapoints", []), key=lambda x: x["Timestamp"])
            return [
                {
                    "timestamp": dp["Timestamp"].isoformat(),
                    "value": round(dp["Average"], 2),
                }
                for dp in datapoints
            ]
        except Exception as e:
            _handle_aws_exception(f"Failed to fetch metric {metric_name}", e)
    
    return {
        "instance_id": instance_id,
        "cpu_utilization": get_metric("CPUUtilization", "Percent"),
        "network_in": get_metric("NetworkIn", "Bytes"),
        "network_out": get_metric("NetworkOut", "Bytes"),
        "disk_read_ops": get_metric("DiskReadOps", "Count"),
        "disk_write_ops": get_metric("DiskWriteOps", "Count"),
    }


def get_instance_current_metrics(
    instance_id: str,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Get current (latest) metrics for an EC2 instance.
    
    Useful for dashboard quick stats. Fetches last 15 minutes of data
    and returns the most recent value for each metric.
    
    Args:
        instance_id: EC2 instance ID
        
    Returns:
        Dict with cpu_percent, network_in_bytes, network_out_bytes
    """
    metrics = get_instance_metrics(
        instance_id,
        period_minutes=15,
        user_role=user_role,
        user_id=user_id,
    )
    
    def get_latest(data: list) -> float:
        """Get the last value from a metric array."""
        return data[-1]["value"] if data else 0
    
    return {
        "instance_id": instance_id,
        "cpu_percent": get_latest(metrics["cpu_utilization"]),
        "network_in_bytes": get_latest(metrics["network_in"]),
        "network_out_bytes": get_latest(metrics["network_out"]),
    }


# =============================================================================
# COST EXPLORER
# =============================================================================
# Note: Cost Explorer API is only available in us-east-1
cost_explorer = _session.client("ce", region_name="us-east-1")


def _cost_filter_for_user(user_role: Optional[str], user_id: Optional[int]) -> Optional[dict]:
    """Return a Cost Explorer filter limiting regular users to their own tags."""
    if user_role == "User" and user_id is not None:
        return {
            "Tags": {
                "Key": "CreatedBy",
                "Values": [str(user_id)],
                "MatchOptions": ["EQUALS"],
            }
        }
    return None


def get_daily_costs(
    days: int = 7,
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> list[dict]:
    """
    Get daily cost breakdown for the last N days.
    
    Categorizes costs into:
    - Compute: EC2 instances
    - Storage: S3, EBS
    - Network: Data transfer, CloudFront
    
    Args:
        days: Number of days to fetch (default: 7)
        
    Returns:
        List of daily cost dicts: {date, compute, storage, network, total}
    """
    if not settings.enable_cost_explorer:
        raise AWSConfigurationError(
            "Cost Explorer integration is disabled. Set ENABLE_COST_EXPLORER=true to enable it."
        )

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)
    
    try:
        client = get_cost_explorer_client_for_user(user_role, user_id)
        request = {
            "TimePeriod": {
                "Start": start_date.isoformat(),
                "End": end_date.isoformat(),
            },
            "Granularity": "DAILY",
            "Metrics": ["BlendedCost"],
            "GroupBy": [
                {"Type": "DIMENSION", "Key": "SERVICE"}
            ],
        }
        cost_filter = _cost_filter_for_user(user_role, user_id)
        if cost_filter:
            request["Filter"] = cost_filter

        response = client.get_cost_and_usage(**request)
        
        daily_costs = []
        for result in response.get("ResultsByTime", []):
            date = result["TimePeriod"]["Start"]
            day_total = 0.0
            compute = 0.0
            storage = 0.0
            network = 0.0
            
            for group in result.get("Groups", []):
                service = group["Keys"][0]
                amount = float(group["Metrics"]["BlendedCost"]["Amount"])
                day_total += amount
                
                # Categorize by service
                if "EC2" in service:
                    compute += amount
                elif "S3" in service or "EBS" in service:
                    storage += amount
                elif "Data Transfer" in service or "CloudFront" in service:
                    network += amount
            
            daily_costs.append({
                "date": date,
                "compute": round(compute, 2),
                "storage": round(storage, 2),
                "network": round(network, 2),
                "total": round(day_total, 2),
            })
        
        return daily_costs
    except Exception as e:
        _handle_aws_exception("Failed to fetch daily costs", e)


def get_monthly_summary(
    user_role: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Get current month's cost summary with projection.
    
    Calculates:
    - month_to_date: Total spend so far this month
    - projected_monthly: Estimated end-of-month total
    - days_elapsed: Days since month start
    
    Returns:
        Cost summary dict
    """
    if not settings.enable_cost_explorer:
        raise AWSConfigurationError(
            "Cost Explorer integration is disabled. Set ENABLE_COST_EXPLORER=true to enable it."
        )

    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    
    try:
        client = get_cost_explorer_client_for_user(user_role, user_id)
        request = {
            "TimePeriod": {
                "Start": month_start.isoformat(),
                "End": today.isoformat(),
            },
            "Granularity": "MONTHLY",
            "Metrics": ["BlendedCost"],
        }
        cost_filter = _cost_filter_for_user(user_role, user_id)
        if cost_filter:
            request["Filter"] = cost_filter

        response = client.get_cost_and_usage(**request)
        
        total = 0.0
        for result in response.get("ResultsByTime", []):
            total = float(result["Total"]["BlendedCost"]["Amount"])
        
        # Calculate projected monthly cost
        days_elapsed = (today - month_start).days or 1
        days_in_month = 30  # Approximate
        projected = (total / days_elapsed) * days_in_month
        
        return {
            "month_to_date": round(total, 2),
            "projected_monthly": round(projected, 2),
            "days_elapsed": days_elapsed,
        }
    except Exception as e:
        _handle_aws_exception("Failed to fetch monthly cost summary", e)
