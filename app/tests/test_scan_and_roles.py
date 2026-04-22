def test_controller_can_lookup_and_consume_ticket(client, admin_headers, controller_headers, event):
    created = client.post(
        "/api/v2/admin/tickets",
        headers=admin_headers,
        json={
            "event_id": event.id,
            "owner_name": "Тест Тестов",
            "seat": "Ряд 7 Место 1",
        },
    )
    ticket_id = created.get_json()["data"]["item"]["id"]

    lookup = client.get(
        f"/api/v2/scan/lookup/{ticket_id}",
        headers=controller_headers,
    )
    assert lookup.status_code == 200

    consume = client.post(
        "/api/v2/scan/consume",
        headers=controller_headers,
        json={"ticket_id": ticket_id},
    )
    assert consume.status_code == 200
    assert consume.get_json()["data"]["item"]["status"] == "used"


def test_controller_cannot_list_admin_tickets(client, controller_headers):
    response = client.get("/api/v2/admin/tickets", headers=controller_headers)
    assert response.status_code == 403


def test_scan_consume_unknown_ticket(client, controller_headers):
    response = client.post(
        "/api/v2/scan/consume",
        headers=controller_headers,
        json={"ticket_id": "not-existing-id"},
    )
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "not_found"


def test_scan_consume_requires_ticket_id(client, controller_headers):
    response = client.post(
        "/api/v2/scan/consume",
        headers=controller_headers,
        json={},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "validation_error"
