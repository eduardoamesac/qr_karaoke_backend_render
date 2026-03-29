"""
Admin authentication tests.
Covers: login with master API key, login with wrong key, and
JWT-protected endpoint access.
"""


def test_login_master_key_returns_tokens(client):
    """POST /api/v1/auth/login with the master key must return access + refresh tokens."""
    response = client.post("/api/v1/auth/login", json={"api_key": "test-master-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_key_is_rejected(client):
    """POST /api/v1/auth/login with a wrong key must return 403."""
    response = client.post("/api/v1/auth/login", json={"api_key": "totally-wrong-key"})
    assert response.status_code == 403


def test_protected_endpoint_without_token_is_rejected(client):
    """Accessing a protected endpoint without a Bearer token must return 401 or 403."""
    response = client.get("/api/v1/mesas/")
    assert response.status_code in (401, 403)


def test_protected_endpoint_with_valid_token(client, admin_token):
    """Accessing a protected endpoint with a valid JWT token must return 200."""
    response = client.get(
        "/api/v1/mesas/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

