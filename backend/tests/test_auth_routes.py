import pytest
from datetime import timedelta

from app.auth import create_access_token

#pytestmark uses a module-level variable to apply the marker to all tests in this file.
pytestmark = pytest.mark.api

# Mirrors conftest.TEST_PASSWORD — the raw password all fixture users are created with.
# Defined here so login tests can send it as form data without importing from conftest.
TEST_PASSWORD = "testpassword123"


# =============================================================================
# POST /api/auth/register
# =============================================================================

#this @ is redundant since we have the module-level pytestmark, but it's here to show the pattern for individual test markers if needed in the future.
@pytest.mark.api
def test_register_success(client): #client fixture provides a test client for making HTTP requests to the API, defined in tests/conftest.py
    r = client.post("/api/auth/register", 
    json={
        "email": "newuser@test.com",
        "password": "password123",
    })
    assert r.status_code == 201 #201 is the standard HTTP status code for "Created"


def test_register_returns_no_password(client):
    # The register route (app/auth_routes.py line 44) returns a full User object from the DB, which includes
    # hashed_password internally. FastAPI's response_model=UserRead is what
    # serializes only safe fields into JSON. This test guards that contract.
    r = client.post("/api/auth/register", json={
        "email": "nopw@test.com",
        "password": "password123",
    })
    assert "hashed_password" not in r.json() # The DB field must never leak to the API response.
    assert "password" not in r.json()


def test_register_default_role_is_user(client):
    # New registrations must never default to Admin
    r = client.post("/api/auth/register", json={
        "email": "defaultrole@test.com",
        "password": "password123",
    })
    print(r.json()) #Use with pytest -s to see this output. It can help debug if the test fails.
    assert r.json()["role"] == "User"


def test_register_duplicate_email_returns_409(client, regular_user):
    #Reject new registration if the email is already in use. The regular_user fixture creates a user with a known email before this test runs.
    r = client.post("/api/auth/register", json={
        "email": regular_user.email,
        "password": "doesntmatter",
    })
    assert r.status_code == 409 #409 Conflict is the standard HTTP status code for a request that conflicts with the current state of the server, such as a duplicate resource.


def test_register_invalid_email_returns_422(client):
    # Pydantic EmailStr rejects this before the route function runs.
    r = client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "password123",
    })
    assert r.status_code == 422 #422 Unprocessable Entity is the standard HTTP status code for a request that is syntactically correct but semantically invalid, such as failing validation.


def test_register_missing_password_returns_422(client):
    r = client.post("/api/auth/register", json={"email": "nopw@test.com"})
    assert r.status_code == 422


# =============================================================================
# POST /api/auth/login
# =============================================================================

def test_login_success_returns_token(client, regular_user):
    r = client.post("/api/auth/login", data={
        "username": regular_user.email,
        "password": TEST_PASSWORD,
    })
    assert r.status_code == 200 #200 OK is the standard HTTP status code for a successful request.
    assert "access_token" in r.json()


def test_login_token_type_is_bearer(client, regular_user):
    r = client.post("/api/auth/login", data={
        "username": regular_user.email,
        "password": TEST_PASSWORD,
    })
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client, regular_user):
    r = client.post("/api/auth/login", data={
        "username": regular_user.email,
        "password": "wrongpassword",
    })
    assert r.status_code == 401 #401 Unauthorized is the standard HTTP status code for failed authentication due to invalid credentials.


def test_login_nonexistent_email_returns_401(client):
    r = client.post("/api/auth/login", data={
        "username": "nobody@test.com",
        "password": "anything",
    })
    assert r.status_code == 401


def test_login_same_error_for_wrong_password_and_nonexistent_email(client, regular_user):
    # Both failures must return the same detail string.
    # If they differ, an attacker can enumerate which emails are registered.
    r_bad_pw = client.post("/api/auth/login", data={
        "username": regular_user.email,
        "password": "wrong",
    })
    r_no_user = client.post("/api/auth/login", data={
        "username": "nobody@test.com",
        "password": "wrong",
    })
    # auth routes return {"detail": "Incorrect email or password"} and 401 for both cases, so the detail strings must match.
    assert r_bad_pw.json()["detail"] == r_no_user.json()["detail"]


def test_login_inactive_user_returns_403_not_401(client, inactive_user):
    # 401 (bad credentials)
    # 403 (account disabled)
    r = client.post("/api/auth/login", data={
        "username": inactive_user.email,
        "password": TEST_PASSWORD,
    })
    assert r.status_code == 403


def test_login_uses_form_not_json(client, regular_user):
    # OAuth2PasswordRequestForm requires application/x-www-form-urlencoded.
    # Sending JSON returns 422 Unprocessable Entity because the form fields are missing. 
    r = client.post("/api/auth/login", json={
        "username": regular_user.email,
        "password": TEST_PASSWORD,
    })
    assert r.status_code == 422 


# =============================================================================
# GET /api/auth/me 
# Fetch current user info based on the token provided in the Authorization header.
# =============================================================================

def test_me_returns_200_with_valid_token(client, user_headers):
    r = client.get("/api/auth/me", headers=user_headers)
    assert r.status_code == 200


def test_me_returns_correct_user(client, admin_user, admin_headers):
    # The token must identify the right user
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.json()["email"] == admin_user.email


def test_me_no_token_returns_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401 #401 Unauthorized


def test_me_invalid_token_returns_401(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


def test_me_inactive_user_token_returns_403(client, inactive_headers):
    r = client.get("/api/auth/me", headers=inactive_headers)
    assert r.status_code == 403


def test_expired_token_me_returns_401(client):
    # Creates a token that is already expired at creation time.
    # Tests the expiry enforcement end-to-end through the full HTTP path.
    expired_token = create_access_token(
        data={"sub": "user@test.com"},
        expires_delta=timedelta(seconds=-1),
    )
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401
