"""
Recreate and seed the CloudSim database from the backend ORM.

Usage:
  cd backend
  env -u DEBUG ENVIRONMENT=development DEBUG=true SECRET_KEY=dev-secret-key \
    .venv/bin/python scripts/recreate_seed_database.py --drop-existing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import User


DEFAULT_USERS = [
    {"email": "admin@gmail.com", "password": "admin123", "role": "Admin"},
    {"email": "devops@gmail.com", "password": "devops123", "role": "DevOps Engineer"},
    {"email": "deng@gmail.com", "password": "deng123", "role": "DevOps Engineer"},
    {"email": "user@gmail.com", "password": "user123", "role": "User"},
]


def upsert_seed_users(db: Session) -> list[tuple[str, str]]:
    seeded: list[tuple[str, str]] = []

    for user_data in DEFAULT_USERS:
        user = db.query(User).filter(User.email == user_data["email"]).first()
        if user is None:
            user = User(email=user_data["email"])
            db.add(user)

        user.hashed_password = get_password_hash(user_data["password"])
        user.role = user_data["role"]
        user.is_active = True
        seeded.append((user.email, user.role))

    db.commit()
    return seeded


def recreate_database(drop_existing: bool) -> list[tuple[str, str]]:
    if settings.is_production:
        raise RuntimeError(
            "recreate_seed_database.py is development-only and cannot run when "
            "CLOUDSIM_ENVIRONMENT=production."
        )

    if drop_existing:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        return upsert_seed_users(db)
    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recreate and seed the CloudSim database.")
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing ORM-managed tables before recreating them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seeded = recreate_database(drop_existing=args.drop_existing)

    print("CloudSim database recreation complete.")
    for email, role in seeded:
        print(f"- {email} -> {role}")


if __name__ == "__main__":
    main()
