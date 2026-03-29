"""
Health-check and static-page tests.
No authentication or external services required.
"""


def test_health_check_returns_ok(client):
    """GET /salud should return 200 with {"status": "ok"}."""
    response = client.get("/salud")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend(client):
    """GET / should serve the user-facing HTML page (200)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_admin_page_is_served(client):
    """GET /admin should serve the admin login HTML page (200)."""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_player_page_is_served(client):
    """GET /player should serve the karaoke projector/player HTML page (200)."""
    response = client.get("/player")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

