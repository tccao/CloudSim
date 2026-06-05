from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

Credentials = dict[str, Any]
ClientFactory = Callable[..., Any]


@runtime_checkable
class RoleProvider(Protocol):
    """Port for assuming AWS roles and building service clients."""

    def assume_role(
        self,
        role_arn: str,
        session_name: str,
        duration: int = 3600, # default 1 hour
    ) -> Credentials:
        """Return temporary credentials for the requested role."""

    def create_client(
        self,
        service: str,
        credentials: Mapping[str, Any],
        region_name: str,
    ) -> Any:
        """Create a service client from temporary credentials."""

    def validate_cached_client(self, service: str, client: Any) -> None:
        """Raise ClientError when a cached client is no longer usable."""


class AwsRoleProvider:
    """Real RoleProvider backed by boto3 STS and service clients."""

    def __init__(
        self,
        *,
        region_name: str,
        client_factory: ClientFactory = boto3.client,
    ) -> None:
        self.region_name = region_name
        self._client_factory = client_factory
        self._sts_client: Any | None = None

    def _get_sts_client(self) -> Any:
        if self._sts_client is None:
            self._sts_client = self._client_factory("sts", region_name=self.region_name)
        return self._sts_client

    def assume_role(
        self,
        role_arn: str,
        session_name: str,
        duration: int = 3600,
    ) -> Credentials:
        try:
            response = self._get_sts_client().assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                DurationSeconds=duration,
            )
            logger.info("Assumed role %s for session %s", role_arn, session_name)
            return dict(response["Credentials"])
        except ClientError as error:
            logger.error("Failed to assume role %s: %s", role_arn, error)
            raise

    def create_client(
        self,
        service: str,
        credentials: Mapping[str, Any],
        region_name: str,
    ) -> Any:
        return self._client_factory(
            service,
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
            region_name=region_name,
        )

    def validate_cached_client(self, service: str, client: Any) -> None:
        if service == "ec2":
            client.describe_regions()


class FakeAwsClient:
    """Tiny in-memory client used by FakeRoleProvider contract tests."""

    def __init__(
        self,
        *,
        service: str,
        credentials: Mapping[str, Any],
        region_name: str,
    ) -> None:
        self.service = service
        self.credentials = dict(credentials)
        self.region_name = region_name
        self.describe_regions_calls = 0
        self.expired = False

    def describe_regions(self) -> dict[str, list[dict[str, str]]]:
        self.describe_regions_calls += 1
        if self.expired:
            raise ClientError(
                {"Error": {"Code": "ExpiredToken", "Message": "expired"}},
                "DescribeRegions",
            )
        return {"Regions": [{"RegionName": self.region_name}]}

    def expire(self) -> None:
        self.expired = True


class FakeRoleProvider:
    """In-memory RoleProvider for deterministic, network-free tests."""

    def __init__(
        self,
        credentials_by_role_arn: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.credentials_by_role_arn: dict[str, Credentials] = {
            role_arn: dict(credentials)
            for role_arn, credentials in (credentials_by_role_arn or {}).items()
        }
        self.assume_role_calls: list[dict[str, Any]] = []
        self.create_client_calls: list[dict[str, Any]] = []
        self.created_clients: dict[tuple[str, str, str], FakeAwsClient] = {}

    @staticmethod
    def credentials_for(role_name: str) -> Credentials:
        return {
            "AccessKeyId": f"FAKE_ACCESS_KEY_{role_name}",
            "SecretAccessKey": f"fake-secret-{role_name}",
            "SessionToken": f"fake-token-{role_name}",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
        }

    def assume_role(
        self,
        role_arn: str,
        session_name: str,
        duration: int = 3600,
    ) -> Credentials:
        self.assume_role_calls.append(
            {
                "RoleArn": role_arn,
                "RoleSessionName": session_name,
                "DurationSeconds": duration,
            }
        )
        if role_arn not in self.credentials_by_role_arn:
            raise ClientError(
                {
                    "Error": {
                        "Code": "AccessDenied",
                        "Message": f"No fake credentials registered for {role_arn}",
                    }
                },
                "AssumeRole",
            )
        return dict(self.credentials_by_role_arn[role_arn])

    def create_client(
        self,
        service: str,
        credentials: Mapping[str, Any],
        region_name: str,
    ) -> FakeAwsClient:
        self.create_client_calls.append(
            {
                "service": service,
                "credentials": dict(credentials),
                "region_name": region_name,
            }
        )
        client = FakeAwsClient(
            service=service,
            credentials=credentials,
            region_name=region_name,
        )
        cache_key = (service, str(credentials["AccessKeyId"]), region_name)
        self.created_clients[cache_key] = client
        return client

    def validate_cached_client(self, service: str, client: Any) -> None:
        if service == "ec2":
            client.describe_regions()
