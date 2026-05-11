# =============================================================================
# conftest.py — Shared Test Fixtures for CloudSim
# =============================================================================
# pytest automatically discovers conftest.py and makes its fixtures available
# to all test files in this directory (and subdirectories).
#
# ARCHITECTURE:
#   engine (session scope)
#     └── TestingSessionLocal
#           └── db_session (function scope, nested transaction)
#                 └── client (overrides get_db dependency)
#                       └── user fixtures (admin, devops, regular, inactive)
#                             └── header fixtures (real JWT tokens)
#   mock_aws_service (function scope, patches aws_service module)
#
# KEY DECISIONS:
# 1. SQLite in-memory for tests — fast, no Docker/Postgres needed
# 2. Nested transactions — each test rolls back, so tests don't affect each other
# 3. Real JWT tokens in fixtures — exercises the full auth path, not fake strings
# 4. dependency_overrides for get_db — FastAPI's official test pattern
# =============================================================================

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# WHY these specific imports?
# - Base: we need it to create tables (Base.metadata.create_all)
# - get_db: we need to OVERRIDE this dependency in the FastAPI app
# - app: the actual FastAPI application instance
# - User model: to create test users in fixtures
# - auth functions: to create real JWT tokens for header fixtures
# ---------------------------------------------------------------------------
from app.db import Base, get_db
from app.main import app
from app.models import User
from app.auth import get_password_hash, create_access_token


# =============================================================================
# DATABASE ENGINE (session scope — created once for the entire test run)
# =============================================================================
# WHY session scope?
# Creating an engine is expensive. We only need ONE engine for all tests.
# The tables are created once, and each individual test uses a nested
# transaction that rolls back — so the schema persists but data doesn't.
#
# WHY SQLite in-memory?
# - No Postgres container needed to run tests
# - :memory: means no file on disk, faster than file-based SQLite
# - StaticPool keeps the same connection alive (SQLite :memory: is per-connection)
#
# WHY check_same_thread=False?
# SQLite normally refuses to be used from multiple threads. FastAPI's
# TestClient may use a different thread. This flag disables that check.
# =============================================================================
@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool, #static pool keeps the same connection alive for the entire test session
    )
    # Create all tables defined in our ORM models
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    # After ALL tests finish, drop everything
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


# =============================================================================
# DATABASE SESSION (function scope — fresh for EVERY test)
# =============================================================================
# WHY function scope?
# Each test gets its own session. We use a SAVEPOINT (begin_nested) at the
# start, then ROLLBACK at the end. This means:
#   - Test A creates a user → user exists during Test A
#   - Test A ends → rollback → user is gone
#   - Test B starts with a clean database
#
# This is MUCH faster than dropping/recreating tables between tests.
#
# WHY override commit/rollback?
# The application code calls db.commit(). If we let that go through,
# the data would be permanently written and our rollback wouldn't help.
# By replacing commit with flush, we get the same effect (IDs are assigned,
# queries work) without actually committing to the outer transaction.
# =============================================================================
@pytest.fixture(scope="function")
def db_session(engine):
    #Open connection to the database 
    connection = engine.connect()
    # Start a transaction that will encompass the entire session (temp container for database)
    transaction = connection.begin()
    # Create a session bound to this connection and transaction (python object instead of SQL)
    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()

    # begin_nested() creates a SAVEPOINT whenever commit() is called. 
    nested = session.begin_nested()

    # Intercept commit: replace with flush (assigns IDs but doesn't persist)
    original_commit = session.commit
    def fake_commit():
        nonlocal nested #nonlocal allows us to modify the nested variable defined in the outer scope
        session.flush()
        # Re-establish the savepoint so the next commit also works
        nested = session.begin_nested()

    session.commit = fake_commit

    yield session

    # ---------- TEARDOWN ----------
    # Roll back the outer transaction — everything this test did disappears
    session.close()
    transaction.rollback()
    connection.close()


