from sqlalchemy import select

from dkinvite.extensions import db
from dkinvite.models import User, UserRole

class UserRepository:
    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_username(username: str) -> User | None:
        normalized = (username or "").strip().lower()
        if not normalized:
            return None
        return db.session.scalar(
            select(User).where(User.username == normalized)
        )

    @staticmethod
    def has_admin() -> bool:
        return (
            db.session.scalar(
                select(User.id).where(User.role == UserRole.admin).limit(1)
            )
            is not None
        )

    @staticmethod
    def create(
        *,
        username: str,
        password_hash: str,
        role: UserRole,
        full_name: str | None = None,
    ) -> User:
        user = User(
            username=(username or "").strip().lower(),
            password_hash=password_hash,
            role=role,
            full_name=(full_name or None),
        )
        db.session.add(user)
        return user
