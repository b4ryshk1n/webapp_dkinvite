from flask import Blueprint, g, request

from dkinvite.api.deps import require_auth
from dkinvite.api.responses import error_response, success_response
from dkinvite.api.serializers import serialize_user
from dkinvite.services.auth_service import AuthService

bp = Blueprint("auth_api", __name__)

@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return error_response(
            "validation_error",
            "Необходимо передать username и password",
            400,
        )

    result = AuthService.authenticate(username, password)
    if not result:
        return error_response(
            "invalid_credentials",
            "Неверный логин или пароль",
            401,
        )

    user, token = result

    return success_response(
        {
            "access_token": token,
            "token_type": "Bearer",
            "user": serialize_user(user),
        },
        status_code=200,
    )

@bp.get("/me")
@require_auth
def me():
    return success_response({"user": serialize_user(g.current_user)})
