def test_signup_and_login(client):
    r = client.post(
        "/auth/signup", json={"email": "A@Example.com", "full_name": "Asha", "password": "password123"}
    )
    assert r.status_code == 201
    assert r.json()["email"] == "a@example.com"          # normalised
    assert "hashed_password" not in r.json()              # never leaked

    r = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_duplicate_signup_conflicts(client):
    body = {"email": "a@example.com", "full_name": "Asha", "password": "password123"}
    assert client.post("/auth/signup", json=body).status_code == 201
    assert client.post("/auth/signup", json=body).status_code == 409


def test_signup_validation(client):
    r = client.post("/auth/signup", json={"email": "not-an-email", "full_name": "A", "password": "123"})
    assert r.status_code == 422


def test_login_wrong_password(client, user_headers):
    r = client.post("/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_protected_route_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401