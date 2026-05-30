"""Production startup bootstrap helpers."""

from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from .auth import get_password_hash
from .config import settings as app_settings
from .db import SessionLocal
from .models import User


logger = logging.getLogger(__name__)


class AdminBootstrapError(RuntimeError):
    """Raised when admin bootstrap is enabled but misconfigured."""


def _required_text(value: str | None, env_name: str) -> str:
    if value is None or value.strip() == "":
        raise AdminBootstrapError(
            f"{env_name} is required when CLOUDSIM_BOOTSTRAP_ADMIN_ENABLED=true"
        )
    return value.strip()


def bootstrap_admin_user_in_session(db: Session, settings: Any = app_settings) -> str | None:
    """Create or restore the configured admin account inside an existing session."""
    if not settings.bootstrap_admin_enabled:
        return None

    email = _required_text(
        settings.bootstrap_admin_email,
        "CLOUDSIM_BOOTSTRAP_ADMIN_EMAIL",
    )
    password = _required_text(
        settings.bootstrap_admin_password,
        "CLOUDSIM_BOOTSTRAP_ADMIN_PASSWORD",
    )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role="Admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        return "created"

    changed = False
    action = "verified"

    if user.role != "Admin":
        user.role = "Admin"
        changed = True
        action = "promoted"

    if not user.is_active:
        user.is_active = True
        changed = True
        if action == "verified":
            action = "reactivated"

    if settings.bootstrap_admin_reset_password:
        user.hashed_password = get_password_hash(password)
        changed = True
        if action == "verified":
            action = "password-reset"

    if changed:
        db.commit()

    return action


def bootstrap_admin_user(
    settings: Any = app_settings,
    session_factory: Callable[[], Session] = SessionLocal,
) -> str | None:
    """Run admin bootstrap with an owned database session."""
    db = session_factory()
    try:
        action = bootstrap_admin_user_in_session(db, settings)
        if action is not None:
            logger.info("Bootstrap admin account %s for %s", action, settings.bootstrap_admin_email)
        return action
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
