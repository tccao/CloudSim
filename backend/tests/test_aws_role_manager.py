# Unit tests for aws_role_manager.py.
#
# These tests cover role ARN lookup, role-based AWS client creation, singleton
# behavior, STS credential handling, and cached client refresh. They use mocks
# and monkeypatching only; no real AWS calls are made.
#
# Runtime flow under test: aws_service.get_*_client_for_user(...)
#   -> aws_role_manager.get_aws_client_for_user(...)
#   -> get_role_arn_for_user(...)
#   -> get_role_manager()
#   -> AWSRoleManager.get_cached_client(...)
#   -> get_service_client(...)
#   -> assume_role(...)
#   -> boto3.client(...)

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

# Import the module under test so we can patch its settings, singleton, and
# boto3 client in place.
from app import aws_role_manager

pytestmark = pytest.mark.unit


# Shared fake ARNs keep the expected role mappings easy to scan.
ADMIN_ARN = "arn:aws:iam::123456789012:role/CloudSimAdmin"
DEVOPS_ARN = "arn:aws:iam::123456789012:role/CloudSimDevOps"
USER_ARN = "arn:aws:iam::123456789012:role/CloudSimUser"


@pytest.fixture(autouse=True)
def reset_singleton():
    # The production module caches one manager globally, so each test starts
    # with a clean singleton and leaves no singleton behind.
    aws_role_manager._role_manager = None
    yield
    aws_role_manager._role_manager = None


@pytest.fixture
def enabled_roles(monkeypatch):
    # Opt in only the tests that need role-based access enabled.
    monkeypatch.setattr(aws_role_manager.settings, "enable_role_based_access", True)
    monkeypatch.setattr(aws_role_manager.settings, "aws_role_admin", ADMIN_ARN)
    monkeypatch.setattr(aws_role_manager.settings, "aws_role_devops", DEVOPS_ARN)
    monkeypatch.setattr(aws_role_manager.settings, "aws_role_readonly", USER_ARN)


def _client_error(code: str = "ExpiredToken") -> ClientError:
    # Use a real Botocore ClientError so exception handling matches boto3.
    return ClientError(
        {"Error": {"Code": code, "Message": "expired"}},
        "DescribeRegions",
    )


def _credentials():
    # Minimal STS credential shape returned by assume_role.
    return {
        "AccessKeyId": "AKIA_TEST",
        "SecretAccessKey": "secret",
        "SessionToken": "token",
        "Expiration": "soon",
    }


def _fake_sts_client(credentials=None):
    # Fake STS client whose assume_role response mirrors boto3's shape.
    sts_client = MagicMock(name="sts-client")
    sts_client.assume_role.return_value = {
        "Credentials": credentials or _credentials()
    }
    return sts_client


# Test 01: Disabled role-based access does not map CloudSim roles to IAM ARNs.
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
# Test 02: Each supported CloudSim role maps to its configured IAM role ARN.
def test_get_role_arn_maps_cloudsim_roles(enabled_roles, user_role, expected):
    assert aws_role_manager.get_role_arn_for_user(user_role) == expected


# Test 03: Unknown application roles are intentionally ignored.
def test_get_role_arn_unknown_role_returns_none(enabled_roles):
    assert aws_role_manager.get_role_arn_for_user("Billing") is None


# Test 04: Client factory returns None when role-based access is off.
def test_get_aws_client_for_user_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(aws_role_manager.settings, "enable_role_based_access", False)

    assert aws_role_manager.get_aws_client_for_user("ec2", "Admin", 1) is None


# Test 05: Client factory delegates enabled requests to the role manager cache.
def test_get_aws_client_for_user_uses_role_manager(enabled_roles, monkeypatch):
    fake_client = object()
    fake_manager = MagicMock()
    fake_manager.get_cached_client.return_value = fake_client

    monkeypatch.setattr(aws_role_manager, "get_role_manager", lambda: fake_manager)
    result = aws_role_manager.get_aws_client_for_user("ec2", "Admin", 42)

    assert result is fake_client
    fake_manager.get_cached_client.assert_called_once_with("ec2", ADMIN_ARN, "42")


# Test 06: get_role_manager creates one AWSRoleManager and reuses it.
def test_get_role_manager_returns_singleton(monkeypatch):
    fake_boto_client = MagicMock()
    monkeypatch.setattr(aws_role_manager.boto3, "client", lambda *args, **kwargs: fake_boto_client)

    first = aws_role_manager.get_role_manager()
    second = aws_role_manager.get_role_manager()

    assert first is second


# Test 07: AWSRoleManager builds its STS client in the configured AWS region.
def test_manager_initializes_sts_client_with_configured_region(monkeypatch):
    calls = []

    def fake_boto_client(*args, **kwargs):
        calls.append((args, kwargs))
        return MagicMock()

    monkeypatch.setattr(aws_role_manager.settings, "aws_region", "us-west-2")
    monkeypatch.setattr(aws_role_manager.boto3, "client", fake_boto_client)

    aws_role_manager.AWSRoleManager()

    assert calls == [(("sts",), {"region_name": "us-west-2"})]


