import pytest

pytestmark = pytest.mark.api


# =============================================================================
# GET /api/admin/users
# =============================================================================
# we express the full access matrix in one place. Each tuple is one test case.
# If a new role is added, we just need to add one line here
# =============================================================================

#headers_fixture is the name of a fixture that provides the appropriate auth headers for that role
#expected is the expected HTTP status code when that role tries to access the endpoint
#test must have parameters in the function signature for headers_fixture and expected. pytest will inject the values from parametrize into those parameters when running the test.
#Use decorator to run the same test function with different sets of parameters, allowing us to test multiple roles and their expected access outcomes in a concise way.
@pytest.mark.parametrize("headers_fixture,expected", [
    ("admin_headers",  200),
    ("devops_headers", 403),
    ("user_headers",   403),
])
def test_list_users_rbac(request, client, headers_fixture, expected): #params are built-in from pytest
    # request.getfixturevalue is the only pytest-native way to use a fixture
    # whose name is a runtime string (e.g. from parametrize).
    headers = request.getfixturevalue(headers_fixture) #use request for fixure injection based on the string name provided in parametrize
    assert client.get("/api/admin/users", headers=headers).status_code == expected


def test_list_users_unauthenticated_returns_401(client):
    assert client.get("/api/admin/users").status_code == 401


#Users are imported by the fixture from conftest.py by pytest automatically
def test_list_users_returns_all_users(client, admin_headers, admin_user, devops_user, regular_user):
    r = client.get("/api/admin/users", headers=admin_headers)
    emails = [u["email"] for u in r.json()]
    assert admin_user.email in emails
    assert devops_user.email in emails
    assert regular_user.email in emails


# =============================================================================
# POST /api/admin/users
# =============================================================================

@pytest.mark.parametrize("headers_fixture,expected", [
    ("admin_headers",  201),
    ("devops_headers", 403),
    ("user_headers",   403),
])
def test_create_user_rbac(request, client, headers_fixture, expected):
    headers = request.getfixturevalue(headers_fixture)
    r = client.post("/api/admin/users", json={
        "email": "created@example.com",
        "password": "pw123",
        "role": "User",
    }, headers=headers)
    assert r.status_code == expected


def test_create_user_unauthenticated_returns_401(client):
    r = client.post("/api/admin/users", json={
        "email": "created@example.com",
        "password": "pw123",
        "role": "User",
    })
    assert r.status_code == 401


def test_create_user_invalid_role_returns_400(client, admin_headers):
    # SQLite silently ignores CHECK constraints, so the Python-layer check
    # in admin_routes.py:157 is the only thing preventing invalid roles.
    # If that check is removed, this test fails while SQLite tests still pass.
    r = client.post("/api/admin/users", json={
        "email": "created@example.com",
        "password": "pw123",
        "role": "Superuser",
    }, headers=admin_headers)
    assert r.status_code == 400


def test_create_user_duplicate_email_returns_409(client, admin_headers, regular_user):
    r = client.post("/api/admin/users", json={
        "email": regular_user.email,
        "password": "pw123",
        "role": "User",
    }, headers=admin_headers)
    assert r.status_code == 409


# =============================================================================
# PUT /api/admin/users/{user_id}
# =============================================================================

@pytest.mark.parametrize("headers_fixture,expected", [
    ("admin_headers",  200),
    ("devops_headers", 403),
    ("user_headers",   403),
])
def test_update_user_rbac(request, client, regular_user, headers_fixture, expected):
    # regular_user is needed so the admin case has a real user_id to update.
    # devops/user cases 403 before reaching the DB lookup, so they don't care.
    headers = request.getfixturevalue(headers_fixture)
    r = client.put(
        f"/api/admin/users/{regular_user.id}",
        json={"role": "User"},
        headers=headers,
    )
    assert r.status_code == expected


def test_update_user_unauthenticated_returns_401(client, regular_user):
    r = client.put(f"/api/admin/users/{regular_user.id}", json={"role": "User"})
    assert r.status_code == 401


def test_admin_cannot_disable_own_account(client, admin_user, admin_headers):
    # Guard is at admin_routes.py:214.
    # An admin disabling themselves would lock out the only admin account.
    r = client.put(
        f"/api/admin/users/{admin_user.id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert r.status_code == 400


def test_update_user_not_found_returns_404(client, admin_headers):
    r = client.put("/api/admin/users/99999", json={"role": "User"}, headers=admin_headers)
    assert r.status_code == 404 #404 is HTTP status code for "Not Found"

def test_update_user_invalid_role_returns_400(client, admin_headers, regular_user):
    r = client.put(
        f"/api/admin/users/{regular_user.id}",
        json={"role": "Overlord"},
        headers=admin_headers,
    )
    assert r.status_code == 400


# =============================================================================
# DELETE /api/admin/users/{user_id}
# =============================================================================

@pytest.mark.parametrize("headers_fixture,expected", [
    ("admin_headers",  200),
    ("devops_headers", 403),
    ("user_headers",   403),
])
def test_delete_user_rbac(request, client, regular_user, headers_fixture, expected):
    # Each parametrize case gets a fresh db_session (function-scoped),
    # so the admin case deleting regular_user doesn't affect the other two cases.
    headers = request.getfixturevalue(headers_fixture)
    r = client.delete(f"/api/admin/users/{regular_user.id}", headers=headers)
    assert r.status_code == expected


def test_delete_user_unauthenticated_returns_401(client, regular_user):
    r = client.delete(f"/api/admin/users/{regular_user.id}")
    assert r.status_code == 401


def test_admin_cannot_delete_own_account(client, admin_user, admin_headers):
    # Guard is at admin_routes.py:271.
    r = client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)
    assert r.status_code == 400


def test_delete_user_not_found_returns_404(client, admin_headers):
    r = client.delete("/api/admin/users/99999", headers=admin_headers)
    assert r.status_code == 404
