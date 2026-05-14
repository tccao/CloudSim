import pytest
from unittest.mock import patch

from app.models import User, Instance, Metric
from app.ec2_routes import (
    _filter_instances_for_user,
    _check_instance_ownership,
    sync_instances_to_db,
    persist_metrics_to_db,
)


# ---------------------------------------------------------------------------
# Shared test data builders
# ---------------------------------------------------------------------------

def _make_user(role: str, user_id: int = 1) -> User:
    """Build an unsaved User with just the fields these helpers care about."""
    u = User()
    u.id = user_id
    u.role = role
    return u


def _make_instance(instance_id: str, created_by_id: int | None = None) -> dict:
    """Build a minimal instance dict. Optionally tag it with a CreatedBy owner."""
    inst = {
        "instance_id": instance_id,
        "name": "test",
        "instance_type": "t2.micro",
        "state": "running",
        "public_ip": "1.2.3.4",
        "private_ip": "10.0.0.1",
        "availability_zone": "us-east-1a",
        "launch_time": "2024-01-01T00:00:00Z",
        "tags": [],
    }
    if created_by_id is not None:
        inst["tags"] = [{"Key": "CreatedBy", "Value": str(created_by_id)}]
    return inst


def _make_metrics(instance_id: str, timestamp: str = "2024-01-01T00:00:00Z") -> dict:
    """Build a minimal metrics payload with one CPU datapoint."""
    return {
        "instance_id": instance_id,
        "cpu_utilization": [{"timestamp": timestamp, "value": 45.5}],
        "network_in": [],
        "network_out": [],
        "disk_read_ops": [],
        "disk_write_ops": [],
    }


# =============================================================================
# UNIT: _filter_instances_for_user
# No DB, no HTTP. Pure dicts + User objects.
# =============================================================================

pytestmark = pytest.mark.unit


def test_filter_admin_sees_all_instances():
    admin = _make_user("Admin")
    instances = [_make_instance("i-001", 1), _make_instance("i-002", 2)]
    assert _filter_instances_for_user(instances, admin) == instances


def test_filter_devops_sees_all_instances():
    devops = _make_user("DevOps Engineer")
    instances = [_make_instance("i-001", 1), _make_instance("i-002", 2)]
    assert _filter_instances_for_user(instances, devops) == instances


def test_filter_user_sees_only_own_instances():
    user = _make_user("User", user_id=7)
    own = _make_instance("i-007", created_by_id=7)
    other = _make_instance("i-999", created_by_id=99)
    result = _filter_instances_for_user([own, other], user)
    assert result == [own]


def test_filter_user_excludes_instance_owned_by_other_user():
    user = _make_user("User", user_id=1)
    other = _make_instance("i-002", created_by_id=2)
    assert _filter_instances_for_user([other], user) == []


def test_filter_user_excludes_instance_with_no_tags():
    # An instance with no tags has no CreatedBy — User role cannot see it.
    user = _make_user("User", user_id=1)
    no_tags = _make_instance("i-notag")
    no_tags.pop("tags")  # remove the key entirely, not just empty it
    assert _filter_instances_for_user([no_tags], user) == []


def test_filter_user_instance_with_multiple_tags_finds_created_by():
    # CreatedBy is not always the first tag — the loop must scan all tags.
    user = _make_user("User", user_id=5)
    inst = _make_instance("i-multi")
    inst["tags"] = [
        {"Key": "Name", "Value": "web-server"},
        {"Key": "Env", "Value": "prod"},
        {"Key": "CreatedBy", "Value": "5"},
    ]
    assert _filter_instances_for_user([inst], user) == [inst]


def test_filter_empty_list_returns_empty():
    admin = _make_user("Admin")
    assert _filter_instances_for_user([], admin) == []


# =============================================================================
# UNIT: _check_instance_ownership
# Admin/DevOps short-circuit before any AWS call.
# User role requires patching aws_service.get_instance.
# =============================================================================

def test_ownership_admin_bypasses_aws_call():
    admin = _make_user("Admin")
    with patch("app.ec2_routes.aws_service.get_instance") as mock_get:
        result = _check_instance_ownership("i-123", admin)
    assert result is True
    mock_get.assert_not_called()


def test_ownership_devops_bypasses_aws_call():
    devops = _make_user("DevOps Engineer")
    with patch("app.ec2_routes.aws_service.get_instance") as mock_get:
        result = _check_instance_ownership("i-123", devops)
    assert result is True
    mock_get.assert_not_called()


def test_ownership_user_with_matching_tag_returns_true():
    user = _make_user("User", user_id=3)
    fake_instance = {"tags": [{"Key": "CreatedBy", "Value": "3"}]}
    with patch("app.ec2_routes.aws_service.get_instance", return_value=fake_instance):
        assert _check_instance_ownership("i-123", user) is True


