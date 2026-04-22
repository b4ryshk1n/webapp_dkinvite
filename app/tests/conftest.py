from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dkinvite import create_app
from dkinvite.extensions import db
from dkinvite.models import Event, User, UserRole
from dkinvite.utils.security import hash_password


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = 60
    PUBLIC_BASE_URL = "http://localhost:5001"

    _tmpdir = tempfile.mkdtemp(prefix="dkinvite_tests_")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path(_tmpdir) / 'test.sqlite'}"


@pytest.fixture()
def app():
    app = create_app(TestConfig)

    with app.app_context():
        db.drop_all()
        db.create_all()

        admin = User(
            username="admin",
            password_hash=hash_password("dkadmin51"),
            role=UserRole.admin,
            full_name="Admin User",
        )
        control = User(
            username="control",
            password_hash=hash_password("dkcontrol51"),
            role=UserRole.controller,
            full_name="Controller User",
        )
        event = Event(name="Тестовое событие")

        db.session.add_all([admin, control, event])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def event(app):
    with app.app_context():
        return db.session.query(Event).filter_by(name="Тестовое событие").first()


def _login_and_get_token(client, username: str, password: str) -> str:
    response = client.post(
        "/api/v2/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    return payload["data"]["access_token"]


@pytest.fixture()
def admin_token(client):
    return _login_and_get_token(client, "admin", "dkadmin51")


@pytest.fixture()
def controller_token(client):
    return _login_and_get_token(client, "control", "dkcontrol51")


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def controller_headers(controller_token):
    return {"Authorization": f"Bearer {controller_token}"}
