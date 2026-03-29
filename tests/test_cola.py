"""
Song queue (cola) tests.
The queue is stored in a JSON cache — no database rows required.
"""


def test_ver_cola_returns_empty_state(client):
    """GET /api/v1/canciones/cola should return a valid empty queue."""
    response = client.get("/api/v1/canciones/cola")
    assert response.status_code == 200
    data = response.json()
    assert "now_playing" in data
    assert "upcoming" in data
    assert data["now_playing"] is None
    assert data["upcoming"] == []


def test_ver_cola_extended_returns_empty_state(client):
    """GET /api/v1/canciones/cola/extended should return an extended empty queue."""
    response = client.get("/api/v1/canciones/cola/extended")
    assert response.status_code == 200
    data = response.json()
    assert "now_playing" in data
    assert data["now_playing"] is None