# Test 08: assume_role returns Credentials and passes the STS args through.
def test_assume_role_returns_credentials(monkeypatch):
    credentials = _credentials()
    sts_client = _fake_sts_client(credentials)

    def fake_boto_client(service, **kwargs):
        assert service == "sts"
        return sts_client

    monkeypatch.setattr(aws_role_manager.boto3, "client", fake_boto_client)

    manager = aws_role_manager.AWSRoleManager()

    assert manager.assume_role(ADMIN_ARN, "cloudsim-1-ec2", duration=900) == credentials
    sts_client.assume_role.assert_called_once_with(
        RoleArn=ADMIN_ARN,
        RoleSessionName="cloudsim-1-ec2",
        DurationSeconds=900,
    )


# Test 09: assume_role preserves boto3 ClientError failures for callers.
def test_assume_role_reraises_client_error(monkeypatch):
    sts_client = MagicMock(name="sts-client")
    sts_client.assume_role.side_effect = _client_error("AccessDenied")

    def fake_boto_client(service, **kwargs):
        assert service == "sts"
        return sts_client

    monkeypatch.setattr(aws_role_manager.boto3, "client", fake_boto_client)

    manager = aws_role_manager.AWSRoleManager()

    with pytest.raises(ClientError):
        manager.assume_role(ADMIN_ARN, "cloudsim-denied")


# Test 10: Service clients are built from assumed-role temporary credentials.
def test_get_service_client_uses_assumed_credentials_and_configured_region(monkeypatch):
    created_clients = []
    sts_client = _fake_sts_client()

    def fake_boto_client(service, **kwargs):
        if service == "sts":
            return sts_client
        client = MagicMock(name=f"{service}-client")
        created_clients.append((service, kwargs, client))
        return client

    monkeypatch.setattr(aws_role_manager.settings, "aws_region", "us-west-2")
    monkeypatch.setattr(aws_role_manager.boto3, "client", fake_boto_client)

    manager = aws_role_manager.AWSRoleManager()

    result = manager.get_service_client("ec2", ADMIN_ARN, "cloudsim-1-ec2")

    service, kwargs, client = created_clients[-1]
    assert result is client
    assert service == "ec2"
    assert kwargs["aws_access_key_id"] == "AKIA_TEST"
    assert kwargs["aws_secret_access_key"] == "secret"
    assert kwargs["aws_session_token"] == "token"
    assert kwargs["region_name"] == "us-west-2"
    sts_client.assume_role.assert_called_once_with(
        RoleArn=ADMIN_ARN,
        RoleSessionName="cloudsim-1-ec2",
        DurationSeconds=3600,
    )


# Test 11: Cost Explorer clients always use AWS's us-east-1 endpoint region.
def test_get_service_client_uses_us_east_1_for_cost_explorer(monkeypatch):
    created_clients = []
    sts_client = _fake_sts_client()

    def fake_boto_client(service, **kwargs):
        if service == "sts":
            return sts_client
        client = MagicMock()
        created_clients.append((service, kwargs, client))
        return client

    monkeypatch.setattr(aws_role_manager.settings, "aws_region", "us-west-2")
    monkeypatch.setattr(aws_role_manager.boto3, "client", fake_boto_client)

    manager = aws_role_manager.AWSRoleManager()

    manager.get_service_client("ce", ADMIN_ARN, "cloudsim-1-ce")

    assert created_clients[-1][1]["region_name"] == "us-east-1"


# Test 12: A valid cached EC2 client is reused after a health check.
def test_get_cached_client_returns_valid_cached_ec2_client(monkeypatch):
    monkeypatch.setattr(aws_role_manager.boto3, "client", lambda *args, **kwargs: MagicMock())
    manager = aws_role_manager.AWSRoleManager()
    cached_client = MagicMock()
    manager._role_sessions[f"7:{ADMIN_ARN}:ec2"] = cached_client

    result = manager.get_cached_client("ec2", ADMIN_ARN, "7")

    assert result is cached_client
    cached_client.describe_regions.assert_called_once_with()


# Test 13: Expired cached EC2 clients are refreshed and stored back.
def test_get_cached_client_refreshes_expired_ec2_client(monkeypatch):
    monkeypatch.setattr(aws_role_manager.boto3, "client", lambda *args, **kwargs: MagicMock())
    manager = aws_role_manager.AWSRoleManager()
    expired_client = MagicMock()
    expired_client.describe_regions.side_effect = _client_error()
    fresh_client = MagicMock()
    manager._role_sessions[f"7:{ADMIN_ARN}:ec2"] = expired_client
    manager.get_service_client = MagicMock(return_value=fresh_client)

    result = manager.get_cached_client("ec2", ADMIN_ARN, "7")

    assert result is fresh_client
    manager.get_service_client.assert_called_once_with("ec2", ADMIN_ARN, "cloudsim-7-ec2")
    assert manager._role_sessions[f"7:{ADMIN_ARN}:ec2"] is fresh_client


# Test 14: Long STS session names are truncated to AWS's 64-character limit.
def test_get_cached_client_creates_client_with_truncated_session_name(monkeypatch):
    monkeypatch.setattr(aws_role_manager.boto3, "client", lambda *args, **kwargs: MagicMock())
    manager = aws_role_manager.AWSRoleManager()
    fresh_client = MagicMock()
    manager.get_service_client = MagicMock(return_value=fresh_client)
    long_user_id = "user-" + "x" * 100

    result = manager.get_cached_client("cloudwatch", USER_ARN, long_user_id)

    assert result is fresh_client
    session_name = manager.get_service_client.call_args.args[2]
    assert session_name.startswith("cloudsim-user-")
    assert len(session_name) == 64
