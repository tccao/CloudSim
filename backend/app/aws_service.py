"""
AWS EC2 Service Layer for CloudSim.

Provides abstraction over Boto3 for EC2 operations.

CREDENTIAL CHAIN (in order of priority):
1. Explicit credentials in .env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
2. AWS profile in .env (AWS_PROFILE)
3. Default boto3 chain (~/.aws/credentials, IAM role, etc.)

ROLE-BASED ACCESS:
When ENABLE_ROLE_BASED_ACCESS=true, users get AWS clients with
permissions based on their CloudSim role (Admin, Developer, User, etc.)

DESIGN DECISIONS:
-----------------
1. Centralized config via config.py
2. Flexible credential handling for different environments
3. Returns typed dictionaries for consistency
4. Optional role-based access via STS AssumeRole
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional
import os

from .config import settings


def _get_boto3_session() -> boto3.Session:
    """
    Create a boto3 session based on configuration.
    
    Priority:
    1. Explicit credentials (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY)
    2. Named profile (AWS_PROFILE)
    3. Default credential chain
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
        # Use named profile
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        )
    else:
        # Use default credential chain
        return boto3.Session(region_name=settings.aws_region)


# Create session and default clients (used when role-based access is disabled)
_session = _get_boto3_session()
ec2 = _session.client("ec2")
ec2_resource = _session.resource("ec2")


def get_ec2_client_for_user(user_role: str, user_id: int):
    """
    Get EC2 client based on user role.
    
    If ENABLE_ROLE_BASED_ACCESS is true, returns a client with assumed role.
    Otherwise, returns the default shared client.
    
    Args:
        user_role: CloudSim user role (Admin, Developer, DevOps Engineer, User)
        user_id: User ID for session naming
        
    Returns:
        boto3 EC2 client
    """
    if settings.enable_role_based_access:
        from .aws_role_manager import get_aws_client_for_user
        role_client = get_aws_client_for_user('ec2', user_role, user_id)
        if role_client:
            return role_client
    
    # Fall back to default client
    return ec2


def get_cloudwatch_client_for_user(user_role: str, user_id: int):
    """Get CloudWatch client based on user role."""
    if settings.enable_role_based_access:
        from .aws_role_manager import get_aws_client_for_user
        role_client = get_aws_client_for_user('cloudwatch', user_role, user_id)
        if role_client:
            return role_client
    
    return cloudwatch


def get_cost_explorer_client_for_user(user_role: str, user_id: int):
    """Get Cost Explorer client based on user role."""
    if settings.enable_role_based_access:
        from .aws_role_manager import get_aws_client_for_user
        role_client = get_aws_client_for_user('ce', user_role, user_id)
        if role_client:
            return role_client
    
    return cost_explorer


def list_instances() -> list[dict]:
    """
    List all EC2 instances in the configured region.
    Returns simplified instance data.
    """
    try:
        response = ec2.describe_instances()
        instances = []
        
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                # Get instance name from tags
                name = ""
                for tag in instance.get("Tags", []):
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
                })
        
        return instances
    except ClientError as e:
        raise Exception(f"Failed to list instances: {e}")


def get_instance(instance_id: str) -> Optional[dict]:
    """Get detailed information for a specific instance."""
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                # Basic info
                name = ""
                tags = instance.get("Tags", [])
                for tag in tags:
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break
                
                # Fetch Volume Details
                block_devices = []
                volume_ids = [bd["Ebs"]["VolumeId"] for bd in instance.get("BlockDeviceMappings", []) if "Ebs" in bd]
                
                if volume_ids:
                    try:
                        vol_response = ec2.describe_volumes(VolumeIds=volume_ids)
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
                                "delete_on_termination": next((bd["Ebs"]["DeleteOnTermination"] for bd in instance.get("BlockDeviceMappings", []) if "Ebs" in bd and bd["Ebs"]["VolumeId"] == vol["VolumeId"]), False)
                            })
                    except ClientError:
                        pass # Ignore volume errors if permissions missing
                
                return {
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
                    "iam_role": instance.get("IamInstanceProfile", {}).get("Arn", "").split("/")[-1] if instance.get("IamInstanceProfile") else None
                }
        return None
    except ClientError as e:
        raise Exception(f"Failed to get instance {instance_id}: {e}")


