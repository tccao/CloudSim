import pytest

from app.models import Instance
from app.aws_service import AWSServiceError, AWSConfigurationError

pytestmark = pytest.mark.api


# ---------------------------------------------------------------------------
# Shared helper — builds an instance dict that satisfies InstanceResponse
# and carries a CreatedBy tag for ownership filtering tests.
# ---------------------------------------------------------------------------

def _mock_instance(instance_id: str, created_by_id: int) -> dict:
    return {
        "instance_id": instance_id,
        "name": "test-server",
        "instance_type": "t2.micro",
        "state": "running",
        "public_ip": "1.2.3.4",
        "private_ip": "10.0.0.1",
        "launch_time": "2024-01-01T00:00:00",
        "availability_zone": "us-east-1a",
        "tags": [{"Key": "CreatedBy", "Value": str(created_by_id)}],
    }


def _action_return(instance_id: str) -> dict:
    return {"message": "ok", "instance_id": instance_id}


# =============================================================================
# GET /api/ec2/instances
# =============================================================================

def test_list_instances_returns_200(client, admin_headers, mock_aws_service):
    r = client.get("/api/ec2/instances", headers=admin_headers)
    assert r.status_code == 200


def test_list_instances_unauthenticated_returns_401(client):
    assert client.get("/api/ec2/instances").status_code == 401


def test_list_instances_user_sees_only_own(client, regular_user, user_headers, mock_aws_service):
    # Most important RBAC test: two instances in AWS, user only owns one.
    own = _mock_instance("i-mine", created_by_id=regular_user.id)
    other = _mock_instance("i-other", created_by_id=999)
    mock_aws_service.list_instances.return_value = [own, other]

    r = client.get("/api/ec2/instances", headers=user_headers)

    assert r.status_code == 200
    ids = [i["instance_id"] for i in r.json()]
    assert "i-mine" in ids
    assert "i-other" not in ids


def test_list_instances_admin_sees_all(client, admin_headers, mock_aws_service):
    mock_aws_service.list_instances.return_value = [
        _mock_instance("i-001", 1),
        _mock_instance("i-002", 2),
    ]
    r = client.get("/api/ec2/instances", headers=admin_headers)
    assert len(r.json()) == 2


def test_list_instances_triggers_db_sync(client, admin_headers, db_session, mock_aws_service):
    # After the endpoint runs, Instance rows must appear in the test DB.
    # This verifies the sync_instances_to_db side effect at the API layer.
    mock_aws_service.list_instances.return_value = [_mock_instance("i-synced", 1)]

    client.get("/api/ec2/instances", headers=admin_headers)

    assert db_session.query(Instance).filter_by(instance_id="i-synced").first() is not None


# =============================================================================
# AWS error translation
# The _raise_http_for_aws_error helper maps exception types to status codes.
# =============================================================================

def test_list_instances_aws_service_error_returns_502(client, admin_headers, mock_aws_service):
    mock_aws_service.list_instances.side_effect = AWSServiceError("AWS unreachable")
    assert client.get("/api/ec2/instances", headers=admin_headers).status_code == 502


def test_list_instances_aws_config_error_returns_503(client, admin_headers, mock_aws_service):
    mock_aws_service.list_instances.side_effect = AWSConfigurationError("No credentials")
    assert client.get("/api/ec2/instances", headers=admin_headers).status_code == 503


# =============================================================================
# POST /api/ec2/instances  (create)
# =============================================================================

def test_create_instance_unauthenticated_returns_401(client):
    assert client.post("/api/ec2/instances", json={"name": "x"}).status_code == 401


def test_create_instance_invalid_type_returns_400(client, user_headers, mock_aws_service):
    # Validation fires before any AWS call — the type is not in allowed list.
    r = client.post("/api/ec2/instances", json={
        "name": "test",
        "instance_type": "t3.large",  # not in mock's allowed list
    }, headers=user_headers)
    assert r.status_code == 400
    mock_aws_service.create_instance.assert_not_called()


def test_create_instance_passes_frontend_launch_options(client, user_headers, regular_user, mock_aws_service):
    mock_aws_service.create_instance.return_value = _action_return("i-new")

    r = client.post("/api/ec2/instances", headers=user_headers, json={
        "name": "app-server",
        "instance_type": "t2.micro",
        "image_id": "ami-123",
        "subnet_id": "subnet-123",
        "security_group_ids": ["sg-123"],
        "volume_size": 12,
        "volume_type": "gp3",
        "assign_public_ip": True,
        "delete_on_termination": True,
    })

    assert r.status_code == 200
    mock_aws_service.create_instance.assert_called_once_with(
        name="app-server",
        instance_type="t2.micro",
        image_id="ami-123",
        user_id=regular_user.id,
        user_email=regular_user.email,
        subnet_id="subnet-123",
        security_group_ids=["sg-123"],
        volume_size=12,
        volume_type="gp3",
        assign_public_ip=True,
        delete_on_termination=True,
        user_role="User",
    )


