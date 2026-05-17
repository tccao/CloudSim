import pytest
from app.models import Metric
from app.aws_service import AWSServiceError

pytestmark = pytest.mark.api

# Timestamps must be ISO-8601 strings because persist_metrics_to_db calls
# datetime.fromisoformat() on each one.
_METRICS_WITH_DATA = {
    "instance_id": "i-test",
    "cpu_utilization": [{"timestamp": "2024-01-15T10:00:00Z", "value": 45.2}],
    "network_in":      [{"timestamp": "2024-01-15T10:00:00Z", "value": 1024.0}],
    "network_out":     [{"timestamp": "2024-01-15T10:00:00Z", "value": 512.0}],
    "disk_read_ops":   [{"timestamp": "2024-01-15T10:00:00Z", "value": 10.0}],
    "disk_write_ops":  [{"timestamp": "2024-01-15T10:00:00Z", "value": 5.0}],
}


# =============================================================================
# GET /api/ec2/instances/{id}/metrics
# =============================================================================

def test_metrics_unauthenticated_returns_401(client):
    # No instance is created for i-test here. Authentication runs before the
    # route performs ownership or AWS lookups, so any placeholder ID is enough.
    assert client.get("/api/ec2/instances/i-test/metrics").status_code == 401


def test_metrics_response_shape(client, admin_headers, mock_aws_service):
    # Guards the frontend contract: all five metric keys must be present.
    mock_aws_service.get_instance_metrics.return_value = _METRICS_WITH_DATA
    r = client.get("/api/ec2/instances/i-test/metrics", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    for key in ("instance_id", "cpu_utilization", "network_in", "network_out",
                "disk_read_ops", "disk_write_ops"):
        # The optional message after the comma is only shown if this assert fails,
        # which makes the missing response field obvious in pytest output.
        assert key in data, f"Response missing key: {key}"

def test_metrics_persists_to_database(client, admin_headers, db_session, mock_aws_service):
    # The DB write is invisible in the HTTP response — only a direct DB query reveals it.
    # The route receives i-persist-check from the URL, fetches metrics from the
    # mocked aws_service, then calls persist_metrics_to_db(instance_id, metrics, db).
    # That helper writes one Metric row per datapoint using the URL instance_id.
    mock_aws_service.get_instance_metrics.return_value = _METRICS_WITH_DATA
    client.get("/api/ec2/instances/i-persist-check/metrics", headers=admin_headers)
    assert db_session.query(Metric).filter_by(instance_id="i-persist-check").count() > 0


def test_metrics_all_five_types_persisted(client, admin_headers, db_session, mock_aws_service):
    mock_aws_service.get_instance_metrics.return_value = _METRICS_WITH_DATA
    client.get("/api/ec2/instances/i-five-types/metrics", headers=admin_headers)
    assert db_session.query(Metric).filter_by(instance_id="i-five-types").count() == 5


def test_metrics_idempotent_on_second_call(client, admin_headers, db_session, mock_aws_service):
    # Calling the endpoint twice with identical CloudWatch data must NOT create
    # duplicate rows — the already_exists guard in persist_metrics_to_db fires
    # on the second call.

    # The AWS call is mocked, but the DB session is real. The endpoint takes
    # this mocked return value and persists it through the real SQLAlchemy path,
    # so this verifies the route's side effect without touching CloudWatch.
    mock_aws_service.get_instance_metrics.return_value = _METRICS_WITH_DATA

    client.get("/api/ec2/instances/i-idem/metrics", headers=admin_headers)
    count_after_first = db_session.query(Metric).filter_by(instance_id="i-idem").count()

    client.get("/api/ec2/instances/i-idem/metrics", headers=admin_headers)
    count_after_second = db_session.query(Metric).filter_by(instance_id="i-idem").count()

    assert count_after_first == count_after_second


def test_metrics_empty_data_persists_nothing(client, admin_headers, db_session):
    # Default mock returns empty lists — no rows should be written.
    client.get("/api/ec2/instances/i-empty/metrics", headers=admin_headers)
    assert db_session.query(Metric).filter_by(instance_id="i-empty").count() == 0


def test_metrics_admin_bypasses_ownership_check(client, admin_headers, mock_aws_service):
    # Admin gets metrics without calling get_instance for the ownership lookup.
    r = client.get("/api/ec2/instances/i-anyones/metrics", headers=admin_headers)
    assert r.status_code == 200
    mock_aws_service.get_instance.assert_not_called()


def test_metrics_devops_bypasses_ownership_check(client, devops_headers, mock_aws_service):
    r = client.get("/api/ec2/instances/i-anyones/metrics", headers=devops_headers)
    assert r.status_code == 200
    mock_aws_service.get_instance.assert_not_called()

def test_metrics_custom_period_is_passed_through(client, admin_headers, mock_aws_service):
    # This is not covered by the response-shape tests. It verifies the endpoint
    # forwards ?period=30 as period_minutes=30 to the AWS service boundary.
    client.get("/api/ec2/instances/i-test/metrics?period=30", headers=admin_headers)
    call_kwargs = mock_aws_service.get_instance_metrics.call_args.kwargs
    assert call_kwargs["period_minutes"] == 30

def test_metrics_aws_error_returns_502(client, admin_headers, mock_aws_service):
    # AWSServiceError means the request reached CloudSim but the upstream AWS
    # dependency failed, so ec2_routes._raise_http_for_aws_error maps it to 502.
    mock_aws_service.get_instance_metrics.side_effect = AWSServiceError("CloudWatch down")
    assert client.get("/api/ec2/instances/i-test/metrics", headers=admin_headers).status_code == 502