def start_instance(instance_id: str) -> dict:
    """Start a stopped EC2 instance."""
    try:
        ec2.start_instances(InstanceIds=[instance_id])
        return {"message": f"Starting instance {instance_id}", "instance_id": instance_id}
    except ClientError as e:
        raise Exception(f"Failed to start instance: {e}")


def stop_instance(instance_id: str) -> dict:
    """Stop a running EC2 instance."""
    try:
        ec2.stop_instances(InstanceIds=[instance_id])
        return {"message": f"Stopping instance {instance_id}", "instance_id": instance_id}
    except ClientError as e:
        raise Exception(f"Failed to stop instance: {e}")


def reboot_instance(instance_id: str) -> dict:
    """Reboot an EC2 instance."""
    try:
        ec2.reboot_instances(InstanceIds=[instance_id])
        return {"message": f"Rebooting instance {instance_id}", "instance_id": instance_id}
    except ClientError as e:
        raise Exception(f"Failed to reboot instance: {e}")


def terminate_instance(instance_id: str) -> dict:
    """Terminate an EC2 instance."""
    try:
        ec2.terminate_instances(InstanceIds=[instance_id])
        return {"message": f"Terminating instance {instance_id}", "instance_id": instance_id}
    except ClientError as e:
        raise Exception(f"Failed to terminate instance: {e}")


def create_instance(
    name: str,
    instance_type: str = "t2.micro",
    image_id: str = None,
    user_id: int = None,
    user_email: str = None,
    subnet_id: str = None,
    security_group_ids: list = None,
) -> dict:
    """
    Create a new EC2 instance.
    
    Args:
        name: Name tag for the instance
        instance_type: EC2 instance type (default: t2.micro - free tier)
        image_id: AMI ID (defaults to Amazon Linux 2023 in us-east-1)
        user_id: CloudSim user ID for instance isolation
        user_email: CloudSim user email for auditing
        subnet_id: VPC subnet to launch in (defaults to cloudsim_subnet_id from config)
        security_group_ids: Security groups to attach (defaults to cloudsim_security_group_id from config)
    """
    # Default to Amazon Linux 2023 AMI in us-east-1
    if not image_id:
        # Get latest Amazon Linux 2023 AMI
        response = ec2.describe_images(
            Owners=["amazon"],
            Filters=[
                {"Name": "name", "Values": ["al2023-ami-*-x86_64"]},
                {"Name": "state", "Values": ["available"]},
            ],
        )
        images = sorted(response["Images"], key=lambda x: x["CreationDate"], reverse=True)
        if images:
            image_id = images[0]["ImageId"]
        else:
            raise Exception("No suitable AMI found")
    
    # Use CloudSim VPC settings if configured and not explicitly provided
    if not subnet_id and settings.cloudsim_subnet_id:
        subnet_id = settings.cloudsim_subnet_id
    
    if not security_group_ids and settings.cloudsim_security_group_id:
        security_group_ids = [settings.cloudsim_security_group_id]
    
    # Build tags - always include Name, optionally include creator info
    tags = [{"Key": "Name", "Value": name}]
    
    if user_id is not None:
        tags.append({"Key": "CreatedBy", "Value": str(user_id)})
    
    if user_email:
        tags.append({"Key": "CreatedByEmail", "Value": user_email})
    
    # Add CloudSim identifier
    tags.append({"Key": "ManagedBy", "Value": "CloudSim"})
    
    # Build instance launch parameters
    launch_params = {
        "ImageId": image_id,
        "InstanceType": instance_type,
        "MinCount": 1,
        "MaxCount": 1,
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": tags,
            }
        ],
    }
    
    # Add VPC settings if configured
    if subnet_id:
        launch_params["SubnetId"] = subnet_id
    
    if security_group_ids:
        launch_params["SecurityGroupIds"] = security_group_ids
    
    try:
        response = ec2_resource.create_instances(**launch_params)
        
        instance = response[0]
        return {
            "message": f"Created instance {instance.id}",
            "instance_id": instance.id,
            "name": name,
            "instance_type": instance_type,
            "subnet_id": subnet_id,
            "security_group_ids": security_group_ids,
        }
    except ClientError as e:
        raise Exception(f"Failed to create instance: {e}")


