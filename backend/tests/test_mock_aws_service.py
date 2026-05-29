# Unit tests for mock_aws_service.py.
#
# These tests exercise the local AWS mock backend that powers CloudSim when
# CLOUDSIM_AWS_BACKEND=mock. They use an in-memory SQLite database so each test
# can create realistic Instance rows without touching Postgres or live AWS.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app import aws_service, mock_aws_service


def _install_mock_db(monkeypatch):
    # Give mock_aws_service its own temporary database session factory.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    monkeypatch.setattr(mock_aws_service, "SessionLocal", TestingSessionLocal)
    return engine


# Test 01: Mock create/list/get returns a realistic instance shape.
def test_mock_create_list_and_get_instance(monkeypatch):
    engine = _install_mock_db(monkeypatch)

    created = mock_aws_service.create_instance(
        name="demo-web",
        instance_type="t2.micro",
        user_id=7,
        user_email="demo@example.com",
    )
    instance_id = created["instance_id"]

    instances = mock_aws_service.list_instances(user_role="User", user_id=7)
    details = mock_aws_service.get_instance(instance_id, user_role="User", user_id=7)

    assert len(instances) == 1
    assert instances[0]["instance_id"] == instance_id
    assert details["name"] == "demo-web"
    assert details["security_groups"][0]["GroupId"] == "sg-mock-web"
    assert {"Key": "CreatedBy", "Value": "7"} in details["tags"]

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# Test 02: Regular users only see instances tagged with their own user ID.
def test_mock_user_list_is_scoped_by_owner(monkeypatch):
    engine = _install_mock_db(monkeypatch)

    mine = mock_aws_service.create_instance("mine", user_id=1)["instance_id"]
    other = mock_aws_service.create_instance("other", user_id=2)["instance_id"]

    user_instances = mock_aws_service.list_instances(user_role="User", user_id=1)
    admin_instances = mock_aws_service.list_instances(user_role="Admin", user_id=99)

    assert [instance["instance_id"] for instance in user_instances] == [mine]
    assert {instance["instance_id"] for instance in admin_instances} == {mine, other}

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# Test 03: Mock lifecycle changes drive current metrics, costs, and deletion.
def test_mock_lifecycle_metrics_and_costs(monkeypatch):
    engine = _install_mock_db(monkeypatch)

    created = mock_aws_service.create_instance("demo", user_id=3)
    instance_id = created["instance_id"]

    mock_aws_service.stop_instance(instance_id)
    stopped_metrics = mock_aws_service.get_instance_current_metrics(instance_id)
    assert stopped_metrics["cpu_percent"] == 0.0

    mock_aws_service.start_instance(instance_id)
    running_metrics = mock_aws_service.get_instance_current_metrics(instance_id)
    assert running_metrics["cpu_percent"] > 0

    costs = mock_aws_service.get_daily_costs(days=3, user_role="User", user_id=3)
    summary = mock_aws_service.get_monthly_summary(user_role="User", user_id=3)

    assert len(costs) == 3
    assert costs[0]["total"] > 0
    assert summary["projected_monthly"] > 0

    mock_aws_service.terminate_instance(instance_id)
    assert mock_aws_service.list_instances(user_role="Admin", user_id=1) == []

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# Test 04: aws_service delegates to the mock facade without initializing boto3.
def test_aws_service_facade_uses_mock_without_boto3(monkeypatch):
    class FakeMockService:
        # This tiny fake proves the facade forwards calls to _mock_service().
        @staticmethod
        def get_available_instance_types():
            return ["t2.micro"]

    monkeypatch.setattr(aws_service.settings, "aws_backend", "mock")
    monkeypatch.setattr(aws_service, "_mock_service", lambda: FakeMockService)
    monkeypatch.setattr(
        aws_service,
        "_get_boto3_session",
        lambda: (_ for _ in ()).throw(AssertionError("boto3 should not be initialized")),
    )

    assert aws_service.get_available_instance_types() == ["t2.micro"]
