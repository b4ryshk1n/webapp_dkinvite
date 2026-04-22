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
from dkinvite.models import User
from dkinvite.utils.security import hash_password

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        user = db.session.scalar(
            select(User).where(User.username == args.username.strip().lower())
        )

        if not user:
            raise SystemExit("Пользователь не найден")

        user.password_hash = hash_password(args.password)
        db.session.commit()
        print(f"Пароль обновлен для: {user.username}")

if __name__ == "__main__":
    main()