def test_ownership_user_with_wrong_tag_returns_false():
    user = _make_user("User", user_id=3)
    fake_instance = {"tags": [{"Key": "CreatedBy", "Value": "99"}]}
    with patch("app.ec2_routes.aws_service.get_instance", return_value=fake_instance):
        assert _check_instance_ownership("i-123", user) is False


def test_ownership_user_instance_not_found_returns_false():
    user = _make_user("User", user_id=3)
    with patch("app.ec2_routes.aws_service.get_instance", return_value=None):
        assert _check_instance_ownership("i-missing", user) is False


# =============================================================================
# INTEGRATION: sync_instances_to_db
# Uses real SQLite session. Tests upsert behaviour and robustness.
# =============================================================================

@pytest.mark.integration
def test_sync_inserts_new_instance(db_session):
    sync_instances_to_db([_make_instance("i-new")], db_session)
    assert db_session.query(Instance).filter_by(instance_id="i-new").first() is not None


@pytest.mark.integration
def test_sync_inserts_multiple_instances(db_session):
    instances = [_make_instance(f"i-{n}") for n in range(3)]
    sync_instances_to_db(instances, db_session)
    assert db_session.query(Instance).count() == 3


@pytest.mark.integration
def test_sync_is_idempotent(db_session):
    # Calling sync twice with the same data must not create duplicate rows.
    inst = _make_instance("i-dupe")
    sync_instances_to_db([inst], db_session)
    sync_instances_to_db([inst], db_session)
    assert db_session.query(Instance).filter_by(instance_id="i-dupe").count() == 1


@pytest.mark.integration
def test_sync_updates_existing_instance(db_session):
    # First sync: state=running. Second sync: same instance, state=stopped.
    inst = _make_instance("i-update")
    inst["state"] = "running"
    sync_instances_to_db([inst], db_session)

    inst["state"] = "stopped"
    sync_instances_to_db([inst], db_session)

    row = db_session.query(Instance).filter_by(instance_id="i-update").first()
    assert row.state == "stopped"
    assert db_session.query(Instance).count() == 1  # still one row


@pytest.mark.integration
def test_sync_handles_invalid_launch_time(db_session):
    # Malformed launch_time must not crash the sync — store None instead.
    inst = _make_instance("i-badtime")
    inst["launch_time"] = "not-a-valid-datetime"
    sync_instances_to_db([inst], db_session)
    row = db_session.query(Instance).filter_by(instance_id="i-badtime").first()
    assert row is not None
    assert row.launch_time is None


# =============================================================================
# INTEGRATION: persist_metrics_to_db
# The idempotency test is the most important: same CloudWatch data called twice
# must produce the same row count both times (no duplicates).
# =============================================================================

@pytest.mark.integration
def test_persist_inserts_datapoints(db_session):
    persist_metrics_to_db("i-001", _make_metrics("i-001"), db_session)
    assert db_session.query(Metric).count() == 1


@pytest.mark.integration
def test_persist_is_idempotent(db_session):
    # This tests the already_exists guard in persist_metrics_to_db.
    # If the guard is removed, the second call doubles the row count.
    metrics = _make_metrics("i-001")
    persist_metrics_to_db("i-001", metrics, db_session)
    count_after_first = db_session.query(Metric).count()

    persist_metrics_to_db("i-001", metrics, db_session)
    count_after_second = db_session.query(Metric).count()

    assert count_after_first == count_after_second


@pytest.mark.integration
def test_persist_empty_metrics_inserts_nothing(db_session):
    empty = {
        "instance_id": "i-empty",
        "cpu_utilization": [],
        "network_in": [],
        "network_out": [],
        "disk_read_ops": [],
        "disk_write_ops": [],
    }
    persist_metrics_to_db("i-empty", empty, db_session)
    assert db_session.query(Metric).count() == 0


@pytest.mark.integration
def test_persist_multiple_metric_types(db_session):
    metrics = {
        "instance_id": "i-multi",
        "cpu_utilization": [{"timestamp": "2024-01-01T00:00:00Z", "value": 10.0}],
        "network_in":      [{"timestamp": "2024-01-01T00:00:00Z", "value": 1024.0}],
        "network_out":     [{"timestamp": "2024-01-01T00:00:00Z", "value": 512.0}],
        "disk_read_ops":   [],
        "disk_write_ops":  [],
    }
    persist_metrics_to_db("i-multi", metrics, db_session)
    # One row per metric type that has datapoints (cpu + net_in + net_out = 3)
    assert db_session.query(Metric).count() == 3
