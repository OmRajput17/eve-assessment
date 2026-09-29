import os

# Must be set BEFORE importing the app so settings pick these up.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_EMAILS"] = '["admin@example.com"]'
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def register_and_login(client, email="user@example.com", password="password123") -> dict:
    client.post("/auth/signup", json={"email": email, "full_name": "Test User", "password": password})
    token = client.post("/auth/login", json={"email": email, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(client):
    return register_and_login(client)


@pytest.fixture()
def other_headers(client):
    return register_and_login(client, email="other@example.com")


@pytest.fixture()
def admin_headers(client):
    return register_and_login(client, email="admin@example.com")


@pytest.fixture()
def offering(client, admin_headers) -> dict:
    """A centre that offers one test at 499.00."""
    centre = client.post(
        "/centres", json={"name": "City Labs", "location": "Lucknow"}, headers=admin_headers
    ).json()
    test = client.post("/tests", json={"name": "CBC"}, headers=admin_headers).json()
    client.post(
        f"/centres/{centre['id']}/tests",
        json={"test_id": test["id"], "price": "499.00"},
        headers=admin_headers,
    )
    return {"centre_id": centre["id"], "test_id": test["id"]}


@pytest.fixture()
def booking(client, user_headers, offering) -> dict:
    when = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp = client.post("/bookings/", json={**offering, "appointment_at": when}, headers=user_headers)
    assert resp.status_code == 201
    return resp.json()


def post_webhook(client, payload: dict, secret: str = "test-webhook-secret"):
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/payments/webhook/",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )