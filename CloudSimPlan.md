# CloudSim — Full Testing Suite Implementation Plan

## Context

CloudSim has a complete, working FastAPI + SQLAlchemy + boto3 backend with zero test coverage.
A broken `conftest.py` (syntax error on line 50) and missing test libraries are the only blockers.
This plan builds a ~119-test suite from scratch, structured as a **pair coding session** that
teaches the WHY behind each decision — not just what to write.

**Goal:** Understand and implement Unit → Integration → API testing layers with real-world
RBAC testing, AWS mocking, and side-effect verification.

---

## Current State

| Item | Status |
|---|---|
| `backend/tests/conftest.py` | Broken — `db = \n()` syntax error on line 50 |
| `backend/tests/__init__.py` | Empty |
| Test libraries in requirements.txt | None — pytest/httpx/moto all missing |
| `pytest.ini` | Does not exist |
| Test files | Zero |

**Critical bugs in conftest.py:**
1. Line 50: `db =` followed by `()` on the next line — Python syntax error, nothing runs
2. Line 48: `scope="function"` and `autouse=False` passed as *function arguments* instead of to `@pytest.fixture(scope=...)` — they are silently ignored
3. Missing: transactional isolation (tests bleed into each other without rollback)
4. Missing: token/auth header helper fixtures
5. Missing: user fixtures for each role

**aws_service.py module-level client problem:**
Lines 119–121 create `ec2`, `ec2_resource` at import time.
`moto`'s `@mock_aws` activated *after* import won't intercept these pre-built clients.
**Solution:** patch `app.ec2_routes.aws_service` as a module mock for route tests.
Reserve `moto` for direct `aws_service.py` unit tests (optional, lower priority).

---

## Files to Create / Modify

| File | Action |
|---|---|
| `backend/requirements-dev.txt` | **Create** — test-only dependencies |
| `backend/pytest.ini` | **Create** — pytest config, asyncio mode, markers |
| `backend/tests/conftest.py` | **Rewrite** — fix all bugs, add role fixtures + mock_aws_service |
| `backend/tests/test_auth_unit.py` | **Create** — unit tests, no DB/HTTP (~12 tests) |
| `backend/tests/test_auth_routes.py` | **Create** — API tests for register/login/me (~18 tests) |
| `backend/tests/test_admin_routes.py` | **Create** — RBAC tests for user CRUD (~20 tests) |
| `backend/tests/test_helpers.py` | **Create** — unit + integration for EC2 helpers (~22 tests) |
| `backend/tests/test_ec2_routes.py` | **Create** — EC2 endpoints with mocked aws_service (~25 tests) |
| `backend/tests/test_metrics_routes.py` | **Create** — side-effect (DB persistence) tests (~12 tests) |
| `backend/tests/test_costs_routes.py` | **Create** — Cost Explorer endpoints (~10 tests) |

---

## Step-by-Step Implementation

### Step 1 — Install test dependencies

Create `backend/requirements-dev.txt`:
```
pytest>=8.0.0
pytest-asyncio>=0.23.0    # routes are async def — without this they silently pass without running
pytest-cov>=5.0.0         # coverage reports
httpx>=0.27.0             # TestClient dependency in newer FastAPI/Starlette
moto[ec2,cloudwatch,ce]>=5.0.0  # intercept boto3 calls at the botocore transport layer
```

Install: `pip install -r requirements-dev.txt` (inside venv)

**Teaching moment:** Why `pytest-asyncio`? All routes use `async def`. Without this plugin,
`async def test_foo()` returns a coroutine object that pytest sees as truthy — the test "passes"
without running. This is one of the most common silent-failure bugs in async test suites.

---

### Step 2 — Create pytest.ini

`backend/pytest.ini`:
```ini
[pytest]
testpaths = tests
minversion = 8.0
asyncio_mode = auto
markers =
    unit: Pure functions, no IO
    integration: DB involved, no HTTP
    api: Full HTTP through TestClient
    aws: Requires moto
addopts = -v --tb=short
log_cli = true
log_cli_level = WARNING
```

**Teaching moment:** `asyncio_mode = auto` means every `async def test_*` function is treated
as an async test automatically. Without it you'd need `@pytest.mark.asyncio` on every function.

---

### Step 3 — Rewrite conftest.py

**Key concepts taught:**
- `dependency_overrides` — FastAPI's way to swap `Depends()` at test time (the correct pattern, not monkey-patching)
- Transactional isolation — `session.begin_nested()` + `transaction.rollback()` resets DB state between tests in microseconds vs dropping/recreating tables
- Fixture scope: `session` for engine/tables, `function` for sessions/users (avoids test pollution)
- Real JWT tokens in fixtures (not fake strings) so the full auth path is exercised

**conftest.py structure:**
```
engine (session scope) ← TestingSessionLocal ← db_session (function scope, nested txn)
                                                      ↓
                                               client fixture (overrides get_db)
                                                      ↓
admin_user / devops_user / regular_user / inactive_user fixtures
                                                      ↓
admin_headers / devops_headers / user_headers (real JWTs)
                                                      ↓
mock_aws_service fixture (patches app.ec2_routes.aws_service module)
```

