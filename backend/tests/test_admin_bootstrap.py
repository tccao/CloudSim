from types import SimpleNamespace

import pytest

from app.auth import get_password_hash, verify_password
from app.bootstrap import (
    AdminBootstrapError,
    bootstrap_admin_user,
    bootstrap_admin_user_in_session,
)
from app.models import User


def _settings(
    *,
    enabled=True,
    email="prod-admin@example.com",
    password="replace-me-with-a-secret",
    reset_password=False,
):
    return SimpleNamespace(
        bootstrap_admin_enabled=enabled,
        bootstrap_admin_email=email,
        bootstrap_admin_password=password,
        bootstrap_admin_reset_password=reset_password,
    )


def test_bootstrap_disabled_is_noop(db_session):
    action = bootstrap_admin_user_in_session(db_session, _settings(enabled=False))

    assert action is None
    assert db_session.query(User).count() == 0


def test_bootstrap_enabled_requires_email(db_session):
    with pytest.raises(AdminBootstrapError, match="CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL"):
        bootstrap_admin_user_in_session(db_session, _settings(email=" "))


def test_bootstrap_enabled_requires_password(db_session):
    with pytest.raises(AdminBootstrapError, match="CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD"):
        bootstrap_admin_user_in_session(db_session, _settings(password=""))


def test_bootstrap_creates_missing_admin(db_session):
    action = bootstrap_admin_user_in_session(db_session, _settings())

    user = db_session.query(User).filter(User.email == "prod-admin@example.com").one()
    assert action == "created"
    assert user.role == "Admin"
    assert user.is_active is True
    assert verify_password("replace-me-with-a-secret", user.hashed_password)


def test_bootstrap_promotes_existing_user_and_preserves_password(db_session):
    original_password = "existing-password"
    user = User(
        email="prod-admin@example.com",
        hashed_password=get_password_hash(original_password),
        role="User",
        is_active=False,
    )
    db_session.add(user)
    db_session.flush()

    action = bootstrap_admin_user_in_session(
        db_session,
        _settings(password="new-bootstrap-password"),
    )

    db_session.refresh(user)
    assert action == "promoted"
    assert user.role == "Admin"
    assert user.is_active is True
    assert verify_password(original_password, user.hashed_password)
    assert not verify_password("new-bootstrap-password", user.hashed_password)


def test_bootstrap_resets_password_only_when_requested(db_session):
    user = User(
        email="prod-admin@example.com",
        hashed_password=get_password_hash("old-password"),
        role="Admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    action = bootstrap_admin_user_in_session(
        db_session,
        _settings(password="new-bootstrap-password", reset_password=True),
    )

    db_session.refresh(user)
    assert action == "password-reset"
    assert verify_password("new-bootstrap-password", user.hashed_password)
    assert not verify_password("old-password", user.hashed_password)


def test_bootstrap_does_not_log_password_or_hash(db_session, caplog):
    settings = _settings(password="super-secret-admin-password")

    with caplog.at_level("INFO", logger="app.bootstrap"):
        bootstrap_admin_user(settings=settings, session_factory=lambda: db_session)

    assert "super-secret-admin-password" not in caplog.text
    assert "$2b$" not in caplog.text
