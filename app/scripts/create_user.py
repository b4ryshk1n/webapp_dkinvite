from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select
from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import User, UserRole
from dkinvite.utils.security import hash_password

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", required=True, choices=["admin", "controller"])
    parser.add_argument("--full-name", default=None)
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        exists = db.session.scalar(
            select(User).where(User.username == args.username.strip().lower())
        )
        if exists:
            raise SystemExit("Пользователь уже существует")

        user = User(
            username=args.username.strip().lower(),
            password_hash=hash_password(args.password),
            role=UserRole(args.role),
            full_name=args.full_name,
        )
        db.session.add(user)
        db.session.commit()

        print(f"Пользователь создан: {user.username} ({args.role})")

if __name__ == "__main__":
    main()
