from tests.conftest import post_webhook


def pay(client, headers, booking_id, **extra):
    return client.post("/payments/", json={"booking_id": booking_id, **extra}, headers=headers)


def test_successful_payment_confirms_booking(client, booking, user_headers):
    r = pay(client, user_headers, booking["id"], force_status="SUCCESS")
    assert r.status_code == 201
    assert r.json()["status"] == "SUCCESS"
    assert r.json()["booking_status"] == "CONFIRMED"


def test_failed_payment_marks_booking_failed_then_retry_succeeds(client, booking, user_headers):
    assert pay(client, user_headers, booking["id"], force_status="FAILED").json()["booking_status"] == "FAILED"
    retry = pay(client, user_headers, booking["id"], force_status="SUCCESS")
    assert retry.json()["booking_status"] == "CONFIRMED"


def test_cannot_pay_confirmed_booking_twice(client, booking, user_headers):
    pay(client, user_headers, booking["id"], force_status="SUCCESS")
    assert pay(client, user_headers, booking["id"]).status_code == 409


def test_cannot_pay_someone_elses_booking(client, booking, other_headers):
    assert pay(client, other_headers, booking["id"]).status_code == 404


def test_payment_requires_auth(client, booking):
    assert client.post("/payments/", json={"booking_id": booking["id"]}).status_code == 401


# ------------------------------- webhook -------------------------------------
def start_async_payment(client, headers, booking_id) -> str:
    return pay(client, headers, booking_id, async_mode=True).json()["provider_reference"]


def test_webhook_confirms_booking(client, booking, user_headers):
    ref = start_async_payment(client, user_headers, booking["id"])
    r = post_webhook(client, {"event_id": "evt_1", "provider_reference": ref, "status": "SUCCESS"})
    assert r.status_code == 200 and r.json()["outcome"] == "processed"
    assert client.get(f"/bookings/{booking['id']}", headers=user_headers).json()["status"] == "CONFIRMED"


def test_webhook_is_idempotent(client, booking, user_headers):
    ref = start_async_payment(client, user_headers, booking["id"])
    event = {"event_id": "evt_dup", "provider_reference": ref, "status": "SUCCESS"}

    outcomes = [post_webhook(client, event).json()["outcome"] for _ in range(3)]

    assert outcomes == ["processed", "duplicate", "duplicate"]
    assert client.get(f"/bookings/{booking['id']}", headers=user_headers).json()["status"] == "CONFIRMED"


def test_late_failed_event_does_not_downgrade_success(client, booking, user_headers):
    ref = start_async_payment(client, user_headers, booking["id"])
    post_webhook(client, {"event_id": "e1", "provider_reference": ref, "status": "SUCCESS"})
    r = post_webhook(client, {"event_id": "e2", "provider_reference": ref, "status": "FAILED"})
    assert r.json()["outcome"] == "ignored"
    assert client.get(f"/bookings/{booking['id']}", headers=user_headers).json()["status"] == "CONFIRMED"


def test_webhook_rejects_bad_signature(client, booking, user_headers):
    ref = start_async_payment(client, user_headers, booking["id"])
    r = post_webhook(
        client, {"event_id": "e1", "provider_reference": ref, "status": "SUCCESS"}, secret="wrong"
    )
    assert r.status_code == 401


def test_webhook_unknown_reference_is_404_and_retryable(client):
    r = post_webhook(client, {"event_id": "e1", "provider_reference": "nope", "status": "SUCCESS"})
    assert r.status_code == 404


def test_webhook_invalid_payload(client):
    assert post_webhook(client, {"event_id": "e1", "status": "MAYBE"}).status_code == 422