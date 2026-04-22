from functools import wraps

import jwt
from flask import g, jsonify, request

from dkinvite.repositories.user_repository import UserRepository
from dkinvite.utils.security import decode_access_token

def _extract_bearer_token() -> str | None:
    header = request.headers.get("Authorization", "").strip()
    if not header:
        return None

    parts = header.split(" ", 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None

    return token.strip() or None

def require_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "missing_token"}), 401

        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token_expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "invalid_token"}), 401

        user_id = payload.get("sub")
        if not user_id:
            return jsonify({"error": "invalid_token_payload"}), 401

        user = UserRepository.get_by_id(int(user_id))
        if not user:
            return jsonify({"error": "user_not_found"}), 401

        g.current_user = user
        g.jwt_payload = payload
        return view_func(*args, **kwargs)

    return wrapper

def require_roles(*allowed_roles):
    normalized = {
        role.value if hasattr(role, "value") else str(role)
        for role in allowed_roles
    }

    def decorator(view_func):
        @wraps(view_func)
        @require_auth
        def wrapper(*args, **kwargs):
            current_role = (
                g.current_user.role.value
                if hasattr(g.current_user.role, "value")
                else str(g.current_user.role)
            )

            if current_role not in normalized:
                return jsonify({"error": "forbidden"}), 403

            return view_func(*args, **kwargs)

        return wrapper

    return decorator
