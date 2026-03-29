"""
User (Usuario) endpoint tests.
Verifies correct 404 responses for non-existent users.
"""


def test_get_unknown_user_returns_404(client):
    """GET /api/v1/usuarios/99999 for a non-existent user must return 404."""
    response = client.get("/api/v1/usuarios/99999")
    assert response.status_code == 404


def test_get_credits_unknown_user_returns_404(client):
    """GET /api/v1/usuarios/99999/song-credits for a non-existent user must return 404."""
    response = client.get("/api/v1/usuarios/99999/song-credits")
    assert response.status_code == 404


def test_get_cuenta_regresiva_unknown_user_returns_404(client):
    """GET /api/v1/usuarios/99999/cuenta-regresiva for a non-existent user must return 404."""
    response = client.get("/api/v1/usuarios/99999/cuenta-regresiva")
    assert response.status_code == 404

