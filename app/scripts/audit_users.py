from __future__ import annotations

import sys
from pathlib import Path
from werkzeug.security import check_password_hash

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select
from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import User

WEAK_PASSWORD_CANDIDATES = [
    "admin",
    "admin123",
    "12345678",
    "password",
    "qwerty123",
    "StrongAdminPass123",
]

def main():
    app = create_app()

    with app.app_context():
        users = list(db.session.scalars(select(User).order_by(User.id.asc())).all())

        if not users:
            print("Пользователей нет.")
            return

        print(f"Найдено пользователей: {len(users)}")
        print("-" * 80)

        for user in users:
            role = user.role.value if hasattr(user.role, "value") else str(user.role)
            created = user.created_at.isoformat() if user.created_at else "-"
            hash_type = "unknown"

            if user.password_hash.startswith("scrypt:"):
                hash_type = "scrypt"
            elif user.password_hash.startswith("pbkdf2:"):
                hash_type = "pbkdf2"

            weak_matches = []
            for candidate in WEAK_PASSWORD_CANDIDATES:
                try:
                    if check_password_hash(user.password_hash, candidate):
                        weak_matches.append(candidate)
                except Exception:
                    pass

            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Role: {role}")
            print(f"Full name: {user.full_name or '-'}")
            print(f"Created at: {created}")
            print(f"Hash type: {hash_type}")

            if hash_type == "unknown":
                print("WARNING: неизвестный формат хеша")

            if weak_matches:
                print("WARNING: найден слабый/временный пароль:", ", ".join(weak_matches))

            print("-" * 80)

if __name__ == "__main__":
    main()
