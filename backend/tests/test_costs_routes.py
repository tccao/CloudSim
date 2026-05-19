import pytest
from datetime import datetime, timezone

from app import aws_service as real_aws_service
from app.aws_service import AWSServiceError

pytestmark = pytest.mark.api


# =============================================================================
# GET /api/ec2/costs/daily
# =============================================================================

@pytest.mark.parametrize("headers_fixture", ["admin_headers", "devops_headers", "user_headers"])
def test_daily_costs_all_roles_return_200(request, client, headers_fixture, mock_aws_service):
    # Cost endpoints are auth-required but not RBAC-gated — all roles must succeed.
    headers = request.getfixturevalue(headers_fixture)
    assert client.get("/api/ec2/costs/daily", headers=headers).status_code == 200


def test_daily_costs_unauthenticated_returns_401(client):
    assert client.get("/api/ec2/costs/daily").status_code == 401

def test_daily_costs_response_is_list(client, admin_headers, mock_aws_service):
    # The route returns aws_service.get_daily_costs(...) directly. The fixture's
    # default mocked value is [], so the API contract should still be a JSON list.
    r = client.get("/api/ec2/costs/daily", headers=admin_headers)
    assert isinstance(r.json(), list)


def test_daily_costs_default_days_is_7(client, admin_headers, mock_aws_service):
    # When ?days= is omitted, aws_service must be called with days=7.
    client.get("/api/ec2/costs/daily", headers=admin_headers)
    # get_daily_costs is called as:
    #   get_daily_costs(days, user_role=current_user.role, user_id=current_user.id)
    # call_args.args[0] is the positional days argument.
    assert mock_aws_service.get_daily_costs.call_args.args[0] == 7


def test_daily_costs_custom_days_forwarded(client, admin_headers, mock_aws_service):
    client.get("/api/ec2/costs/daily?days=14", headers=admin_headers)
    assert mock_aws_service.get_daily_costs.call_args.args[0] == 14


def test_daily_costs_aws_error_returns_502(client, admin_headers, mock_aws_service):
    # side_effect tells the MagicMock to raise this exception when the route
    # calls get_daily_costs. AWSServiceError is translated to HTTP 502 because
    # Cost Explorer is an upstream dependency that failed.
    mock_aws_service.get_daily_costs.side_effect = AWSServiceError("CE unavailable")
    assert client.get("/api/ec2/costs/daily", headers=admin_headers).status_code == 502


# =============================================================================
# GET /api/ec2/costs/summary
# =============================================================================

@pytest.mark.parametrize("headers_fixture", ["admin_headers", "devops_headers", "user_headers"])
def test_cost_summary_all_roles_return_200(request, client, headers_fixture, mock_aws_service):
    headers = request.getfixturevalue(headers_fixture)
    assert client.get("/api/ec2/costs/summary", headers=headers).status_code == 200


def test_cost_summary_unauthenticated_returns_401(client):
    assert client.get("/api/ec2/costs/summary").status_code == 401


def test_cost_summary_response_shape(client, admin_headers, mock_aws_service):
    r = client.get("/api/ec2/costs/summary", headers=admin_headers)
    data = r.json()
    assert "month_to_date" in data
    assert "projected_monthly" in data
    assert "days_elapsed" in data


def test_cost_summary_values_pass_through(client, admin_headers, mock_aws_service):
    # Verify mock values reach the response.
    mock_aws_service.get_monthly_summary.return_value = {
        "month_to_date": 45.0,
        "projected_monthly": 90.0,
        "days_elapsed": 15,
    }
    data = client.get("/api/ec2/costs/summary", headers=admin_headers).json()
    assert data["month_to_date"] == 45.0
    assert data["projected_monthly"] == 90.0
    assert data["days_elapsed"] == 15


@pytest.mark.unit
def test_cost_summary_projection_math(monkeypatch):
    # The route only returns get_monthly_summary(); the projection formula lives
    # in aws_service.py, so this patches the Cost Explorer client directly.
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 1, 16, tzinfo=timezone.utc)

    class FakeCostExplorerClient:
        def get_cost_and_usage(self, **request):
            return {
                "ResultsByTime": [
                    {"Total": {"BlendedCost": {"Amount": "45.0"}}}
                ]
            }

    monkeypatch.setattr(real_aws_service.settings, "enable_cost_explorer", True)
    monkeypatch.setattr(real_aws_service, "datetime", FrozenDateTime)
    monkeypatch.setattr(
        real_aws_service,
        "get_cost_explorer_client_for_user",
        lambda user_role=None, user_id=None: FakeCostExplorerClient(),
    )

    data = real_aws_service.get_monthly_summary()

    assert data["month_to_date"] == 45.0
    assert data["days_elapsed"] == 15
    assert data["projected_monthly"] == 90.0


def test_cost_summary_aws_error_returns_502(client, admin_headers, mock_aws_service):
    mock_aws_service.get_monthly_summary.side_effect = AWSServiceError("CE unavailable")
    assert client.get("/api/ec2/costs/summary", headers=admin_headers).status_code == 502