**SQLite caveat to teach:** `CheckConstraint("role IN (...)")` is silently ignored by SQLite.
Role validation in tests relies on the Python-layer check in `admin_routes.py`, not the DB.
This is acceptable — it means if the Python check is removed, tests pass locally but fail in prod PostgreSQL.

---

### Step 4 — test_auth_unit.py (Start here — zero dependencies)

**Teaching concept:** Unit testing pure functions. No DB, no HTTP, no side effects. Fastest possible feedback loop.

Target functions (all in `backend/app/auth.py`):
- `get_password_hash(password)` → `verify_password(plain, hash)`
- `create_access_token(data, expires_delta)`

Key tests to understand:
- `test_hash_different_each_call` — bcrypt uses random salt; hashing "x" twice gives two *different* strings. Tests that rainbow table attacks don't work.
- `test_verify_wrong_hash_returns_false_not_exception` — corrupt DB hash must fail gracefully
- `test_expired_token_fails_decode` — `expires_delta=timedelta(seconds=-1)` creates an already-expired token. If this test fails, stolen tokens work forever.
- `test_token_payload_contains_sub` — The `sub` field is what `get_current_user()` uses to look up the user. If it's missing, every request returns 401.

~12 tests. Run time: < 0.5 seconds.

---

### Step 5 — test_auth_routes.py

**Teaching concept:** API tests verify HTTP *contracts* — status codes, response shapes, security behaviors.
The 401 vs 403 distinction is critical:
- 401 = "I don't know who you are" → browser redirects to login
- 403 = "I know who you are, but no" → browser shows access denied

