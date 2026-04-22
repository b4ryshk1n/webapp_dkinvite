from pathlib import Path

from flask import Flask, jsonify, render_template, request

from dkinvite.config import Config
from dkinvite.extensions import db, migrate

def create_app(config_class: type[Config] = Config) -> Flask:
    base_dir = Path(__file__).resolve().parent.parent

    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )
    app.json.ensure_ascii = False
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from dkinvite.models import AuditLog, Event, Ticket, User  # noqa: F401
    from dkinvite.api.auth_routes import bp as auth_api_bp
    from dkinvite.api.admin_routes import bp as admin_api_bp
    from dkinvite.api.scan_routes import bp as scan_api_bp
    from dkinvite.web.routes import bp as web_bp
    from dkinvite.web.delivery_routes import bp as delivery_bp

    app.register_blueprint(auth_api_bp, url_prefix="/api/v2/auth")
    app.register_blueprint(admin_api_bp, url_prefix="/api/v2/admin")
    app.register_blueprint(scan_api_bp, url_prefix="/api/v2/scan")
    app.register_blueprint(web_bp)
    app.register_blueprint(delivery_bp)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "app": "dkinvite-v2"}

    @app.get("/api/v2")
    def api_index():
        return jsonify({
            "ok": True,
            "name": "DKInvite REST API",
            "version": "v2",
            "docs": "/api/v2/docs",
            "endpoints": {
                "auth_login": {
                    "method": "POST",
                    "path": "/api/v2/auth/login"
                },
                "auth_me": {
                    "method": "GET",
                    "path": "/api/v2/auth/me"
                },
                "events_list": {
                    "method": "GET",
                    "path": "/api/v2/admin/events"
                },
                "tickets_list": {
                    "method": "GET",
                    "path": "/api/v2/admin/tickets"
                },
                "ticket_get": {
                    "method": "GET",
                    "path": "/api/v2/admin/tickets/<ticket_id>"
                },
                "ticket_create": {
                    "method": "POST",
                    "path": "/api/v2/admin/tickets"
                },
                "ticket_use": {
                    "method": "POST",
                    "path": "/api/v2/admin/tickets/<ticket_id>/use"
                },
                "ticket_reset": {
                    "method": "POST",
                    "path": "/api/v2/admin/tickets/<ticket_id>/reset"
                },
                "scan_lookup": {
                    "method": "GET",
                    "path": "/api/v2/scan/lookup/<ticket_id>"
                },
                "scan_consume": {
                    "method": "POST",
                    "path": "/api/v2/scan/consume"
                }
            }
        }), 200

    @app.get("/api/v2/docs")
    def api_docs():
        return jsonify({
            "ok": True,
            "name": "DKInvite REST API docs",
            "version": "v2",
            "base_url": "https://dkinvite.ru/api/v2",
            "auth": {
                "type": "Bearer JWT",
                "header": "Authorization: Bearer <token>"
            },
            "roles": {
                "admin": [
                    "full access to events",
                    "full access to tickets",
                    "scan lookup/consume",
                    "ticket reset"
                ],
                "controller": [
                    "auth/me",
                    "scan lookup/consume",
                    "ticket lookup by id"
                ]
            },
            "routes": [
                {
                    "method": "POST",
                    "path": "/api/v2/auth/login",
                    "body": {
                        "username": "string",
                        "password": "string"
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/v2/auth/me"
                },
                {
                    "method": "GET",
                    "path": "/api/v2/admin/events"
                },
                {
                    "method": "POST",
                    "path": "/api/v2/admin/events",
                    "body": {
                        "name": "string",
                        "event_date": "YYYY-MM-DD|null"
                    }
                },
                {
                    "method": "GET",
                    "path": "/api/v2/admin/tickets"
                },
                {
                    "method": "GET",
                    "path": "/api/v2/admin/tickets/<ticket_id>"
                },
                {
                    "method": "POST",
                    "path": "/api/v2/admin/tickets",
                    "body": {
                        "event_id": "integer",
                        "owner_name": "string",
                        "seat": "string"
                    }
                },
                {
                    "method": "POST",
                    "path": "/api/v2/admin/tickets/<ticket_id>/use"
                },
                {
                    "method": "POST",
                    "path": "/api/v2/admin/tickets/<ticket_id>/reset"
                },
                {
                    "method": "DELETE",
                    "path": "/api/v2/admin/tickets/<ticket_id>"
                },
                {
                    "method": "GET",
                    "path": "/api/v2/scan/lookup/<ticket_id>"
                },
                {
                    "method": "POST",
                    "path": "/api/v2/scan/consume",
                    "body": {
                        "ticket_id": "string"
                    }
                }
            ],
            "common_errors": [
                {"error": "validation_error", "http_status": 400},
                {"error": "invalid_credentials", "http_status": 401},
                {"error": "not_found", "http_status": 404},
                {"error": "forbidden", "http_status": 403},
                {"error": "already_used", "http_status": 400},
                {"error": "invalid_state", "http_status": 400},
                {"error": "internal_server_error", "http_status": 500}
            ]
        }), 200

    @app.errorhandler(403)
    def handle_403(error):
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": "forbidden",
                "message": "Недостаточно прав",
            }), 403
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def handle_404(error):
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": "not_found",
                "message": "Маршрут не найден",
            }), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def handle_500(error):
        if request.path.startswith("/api/"):
            return jsonify({
                "ok": False,
                "error": "internal_server_error",
                "message": "Внутренняя ошибка сервера",
            }), 500
        return error

    return app
