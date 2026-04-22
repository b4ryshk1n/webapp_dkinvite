from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import UserRole
from dkinvite.repositories.user_repository import UserRepository
from dkinvite.utils.security import hash_password

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default=None)
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        exists = UserRepository.get_by_username(args.username)
        if exists:
            print("Пользователь уже существует")
            return

        user = UserRepository.create(
            username=args.username,
            password_hash=hash_password(args.password),
            role=UserRole.admin,
            full_name=args.full_name,
        )
        db.session.commit()
        print(f"Администратор создан: {user.username}")

if __name__ == "__main__":
    main()
