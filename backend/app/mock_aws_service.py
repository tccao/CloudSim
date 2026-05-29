from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import math
import uuid

from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Instance


MOCK_AMIS = [
    {
        "id": "ami-mock-al2023",
        "name": "Amazon Linux 2023 AMI",
        "description": "CloudSim mock Amazon Linux image",
        "architecture": "x86_64",
    },
    {
        "id": "ami-mock-ubuntu-2204",
        "name": "Ubuntu Server 22.04 LTS",
        "description": "CloudSim mock Ubuntu image",
        "architecture": "x86_64",
    },
    {
        "id": "ami-mock-windows-2022",
        "name": "Windows Server 2022 Base",
        "description": "CloudSim mock Windows image",
        "architecture": "x86_64",
    },
]

MOCK_VPCS = [{"id": "vpc-mock-default", "name": "cloudsim-demo-vpc", "is_default": True}]
MOCK_SUBNETS = [
    {
        "id": "subnet-mock-a",
        "name": "cloudsim-demo-public-a",
        "vpc_id": "vpc-mock-default",
        "availability_zone": f"{settings.aws_region}a",
        "default_for_az": True,
    },
    {
        "id": "subnet-mock-b",
        "name": "cloudsim-demo-public-b",
        "vpc_id": "vpc-mock-default",
        "availability_zone": f"{settings.aws_region}b",
        "default_for_az": True,
    },
]
MOCK_SECURITY_GROUPS = [
    {
        "id": "sg-mock-web",
        "name": "cloudsim-demo-web",
        "vpc_id": "vpc-mock-default",
        "description": "Mock web access security group",
    }
]

INSTANCE_TYPES = ["t2.nano", "t2.micro", "t2.small", "t2.medium", "t2.large"]
HOURLY_RATES = {
    "t2.nano": 0.0058,
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t2.medium": 0.0464,
    "t2.large": 0.0928,
}


@contextmanager
def _session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _new_instance_id() -> str:
    return f"i-{uuid.uuid4().hex[:17]}"


def _mock_public_ip(instance_id: str) -> str:
    octet = (int(instance_id[-2:], 16) % 250) + 1
    return f"203.0.113.{octet}"


def _mock_private_ip(instance_id: str, user_id: int | None) -> str:
    user_octet = (user_id or 10) % 250
    host_octet = (int(instance_id[-2:], 16) % 250) + 1
    return f"10.42.{user_octet}.{host_octet}"


def _tags_for_instance(instance: Instance) -> list[dict]:
    tags = [
        {"Key": "Name", "Value": instance.name or instance.instance_id},
        {"Key": "ManagedBy", "Value": "CloudSim"},
        {"Key": "Backend", "Value": "Mock"},
    ]
    if instance.created_by_user_id is not None:
        tags.append({"Key": "CreatedBy", "Value": str(instance.created_by_user_id)})
    return tags


def _summary(instance: Instance) -> dict:
    return {
        "instance_id": instance.instance_id,
        "name": instance.name or "",
        "instance_type": instance.instance_type,
        "state": instance.state,
        "public_ip": instance.public_ip,
        "private_ip": instance.private_ip,
        "launch_time": instance.launch_time.isoformat() if instance.launch_time else None,
        "availability_zone": instance.availability_zone or f"{settings.aws_region}a",
        "tags": _tags_for_instance(instance),
    }


def _detail(instance: Instance) -> dict:
    public_dns = None
    if instance.public_ip:
        public_dns = f"ec2-{instance.public_ip.replace('.', '-')}.compute.mock"

    return {
        **_summary(instance),
        "key_name": None,
        "platform": "Linux/UNIX",
        "tenancy": "default",
        "ami_id": MOCK_AMIS[0]["id"],
        "monitoring": "enabled",
        "public_dns": public_dns,
        "private_dns": f"ip-{(instance.private_ip or '10.42.0.1').replace('.', '-')}.mock",
        "vpc_id": MOCK_VPCS[0]["id"],
        "subnet_id": MOCK_SUBNETS[0]["id"],
        "security_groups": [
            {
                "GroupId": MOCK_SECURITY_GROUPS[0]["id"],
                "GroupName": MOCK_SECURITY_GROUPS[0]["name"],
            }
        ],
        "block_devices": [
            {
                "device_name": "/dev/xvda",
                "volume_id": f"vol-{instance.instance_id.replace('i-', '')[:12]}",
                "size": 8,
                "volume_type": "gp3",
                "iops": 3000,
                "throughput": 125,
                "encrypted": True,
                "delete_on_termination": True,
            }
        ],
        "iam_role": None,
    }