Key tests to understand:
- `test_register_returns_no_password` — Response MUST NOT include `hashed_password`. Most important security test here.
- `test_register_default_role_is_user` — New registrations default to "User", never "Admin". Privilege escalation guard.
- `test_login_same_error_for_wrong_password_and_nonexistent_email` — Prevents user enumeration (attacker can't discover which emails exist by comparing error messages)
- `test_login_inactive_user_returns_403_not_401` — The 401 vs 403 distinction: credentials are valid, account is disabled
- `test_login_uses_form_not_json` — OAuth2PasswordRequestForm requires `application/x-www-form-urlencoded`. Sending JSON returns 422. Tests a real frontend gotcha.
- `test_expired_token_me_returns_401` — `expires_delta=timedelta(seconds=-1)` tests the expiry enforcement end-to-end

~18 tests.

---

### Step 6 — test_admin_routes.py

**Teaching concept:** RBAC testing with `@pytest.mark.parametrize`. Instead of 3 duplicate tests
per endpoint, parametrize over roles:

```python
@pytest.mark.parametrize("headers_fixture,expected", [
    ("admin_headers",  200),
    ("devops_headers", 403),
    ("user_headers",   403),
])
def test_list_users_rbac(request, client, headers_fixture, expected):
    headers = request.getfixturevalue(headers_fixture)
    assert client.get("/api/admin/users", headers=headers).status_code == expected
```

Key tests to understand:
- `test_admin_cannot_disable_own_account` — Admin disabling themselves = lockout. Guard is in `admin_routes.py:214`. Test passes `user_id=admin.id` + `is_active=False`.
- `test_admin_cannot_delete_own_account` — Same concept. Guard is in `admin_routes.py:271`.
- `test_create_user_invalid_role_returns_400` — Tests the Python-layer role validation that compensates for SQLite's ignored CHECK constraint.
- Pattern: every endpoint gets a `test_*_unauthenticated_returns_401` test.

~20 tests.

---

### Step 7 — test_helpers.py

**Teaching concept:** Helper functions are hard to test via HTTP (too much setup) but trivial to
test directly. Unit test the logic, integration test the DB side effects.

**Unit tests** (no DB, no HTTP — pure Python dicts + User objects):
- `_filter_instances_for_user` in `ec2_routes.py:261`
  - Admin/DevOps: all instances pass through
  - User: only instances where `CreatedBy` tag == `str(user.id)` survive
  - Edge case: instance with NO tags → excluded for User role
- `_check_instance_ownership` in `ec2_routes.py:309`
  - Patch `app.ec2_routes.aws_service.get_instance` to return a fake instance dict
  - Admin/DevOps always return True without hitting AWS

**Integration tests** (real SQLite session via `db_session` fixture):
- `sync_instances_to_db` in `ec2_routes.py:146`
  - Run twice with same data → row count unchanged (upsert, not insert)
  - Invalid launch_time → `launch_time=None`, no crash
- `persist_metrics_to_db` in `ec2_routes.py:203`
  - **The idempotency test:** call twice with same CloudWatch data → exact same row count both times. Tests the `already_exists` guard.

~22 tests.

---

### Step 8 — test_ec2_routes.py

**Teaching concept:** Mocking external services. Why `patch` over `moto` here:
- `aws_service.py` creates `ec2` / `ec2_resource` at *module import time* (lines 119–121)
- `moto`'s `@mock_aws` only intercepts boto3 calls made *after* the mock is activated
- Pre-imported clients bypass moto → tests hit real AWS or error
- **Solution:** `mock_aws_service` fixture patches the entire `aws_service` module as used by `ec2_routes`

```python
# conftest.py fixture
@pytest.fixture
def mock_aws_service():
    with patch("app.ec2_routes.aws_service") as mock:
        mock.list_instances.return_value = []
        mock.get_available_instance_types.return_value = ["t2.nano","t2.micro","t2.small","t2.medium","t2.large"]
        mock.get_instance_metrics.return_value = {"instance_id":"i-test","cpu_utilization":[],...}
        mock.get_daily_costs.return_value = []
        mock.get_monthly_summary.return_value = {"month_to_date":0.0,"projected_monthly":0.0,"days_elapsed":1}
        yield mock
```

Key tests to understand:
- `test_list_instances_user_sees_only_own` — Most important RBAC test. Populate `mock_aws_service.list_instances.return_value` with 2 instances tagged for different users. User sees 1.
- `test_create_instance_invalid_type_returns_400` — Validation must fire *before* AWS call. Test that `"t3.large"` returns 400 without touching mocked AWS.
- `test_list_instances_triggers_db_sync` — After calling the endpoint, query `db_session` directly for `Instance` rows. Tests the `sync_instances_to_db` side effect at the API layer.
- `test_start_instance_all_four_action_types` — start/stop/reboot/terminate all have identical ownership logic. Test all four to catch copy-paste errors.
- Simulating AWS errors: `mock_aws_service.list_instances.side_effect = AWSServiceError(...)` → assert 502; `AWSConfigurationError` → assert 503.

~25 tests.

---

### Step 9 — test_metrics_routes.py

**Teaching concept:** Testing side effects. The metrics endpoint has TWO observable behaviors:
returns data (visible in response) AND writes to `metrics` table (invisible in response).
Both must be tested explicitly.

Key tests:
- `test_metrics_persists_to_database` — After `GET /api/ec2/instances/{id}/metrics`, query `db_session.query(Metric).count()`. Must be > 0.
- `test_metrics_idempotent_on_second_call` — Call the same endpoint twice (same mocked CloudWatch data). `Metric` count after call 2 == count after call 1. Tests the `already_exists` guard at the API level.
- `test_metrics_response_shape` — Response must have `instance_id`, `cpu_utilization`, `network_in`, `network_out`, `disk_read_ops`, `disk_write_ops`. Tests the frontend contract.

~12 tests.

---

### Step 10 — test_costs_routes.py

**Teaching concept:** Testing endpoints where all roles are permitted (auth required, not RBAC-gated).
A different pattern from admin routes.

Key tests:
- Parametrize `test_daily_costs_all_roles_return_200` over admin/devops/user headers — all three must succeed
- `test_daily_costs_unauthenticated_401` — even with no RBAC, a token is still required
- `test_cost_summary_projection_math` — If `month_to_date=45` and `days_elapsed=15`, `projected = 90`. Tests the calculation.

~10 tests.

---

## How to Run

```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt

# All tests
pytest

# With coverage (target 75–80%)
pytest --cov=app --cov-report=term-missing

# Fast feedback during writing (unit only)
pytest -m unit

# Stop at first failure
pytest -x

# One file
pytest tests/test_auth_routes.py::test_register_success
```

---

## Priority / Execution Order

| Order | File | Teaches | Est. Time |
|---|---|---|---|
| 1 | `conftest.py` rewrite | Dependency injection, transactional isolation, fixtures | 1.5 hr |
| 2 | `requirements-dev.txt` + `pytest.ini` | Dev tooling setup | 20 min |
| 3 | `test_auth_unit.py` | Pure function testing, JWT, bcrypt | 1.5 hr |
| 4 | `test_auth_routes.py` | HTTP contracts, 401 vs 403, security | 2 hr |
| 5 | `test_helpers.py` | Unit + integration, idempotency | 2.5 hr |
| 6 | `test_admin_routes.py` | RBAC testing, parametrize | 2 hr |
| 7 | `test_ec2_routes.py` | Mocking external services, side effects | 3.5 hr |
| 8 | `test_metrics_routes.py` | Side-effect testing | 2 hr |
| 9 | `test_costs_routes.py` | Cross-role auth, query params | 1.5 hr |

**Total: ~120 tests, ~16 hours of pair coding across all steps**

---

## Coverage Targets (after all steps)

| Module | Target |
|---|---|
| `auth.py` | 95%+ |
| `auth_routes.py` | 90%+ |
| `admin_routes.py` | 90%+ |
| `ec2_routes.py` | 75%+ |
| `aws_service.py` | 30–40% (via patches; deeper coverage optional via moto) |
| **Overall** | **75–80%** |
