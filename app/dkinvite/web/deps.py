from functools import wraps

from flask import g, redirect, render_template, session, url_for

from dkinvite.repositories.user_repository import UserRepository

def require_web_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("web.login"))

        user = UserRepository.get_by_id(int(user_id))
        if not user:
            session.clear()
            return redirect(url_for("web.login"))

        g.current_user = user
        return view_func(*args, **kwargs)

    return wrapper

def require_web_roles(*allowed_roles):
    normalized = {
        role.value if hasattr(role, "value") else str(role)
        for role in allowed_roles
    }

    def decorator(view_func):
        @wraps(view_func)
        @require_web_auth
        def wrapper(*args, **kwargs):
            current_role = (
                g.current_user.role.value
                if hasattr(g.current_user.role, "value")
                else str(g.current_user.role)
            )

            if current_role not in normalized:
                return render_template("403.html"), 403

            return view_func(*args, **kwargs)

        return wrapper

    return decorator