# =============================================================================
# TEST CLIENT (function scope — uses overridden get_db)
# =============================================================================
# WHY dependency_overrides?
# This is FastAPI's OFFICIAL pattern for testing. In production, get_db()
# yields a SessionLocal(). In tests, we override it to yield our test session
# instead. The application code doesn't change at all.
#
# WHY function scope?
# The client depends on db_session which is function-scoped. If the client
# were session-scoped, it would try to reuse a closed session.
# =============================================================================
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    # Clean up: remove the override so it doesn't leak to other tests
    app.dependency_overrides.clear()


# =============================================================================
# USER FIXTURES — one per role
# =============================================================================
# WHY create users in fixtures instead of via the API?
# 1. Faster — skips HTTP parsing, middleware, response serialization
# 2. Deterministic — we control the exact state (e.g., is_active=False)
# 3. Independent — test_register tests the API; other tests shouldn't depend on it
#
# Each fixture:
# 1. Creates a User with a known password hash
# 2. Adds it to the test session
# 3. Flushes (so .id is assigned) without committing
# 4. Returns the User object
# =============================================================================
TEST_PASSWORD = "testpassword123"


@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash(TEST_PASSWORD),
        role="Admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def devops_user(db_session):
    user = User(
        email="devops@example.com",
        hashed_password=get_password_hash(TEST_PASSWORD),
        role="DevOps Engineer",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def regular_user(db_session):
    user = User(
        email="user@example.com",
        hashed_password=get_password_hash(TEST_PASSWORD),
        role="User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def inactive_user(db_session):
    user = User(
        email="inactive@example.com",
        hashed_password=get_password_hash(TEST_PASSWORD),
        role="User",
        is_active=False,
    )
    db_session.add(user)
    db_session.flush()
    return user


# =============================================================================
# AUTH HEADER FIXTURES — real JWT tokens
# =============================================================================
# WHY real tokens instead of fake strings?
# The full auth pipeline is exercised:
#   Header → oauth2_scheme extracts token → jwt.decode → db.query(User)
# If we used fake strings, we'd only be testing "does the route exist?"
# not "does authentication actually work?"
#
# PATTERN: Each returns a dict like {"Authorization": "Bearer eyJ..."}
# that you pass directly to client.get(..., headers=admin_headers)
# =============================================================================
@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def devops_headers(devops_user):
    token = create_access_token(data={"sub": devops_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(regular_user):
    token = create_access_token(data={"sub": regular_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def inactive_headers(inactive_user):
    """Token for an inactive user — credentials are valid but account is disabled."""
    token = create_access_token(data={"sub": inactive_user.email})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# MOCK AWS SERVICE FIXTURE
# =============================================================================
# WHY patch instead of moto?
# aws_service.py creates ec2 and ec2_resource clients at MODULE IMPORT TIME
# (lines 119-121). moto's @mock_aws only intercepts boto3 calls made AFTER
# activation. Pre-imported clients bypass moto entirely.
#
# SOLUTION: Patch the entire aws_service MODULE as used by ec2_routes.
# This replaces every function call (list_instances, get_instance, etc.)
# with a MagicMock that we can configure per-test.
#
# For direct aws_service.py unit tests, we CAN use moto 
# =============================================================================
@pytest.fixture
def mock_aws_service():
    with patch("app.ec2_routes.aws_service") as mock:
        # Sensible defaults so tests don't crash on unexpected calls
        mock.list_instances.return_value = []
        mock.get_available_instance_types.return_value = [
            "t2.nano", "t2.micro", "t2.small", "t2.medium", "t2.large",
        ]
        mock.get_instance_metrics.return_value = {
            "instance_id": "i-test",
            "cpu_utilization": [],
            "network_in": [],
            "network_out": [],
            "disk_read_ops": [],
            "disk_write_ops": [],
        }
        mock.get_daily_costs.return_value = []
        mock.get_monthly_summary.return_value = {
            "month_to_date": 0.0,
            "projected_monthly": 0.0,
            "days_elapsed": 1,
        }
        yield mock