def _query_visible_instances(db: Session, user_role: str | None, user_id: int | None):
    query = db.query(Instance).filter(Instance.state != "terminated")
    if user_role == "User" and user_id is not None:
        query = query.filter(Instance.created_by_user_id == user_id)
    return query.order_by(Instance.launch_time.desc()).all()


def list_instances(user_role: str | None = None, user_id: int | None = None) -> list[dict]:
    with _session_scope() as db:
        return [_summary(instance) for instance in _query_visible_instances(db, user_role, user_id)]


def get_instance(
    instance_id: str,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict | None:
    with _session_scope() as db:
        instance = db.query(Instance).filter(Instance.instance_id == instance_id).first()
        if instance is None:
            return None
        return _detail(instance)


def create_instance(
    name: str,
    instance_type: str = "t2.micro",
    image_id: str | None = None,
    user_id: int | None = None,
    user_email: str | None = None,
    subnet_id: str | None = None,
    security_group_ids: list[str] | None = None,
    volume_size: int = 8,
    volume_type: str = "gp3",
    assign_public_ip: bool = True,
    delete_on_termination: bool = True,
    user_role: str | None = None,
) -> dict:
    instance_id = _new_instance_id()
    now = datetime.now(timezone.utc)

    with _session_scope() as db:
        instance = Instance(
            instance_id=instance_id,
            name=name,
            instance_type=instance_type,
            state="running",
            public_ip=_mock_public_ip(instance_id) if assign_public_ip else None,
            private_ip=_mock_private_ip(instance_id, user_id),
            availability_zone=MOCK_SUBNETS[0]["availability_zone"],
            launch_time=now,
            last_synced=now,
            created_by_user_id=user_id,
        )
        db.add(instance)

    return {
        "message": f"Created mock instance {instance_id}",
        "instance_id": instance_id,
        "name": name,
        "instance_type": instance_type,
        "image_id": image_id or MOCK_AMIS[0]["id"],
        "subnet_id": subnet_id or MOCK_SUBNETS[0]["id"],
        "security_group_ids": security_group_ids or [MOCK_SECURITY_GROUPS[0]["id"]],
        "volume_size": volume_size,
        "volume_type": volume_type,
    }


def _set_instance_state(instance_id: str, state: str, message: str) -> dict:
    with _session_scope() as db:
        instance = db.query(Instance).filter(Instance.instance_id == instance_id).first()
        if instance is None:
            from .aws_service import AWSServiceError

            raise AWSServiceError(f"Mock instance {instance_id} was not found")

        if instance.state == "terminated" and state != "terminated":
            from .aws_service import AWSServiceError

            raise AWSServiceError(f"Mock instance {instance_id} is terminated")

        instance.state = state
        instance.last_synced = datetime.now(timezone.utc)
        if state == "running" and instance.public_ip is None:
            instance.public_ip = _mock_public_ip(instance_id)
        if state in {"stopped", "terminated"}:
            instance.public_ip = None

    return {"message": f"{message} mock instance {instance_id}", "instance_id": instance_id}


def start_instance(
    instance_id: str,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    return _set_instance_state(instance_id, "running", "Starting")


def stop_instance(
    instance_id: str,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    return _set_instance_state(instance_id, "stopped", "Stopping")


def reboot_instance(
    instance_id: str,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    return _set_instance_state(instance_id, "running", "Rebooting")


def terminate_instance(
    instance_id: str,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    return _set_instance_state(instance_id, "terminated", "Terminating")


def get_available_instance_types() -> list[str]:
    return INSTANCE_TYPES.copy()


def get_launch_options(
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    return {
        "instance_types": get_available_instance_types(),
        "amis": MOCK_AMIS,
        "vpcs": MOCK_VPCS,
        "subnets": MOCK_SUBNETS,
        "security_groups": MOCK_SECURITY_GROUPS,
        "defaults": {
            "instance_type": "t2.micro",
            "ami_id": MOCK_AMIS[0]["id"],
            "vpc_id": MOCK_VPCS[0]["id"],
            "subnet_id": MOCK_SUBNETS[0]["id"],
            "security_group_id": MOCK_SECURITY_GROUPS[0]["id"],
            "volume_size": 8,
            "volume_type": "gp3",
            "assign_public_ip": True,
            "delete_on_termination": True,
        },
    }


def _metric_points(instance_id: str, period_minutes: int, running: bool, scale: float) -> list[dict]:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    interval = 5
    count = max(1, min(288, period_minutes // interval))
    seed = sum(ord(char) for char in instance_id)
    points = []

    for index in range(count):
        timestamp = now - timedelta(minutes=(count - index - 1) * interval)
        if running:
            wave = math.sin((seed + index) / 3)
            value = max(0.0, scale + (wave * scale * 0.35))
        else:
            value = 0.0
        points.append({"timestamp": timestamp.isoformat(), "value": round(value, 2)})

    return points


def get_instance_metrics(
    instance_id: str,
    period_minutes: int = 60,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    instance = get_instance(instance_id, user_role, user_id)
    running = instance is not None and instance["state"] == "running"

    return {
        "instance_id": instance_id,
        "cpu_utilization": _metric_points(instance_id, period_minutes, running, 35.0),
        "network_in": _metric_points(instance_id, period_minutes, running, 250000.0),
        "network_out": _metric_points(instance_id, period_minutes, running, 120000.0),
        "disk_read_ops": _metric_points(instance_id, period_minutes, running, 18.0),
        "disk_write_ops": _metric_points(instance_id, period_minutes, running, 9.0),
    }


def get_instance_current_metrics(
    instance_id: str,
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    metrics = get_instance_metrics(instance_id, 15, user_role, user_id)

    def latest(key: str) -> float:
        data = metrics[key]
        return data[-1]["value"] if data else 0.0

    return {
        "instance_id": instance_id,
        "cpu_percent": latest("cpu_utilization"),
        "network_in_bytes": latest("network_in"),
        "network_out_bytes": latest("network_out"),
    }


def _daily_total_for_instances(instances: list[Instance]) -> dict:
    compute = 0.0
    storage = 0.0
    network = 0.0

    for instance in instances:
        if instance.state == "terminated":
            continue
        if instance.state == "running":
            compute += HOURLY_RATES.get(instance.instance_type, HOURLY_RATES["t2.micro"]) * 24
            network += 0.03
        storage += (8 * 0.08) / 30

    total = compute + storage + network
    return {
        "compute": round(compute, 2),
        "storage": round(storage, 2),
        "network": round(network, 2),
        "total": round(total, 2),
    }


def get_daily_costs(
    days: int = 7,
    user_role: str | None = None,
    user_id: int | None = None,
) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    with _session_scope() as db:
        instances = _query_visible_instances(db, user_role, user_id)
        totals = _daily_total_for_instances(instances)

    return [
        {
            "date": (today - timedelta(days=days - index)).isoformat(),
            **totals,
        }
        for index in range(days)
    ]


def get_monthly_summary(
    user_role: str | None = None,
    user_id: int | None = None,
) -> dict:
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    days_elapsed = max((today - month_start).days, 1)
    daily = get_daily_costs(1, user_role, user_id)
    daily_total = daily[0]["total"] if daily else 0.0
    month_to_date = daily_total * days_elapsed

    return {
        "month_to_date": round(month_to_date, 2),
        "projected_monthly": round(daily_total * 30, 2),
        "days_elapsed": days_elapsed,
    }
