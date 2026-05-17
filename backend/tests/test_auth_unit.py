
import pytest
from datetime import timedelta

from jose import JWTError, jwt

from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
# Define test password to reuse across test
TEST_PASSWORD = "testpassword123"

pytestmark = pytest.mark.unit


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def test_hash_returns_bcrypt_string():
    h = get_password_hash(TEST_PASSWORD)
    # bcrypt hashes always start with $2b$ (or $2a$/$2y$)
    assert h.startswith("$2")


def test_hash_different_each_call():
    # bcrypt uses a random salt — same input produces different ciphertext every time
    # This prevents leaked hash to be reversed via a rainbow table
    h2 = get_password_hash(TEST_PASSWORD)
    h1 = get_password_hash(TEST_PASSWORD)
    assert h1 != h2


def test_hash_not_equal_to_plain():
    plain = "TEST_PASSWORD"
    assert get_password_hash(plain) != plain


def test_verify_correct_password_returns_true():
    plain = "TEST_PASSWORD"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True


def test_verify_wrong_password_returns_false():
    hashed = get_password_hash(TEST_PASSWORD)
    assert verify_password("wrong", hashed) is False


def test_verify_wrong_hash_returns_false_not_exception():
    # A corrupt row in the DB must not crash the login endpoint
    try:
        result = verify_password(TEST_PASSWORD, "not-a-bcrypt-hash")
        assert result is False
    except Exception as exc:
        pytest.fail(
            f"verify_password raised {type(exc).__name__} on a malformed hash. "
            "Add a try/except in verify_password to return False instead."
        )


def test_round_trip_hash_and_verify():
    plain = "roundtrip-test-99!"
    assert verify_password(plain, get_password_hash(plain)) is True


# =============================================================================
# JWT TOKEN CREATION
# =============================================================================

TEST_EMAIL = "user@example.com"

def test_token_returns_string():
    token = create_access_token(data={"sub": TEST_EMAIL})
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_payload_contains_sub():
    # get_current_user() reads payload["sub"] to look up the user.
    # If sub is missing, every authenticated request returns 401.
    email = TEST_EMAIL
    token = create_access_token(data={"sub": email})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == email


def test_token_has_expiry():
    token = create_access_token(data={"sub": TEST_EMAIL})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_token_default_expiry_is_set():
    # Token created without explicit delta should still expire (not live forever)
    token = create_access_token(data={"sub": TEST_EMAIL})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    from datetime import datetime, timezone
    exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    assert exp_dt > now


def test_expired_token_fails_decode():
    # Stolen tokens must not work after expiry.
    # expires_delta=-1s produces a token that is already expired at creation time.
    expired_token = create_access_token(
        data={"sub": TEST_EMAIL},
        expires_delta=timedelta(seconds=-1),
    )
    with pytest.raises(JWTError):
        jwt.decode(expired_token, SECRET_KEY, algorithms=[ALGORITHM])
