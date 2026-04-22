def test_login_admin_success(client):
    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "dkadmin51"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["data"]["user"]["username"] == "admin"
    assert data["data"]["user"]["role"] == "admin"
    assert data["data"]["access_token"]


def test_login_invalid_password(client):
    response = client.post(
        "/api/v2/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data["ok"] is False
    assert data["error"] == "invalid_credentials"


def test_me_requires_auth(client):
    response = client.get("/api/v2/auth/me")
    assert response.status_code == 401


def test_me_admin_success(client, admin_headers):
    response = client.get("/api/v2/auth/me", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["data"]["user"]["username"] == "admin"
