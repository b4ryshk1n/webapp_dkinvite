from dkinvite.repositories.user_repository import UserRepository
from dkinvite.utils.security import create_access_token, verify_password

class AuthService:
    @staticmethod
    def authenticate(username: str, password: str):
        user = UserRepository.get_by_username(username)
        if not user:
            return None

        if not verify_password(user.password_hash, password):
            return None

        role = user.role.value if hasattr(user.role, "value") else str(user.role)

        token = create_access_token(
            user_id=user.id,
            username=user.username,
            role=role,
        )
        return user, token
