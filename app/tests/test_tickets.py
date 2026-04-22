def test_admin_can_create_ticket(client, admin_headers, event):
    response = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "иванов иван иванович",
            "seat": "1/2",
        },
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    data = response.get_json()
    assert data["ok"] is True
    assert data["data"]["item"]["owner_name"] == "Иванов Иван Иванович"
    assert data["data"]["item"]["seat"] == "Ряд 1 Место 2"
    assert data["data"]["item"]["status"] == "active"


def test_duplicate_seat_is_blocked(client, admin_headers, event):
    first = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "Петров Петр",
            "seat": "Ряд 2 Место 3",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "Сидоров Сидор",
            "seat": "Ряд 2 Место 3",
        },
    )
    assert second.status_code == 400
    data = second.get_json()
    assert data["ok"] is False
    assert data["error"] == "validation_error"


def test_controller_cannot_create_ticket(client, controller_headers, event):
    response = client.post(
        "/api/v2/admin/tickets",
        headers=controller_headers,
        json={
            "event_id": event.id,
            "owner_name": "Иванов Иван",
            "seat": "Ряд 3 Место 1",
        },
    )
    assert response.status_code == 403


def test_admin_can_use_and_reset_ticket(client, admin_headers, event):
    created = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "Иванов Иван",
            "seat": "Ряд 4 Место 1",
        },
    )
    ticket_id = created.get_json()["data"]["item"]["id"]

    used = client.post(
        f"/api/v2/admin/tickets/{ticket_id}/use",
        headers=admin_headers,
    )
    assert used.status_code == 200
    assert used.get_json()["data"]["item"]["status"] == "used"

    reset = client.post(
        f"/api/v2/admin/tickets/{ticket_id}/reset",
        headers=admin_headers,
    )
    assert reset.status_code == 200
    assert reset.get_json()["data"]["item"]["status"] == "active"


def test_reset_active_ticket_is_blocked(client, admin_headers, event):
    created = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "Иванов Иван",
            "seat": "Ряд 5 Место 1",
        },
    )
    ticket_id = created.get_json()["data"]["item"]["id"]

    reset = client.post(
        f"/api/v2/admin/tickets/{ticket_id}/reset",
        headers=admin_headers,
    )
    assert reset.status_code == 400
    data = reset.get_json()
    assert data["error"] == "invalid_state"


def test_repeat_use_is_blocked(client, admin_headers, event):
    created = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "Иванов Иван",
            "seat": "Ряд 6 Место 1",
        },
    )
    ticket_id = created.get_json()["data"]["item"]["id"]

    first = client.post(
        f"/api/v2/admin/tickets/{ticket_id}/use",
        headers=admin_headers,
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v2/admin/tickets/{ticket_id}/use",
        headers=admin_headers,
    )
    assert second.status_code == 400
    data = second.get_json()
    assert data["error"] == "invalid_state"
