# Shared RoleProvider contract tests.
#
# Both the boto3-backed adapter and the in-memory fake must satisfy these
# expectations. The AwsRoleProvider case uses a local client factory, so this
# contract is still fully network-free.

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.role_providers import AwsRoleProvider, FakeAwsClient, FakeRoleProvider, RoleProvider


pytestmark = pytest.mark.unit


ADMIN_ARN = "arn:aws:iam::123456789012:role/CloudSimAdmin"
UNKNOWN_ARN = "arn:aws:iam::123456789012:role/Unknown"


@dataclass
class ProviderCase:
    name: str
    provider: RoleProvider
    credentials: dict[str, Any]


def _client_error(code: str, operation: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": code}},
        operation,
    )


def _describe_regions_call_count(client: Any) -> int:
    if isinstance(client, FakeAwsClient):
        return client.describe_regions_calls
    return client.describe_regions.call_count


def _expire_client(client: Any) -> None:
    if isinstance(client, FakeAwsClient):
        client.expire()
    else:
        client.describe_regions.side_effect = _client_error("ExpiredToken", "DescribeRegions")


@pytest.fixture(params=["aws", "fake"], ids=["aws-provider", "fake-provider"])
def provider_case(request) -> ProviderCase:
    credentials = FakeRoleProvider.credentials_for("contract")

    if request.param == "fake":
        return ProviderCase(
            name="fake",
            provider=FakeRoleProvider({ADMIN_ARN: credentials}),
            credentials=credentials,
        )

    sts_client = MagicMock(name="sts-client")

    def assume_role(**kwargs):
        if kwargs["RoleArn"] != ADMIN_ARN:
            raise _client_error("AccessDenied", "AssumeRole")
        return {"Credentials": credentials}

    sts_client.assume_role.side_effect = assume_role

    def client_factory(service: str, **kwargs):
        if service == "sts":
            return sts_client
        client = MagicMock(name=f"{service}-client")
        client.service = service
        client.credentials = {
            "AccessKeyId": kwargs["aws_access_key_id"],
            "SecretAccessKey": kwargs["aws_secret_access_key"],
            "SessionToken": kwargs["aws_session_token"],
            "Expiration": credentials["Expiration"],
        }
        client.region_name = kwargs["region_name"]
        return client

    return ProviderCase(
        name="aws",
        provider=AwsRoleProvider(region_name="us-west-2", client_factory=client_factory),
        credentials=credentials,
    )


def test_role_provider_contract_assumes_known_role(provider_case):
    result = provider_case.provider.assume_role(
        ADMIN_ARN,
        "cloudsim-1-ec2",
        duration=900,
    )

    assert result == provider_case.credentials


def test_role_provider_contract_rejects_unknown_role(provider_case, caplog):
    caplog.set_level("CRITICAL", logger="app.role_providers")

    with pytest.raises(ClientError):
        provider_case.provider.assume_role(UNKNOWN_ARN, "cloudsim-unknown")


def test_role_provider_contract_creates_service_client(provider_case):
    credentials = provider_case.provider.assume_role(ADMIN_ARN, "cloudsim-1-ec2")

    client = provider_case.provider.create_client("ec2", credentials, "us-west-2")

    assert client.service == "ec2"
    assert client.credentials == provider_case.credentials
    assert client.region_name == "us-west-2"


def test_role_provider_contract_validates_cached_ec2_client(provider_case):
    credentials = provider_case.provider.assume_role(ADMIN_ARN, "cloudsim-1-ec2")
    client = provider_case.provider.create_client("ec2", credentials, "us-west-2")

    provider_case.provider.validate_cached_client("ec2", client)

    assert _describe_regions_call_count(client) == 1


def test_role_provider_contract_surfaces_expired_cached_ec2_client(provider_case):
    credentials = provider_case.provider.assume_role(ADMIN_ARN, "cloudsim-1-ec2")
    client = provider_case.provider.create_client("ec2", credentials, "us-west-2")
    _expire_client(client)

    with pytest.raises(ClientError):
        provider_case.provider.validate_cached_client("ec2", client)
