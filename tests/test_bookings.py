from datetime import UTC, datetime, timedelta


def test_create_booking_uses_server_side_price(client, user_headers, offering):
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    r = client.post(
        "/bookings/",
        json={**offering, "appointment_at": when, "amount": "1.00"},  # client-sent amount is ignored
        headers=user_headers,
    )
    assert r.status_code == 201
    assert r.json()["amount"] == "499.00"
    assert r.json()["status"] == "PENDING"


def test_booking_requires_auth(client, offering):
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert client.post("/bookings/", json={**offering, "appointment_at": when}).status_code == 401


def test_past_appointment_rejected(client, user_headers, offering):
    when = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    r = client.post("/bookings/", json={**offering, "appointment_at": when}, headers=user_headers)
    assert r.status_code == 422


def test_centre_not_offering_test_is_404(client, user_headers, offering):
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    r = client.post(
        "/bookings/",
        json={"centre_id": offering["centre_id"], "test_id": 9999, "appointment_at": when},
        headers=user_headers,
    )
    assert r.status_code == 404


def test_cannot_see_or_cancel_someone_elses_booking(client, booking, other_headers):
    assert client.get(f"/bookings/{booking['id']}", headers=other_headers).status_code == 404
    assert client.post(f"/bookings/{booking['id']}/cancel", headers=other_headers).status_code == 404


def test_invalid_booking_id(client, user_headers):
    assert client.get("/bookings/99999", headers=user_headers).status_code == 404
    assert client.get("/bookings/abc", headers=user_headers).status_code == 422


def test_non_admin_cannot_create_centre(client, user_headers):
    r = client.post("/centres", json={"name": "X Labs", "location": "Delhi"}, headers=user_headers)
    assert r.status_code == 403


def test_cancel_booking_then_cannot_pay(client, booking, user_headers):
    assert client.post(f"/bookings/{booking['id']}/cancel", headers=user_headers).json()["status"] == "CANCELLED"
    r = client.post("/payments/", json={"booking_id": booking["id"]}, headers=user_headers)
    assert r.status_code == 409