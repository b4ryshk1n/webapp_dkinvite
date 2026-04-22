from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

def hash_password(password: str) -> str:
    password = (password or "").strip()
    if len(password) < 8:
        raise ValueError("Пароль должен быть не короче 8 символов")
    return generate_password_hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    if not password_hash or not password:
        return False
    return check_password_hash(password_hash, password)

def create_access_token(*, user_id: int, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(
        minutes=current_app.config["JWT_ACCESS_TOKEN_EXPIRES_MINUTES"]
    )

    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET_KEY"],
        algorithms=["HS256"],
    )