def get_available_instance_types() -> list[str]:
    """Return list of allowed instance types for CloudSim."""
    return [
        "t2.micro",    # Free tier
        "t2.small",
        "t2.medium",
        "t3.micro",
        "t3.small",
        "t3.medium",
    ]


# ============================================================================
# CLOUDWATCH METRICS
# ============================================================================
cloudwatch = _session.client("cloudwatch")


def get_instance_metrics(instance_id: str, period_minutes: int = 60) -> dict:
    """
    Get CloudWatch metrics for an EC2 instance.
    
    Args:
        instance_id: EC2 instance ID
        period_minutes: How far back to fetch metrics (default 60 min)
    
    Returns:
        Dict with cpu_utilization, network_in, network_out data points
    """
    from datetime import datetime, timedelta
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=period_minutes)
    
    def get_metric(metric_name: str, unit: str = "Percent") -> list:
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5-minute intervals
                Statistics=["Average"],
                Unit=unit,
            )
            # Sort by timestamp and return values
            datapoints = sorted(response.get("Datapoints", []), key=lambda x: x["Timestamp"])
            return [
                {
                    "timestamp": dp["Timestamp"].isoformat(),
                    "value": round(dp["Average"], 2),
                }
                for dp in datapoints
            ]
        except ClientError as e:
            print(f"Error fetching {metric_name}: {e}")
            return []
    
    return {
        "instance_id": instance_id,
        "cpu_utilization": get_metric("CPUUtilization", "Percent"),
        "network_in": get_metric("NetworkIn", "Bytes"),
        "network_out": get_metric("NetworkOut", "Bytes"),
        "disk_read_ops": get_metric("DiskReadOps", "Count"),
        "disk_write_ops": get_metric("DiskWriteOps", "Count"),
    }


def get_instance_current_metrics(instance_id: str) -> dict:
    """
    Get current (latest) metrics for an EC2 instance.
    Useful for dashboard overview.
    """
    metrics = get_instance_metrics(instance_id, period_minutes=15)
    
    def get_latest(data: list) -> float:
        return data[-1]["value"] if data else 0
    
    return {
        "instance_id": instance_id,
        "cpu_percent": get_latest(metrics["cpu_utilization"]),
        "network_in_bytes": get_latest(metrics["network_in"]),
        "network_out_bytes": get_latest(metrics["network_out"]),
    }


# ============================================================================
# COST EXPLORER
# ============================================================================
# Note: Cost Explorer is only available in us-east-1
cost_explorer = _session.client("ce", region_name="us-east-1")


def get_daily_costs(days: int = 7) -> list[dict]:
    """
    Get daily cost breakdown for the last N days.
    Returns list of {date, compute, storage, network, total}.
    """
    from datetime import datetime, timedelta
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    try:
        response = cost_explorer.get_cost_and_usage(
            TimePeriod={
                "Start": start_date.isoformat(),
                "End": end_date.isoformat(),
            },
            Granularity="DAILY",
            Metrics=["BlendedCost"],
            GroupBy=[
                {"Type": "DIMENSION", "Key": "SERVICE"}
            ],
        )
        
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
    except ClientError as e:
        print(f"Error fetching costs: {e}")
        return []


def get_monthly_summary() -> dict:
    """
    Get current month's cost summary.
    """
    from datetime import datetime
    
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    
    try:
        response = cost_explorer.get_cost_and_usage(
            TimePeriod={
                "Start": month_start.isoformat(),
                "End": today.isoformat(),
            },
            Granularity="MONTHLY",
            Metrics=["BlendedCost"],
        )
        
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
    except ClientError as e:
        print(f"Error fetching monthly costs: {e}")
        return {"month_to_date": 0, "projected_monthly": 0, "days_elapsed": 0}