# =============================================================================
# Instance actions: start / stop / reboot / terminate
#
# All four endpoints share identical ownership logic — a copy-paste bug in any
# one of them would be invisible without testing all four.
# Parametrize catches the whole set with one test function.
# =============================================================================

_ACTIONS = [
    ("post",   "/start",  "start_instance"),
    ("post",   "/stop",   "stop_instance"),
    ("post",   "/reboot", "reboot_instance"),
    ("delete", "",        "terminate_instance"),
]


@pytest.mark.parametrize("http_method,url_suffix,action_mock", _ACTIONS)
def test_action_user_cannot_act_on_unowned_instance(
    client, user_headers, mock_aws_service, http_method, url_suffix, action_mock
):
    # Ownership check fires before the AWS call — mock the get_instance lookup.
    mock_aws_service.get_instance.return_value = {
        "tags": [{"Key": "CreatedBy", "Value": "999"}]
    }
    r = getattr(client, http_method)(
        f"/api/ec2/instances/i-other{url_suffix}", headers=user_headers
    )
    assert r.status_code == 403
    getattr(mock_aws_service, action_mock).assert_not_called()


@pytest.mark.parametrize("http_method,url_suffix,action_mock", _ACTIONS)
def test_action_user_can_act_on_owned_instance(
    client, regular_user, user_headers, mock_aws_service, http_method, url_suffix, action_mock
):
    mock_aws_service.get_instance.return_value = {
        "tags": [{"Key": "CreatedBy", "Value": str(regular_user.id)}]
    }
    getattr(mock_aws_service, action_mock).return_value = _action_return("i-mine")

    r = getattr(client, http_method)(
        f"/api/ec2/instances/i-mine{url_suffix}", headers=user_headers
    )
    assert r.status_code == 200


@pytest.mark.parametrize("http_method,url_suffix,action_mock", _ACTIONS)
def test_action_admin_can_act_on_any_instance(
    client, admin_headers, mock_aws_service, http_method, url_suffix, action_mock
):
    # Admin bypasses the ownership check — no get_instance call needed.
    getattr(mock_aws_service, action_mock).return_value = _action_return("i-any")

    r = getattr(client, http_method)(
        f"/api/ec2/instances/i-any{url_suffix}", headers=admin_headers
    )
    assert r.status_code == 200
    mock_aws_service.get_instance.assert_not_called()


# =============================================================================
# GET /api/ec2/instance-types
# =============================================================================

def test_get_instance_types_returns_list(client, user_headers, mock_aws_service):
    r = client.get("/api/ec2/instance-types", headers=user_headers)
    assert r.status_code == 200
    assert "t2.micro" in r.json()["instance_types"]


# =============================================================================
# GET /api/ec2/instances/{id}/metrics
# =============================================================================

def test_user_can_get_metrics_for_owned_instance(client, user_headers, regular_user, mock_aws_service):
    mock_aws_service.get_instance.return_value = {
        "tags": [{"Key": "CreatedBy", "Value": str(regular_user.id)}],
    }
    r = client.get("/api/ec2/instances/i-owned/metrics", headers=user_headers)
    assert r.status_code == 200
    mock_aws_service.get_instance_metrics.assert_called_once_with(
        "i-owned",
        period_minutes=60,
        user_role="User",
        user_id=regular_user.id,
    )


def test_user_cannot_get_metrics_for_unowned_instance(client, user_headers, mock_aws_service):
    mock_aws_service.get_instance.return_value = {
        "tags": [{"Key": "CreatedBy", "Value": "999"}],
    }
    r = client.get("/api/ec2/instances/i-other/metrics", headers=user_headers)
    assert r.status_code == 403
    mock_aws_service.get_instance_metrics.assert_not_called()


# =============================================================================
# GET /api/ec2/costs/daily  and  /costs/summary
# =============================================================================

def test_user_costs_are_requested_with_ownership_context(client, user_headers, regular_user, mock_aws_service):
    r = client.get("/api/ec2/costs/daily?days=3", headers=user_headers)
    assert r.status_code == 200
    mock_aws_service.get_daily_costs.assert_called_once_with(
        3,
        user_role="User",
        user_id=regular_user.id,
    )


def test_cost_summary_unauthenticated_returns_401(client):
    assert client.get("/api/ec2/costs/summary").status_code == 401
