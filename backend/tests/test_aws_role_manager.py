# Unit tests for aws_role_manager.py.
#
# These tests exercise role mapping, provider injection, session naming, and
# client caching without patching boto3 or touching the network.

import pytest
from botocore.exceptions import ClientError

from app import aws_role_manager
from app.role_providers import FakeAwsClient, FakeRoleProvider


pytestmark = pytest.mark.unit


ADMIN_ARN = "arn:aws:iam::123456789012:role/CloudSimAdmin"
DEVOPS_ARN = "arn:aws:iam::123456789012:role/CloudSimDevOps"
USER_ARN = "arn:aws:iam::123456789012:role/CloudSimUser"


@pytest.fixture(autouse=True)
def reset_role_manager():
    old_manager = aws_role_manager._role_manager
    old_provider = aws_role_manager._role_provider
    aws_role_manager._role_manager = None
    aws_role_manager._role_provider = None
    yield
    aws_role_manager._role_manager = old_manager
    aws_role_manager._role_provider = old_provider


@pytest.fixture
def enabled_roles(monkeypatch):
    monkeypatch.setattr(aws_role_manager.settings, "enable_role_based_access", True)
    monkeypatch.setattr(aws_role_manager.settings, "aws_role_admin", ADMIN_ARN)
    monkeypatch.setattr(aws_role_manager.settings, "aws_role_devops", DEVOPS_ARN)
    monkeypatch.setattr(aws_role_manager.settings, "aws_role_readonly", USER_ARN)


def _credentials(name: str = "admin"):
    return FakeRoleProvider.credentials_for(name)


def _provider_for_admin(credentials=None) -> FakeRoleProvider:
    return FakeRoleProvider({ADMIN_ARN: credentials or _credentials()})


def test_get_role_arn_returns_none_when_role_based_access_disabled(monkeypatch):
    monkeypatch.setattr(aws_role_manager.settings, "enable_role_based_access", False)

    assert aws_role_manager.get_role_arn_for_user("Admin") is None


@pytest.mark.parametrize(
    "user_role,expected",
    [
        ("Admin", ADMIN_ARN),
        ("DevOps Engineer", DEVOPS_ARN),
        ("User", USER_ARN),
    ],
)
def test_get_role_arn_maps_cloudsim_roles(enabled_roles, user_role, expected):
    assert aws_role_manager.get_role_arn_for_user(user_role) == expected


def test_get_role_arn_unknown_role_returns_none(enabled_roles):
    assert aws_role_manager.get_role_arn_for_user("Billing") is None


def test_get_aws_client_for_user_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(aws_role_manager.settings, "enable_role_based_access", False)

    assert aws_role_manager.get_aws_client_for_user("ec2", "Admin", 1) is None


def test_get_role_manager_requires_configured_provider():
    with pytest.raises(RuntimeError, match="role provider"):
        aws_role_manager.get_role_manager()


def test_configure_role_manager_creates_singleton():
    provider = _provider_for_admin()

    aws_role_manager.configure_role_manager(provider, "us-west-2")

    first = aws_role_manager.get_role_manager()
    second = aws_role_manager.get_role_manager()

    assert first is second
    assert first.role_provider is provider
    assert first.aws_region == "us-west-2"


def test_get_aws_client_for_user_uses_fake_provider_with_no_network(enabled_roles):
    credentials = _credentials()
    provider = _provider_for_admin(credentials)
    aws_role_manager.configure_role_manager(provider, "us-west-2")

    result = aws_role_manager.get_aws_client_for_user("ec2", "Admin", 42)

    assert isinstance(result, FakeAwsClient)
    assert result.service == "ec2"
    assert result.credentials == credentials
    assert result.region_name == "us-west-2"
    assert provider.assume_role_calls == [
        {
            "RoleArn": ADMIN_ARN,
            "RoleSessionName": "cloudsim-42-ec2",
            "DurationSeconds": 3600,
        }
    ]


def test_assume_role_delegates_to_provider():
    credentials = _credentials()
    provider = _provider_for_admin(credentials)
    manager = aws_role_manager.AWSRoleManager(provider, "us-west-2")

    assert manager.assume_role(ADMIN_ARN, "cloudsim-1-ec2", duration=900) == credentials
    assert provider.assume_role_calls == [
        {
            "RoleArn": ADMIN_ARN,
            "RoleSessionName": "cloudsim-1-ec2",
            "DurationSeconds": 900,
        }
    ]


def test_assume_role_reraises_provider_client_error():
    manager = aws_role_manager.AWSRoleManager(FakeRoleProvider(), "us-west-2")

    with pytest.raises(ClientError):
        manager.assume_role(ADMIN_ARN, "cloudsim-denied")


def test_get_service_client_uses_assumed_credentials_and_configured_region():
    credentials = _credentials()
    provider = _provider_for_admin(credentials)
    manager = aws_role_manager.AWSRoleManager(provider, "us-west-2")

    result = manager.get_service_client("ec2", ADMIN_ARN, "cloudsim-1-ec2")

    assert result.service == "ec2"
    assert result.credentials == credentials
    assert result.region_name == "us-west-2"
    assert provider.create_client_calls == [
        {
            "service": "ec2",
            "credentials": credentials,
            "region_name": "us-west-2",
        }
    ]


def test_get_service_client_uses_us_east_1_for_cost_explorer():
    provider = _provider_for_admin()
    manager = aws_role_manager.AWSRoleManager(provider, "us-west-2")

    result = manager.get_service_client("ce", ADMIN_ARN, "cloudsim-1-ce")

    assert result.service == "ce"
    assert result.region_name == "us-east-1"


def test_get_cached_client_returns_valid_cached_ec2_client():
    provider = _provider_for_admin()
    manager = aws_role_manager.AWSRoleManager(provider, "us-west-2")
    cached_client = FakeAwsClient(
        service="ec2",
        credentials=_credentials(),
        region_name="us-west-2",
    )
    manager._role_sessions[f"7:{ADMIN_ARN}:ec2"] = cached_client

    result = manager.get_cached_client("ec2", ADMIN_ARN, "7")

    assert result is cached_client
    assert cached_client.describe_regions_calls == 1


def test_get_cached_client_refreshes_expired_ec2_client():
    provider = _provider_for_admin()
    manager = aws_role_manager.AWSRoleManager(provider, "us-west-2")
    expired_client = FakeAwsClient(
        service="ec2",
        credentials=_credentials("expired"),
        region_name="us-west-2",
    )
    expired_client.expire()
    manager._role_sessions[f"7:{ADMIN_ARN}:ec2"] = expired_client

    result = manager.get_cached_client("ec2", ADMIN_ARN, "7")

    assert result is not expired_client
    assert result is manager._role_sessions[f"7:{ADMIN_ARN}:ec2"]
    assert provider.assume_role_calls[-1]["RoleSessionName"] == "cloudsim-7-ec2"


def test_get_cached_client_creates_client_with_truncated_session_name():
    provider = _provider_for_admin()
    manager = aws_role_manager.AWSRoleManager(provider, "us-west-2")
    long_user_id = "user-" + "x" * 100

    result = manager.get_cached_client("cloudwatch", ADMIN_ARN, long_user_id)

    assert result.service == "cloudwatch"
    session_name = provider.assume_role_calls[-1]["RoleSessionName"]
    assert session_name.startswith("cloudsim-user-")
    assert len(session_name) == 64
