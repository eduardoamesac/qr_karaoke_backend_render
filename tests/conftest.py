import os

# ── Must be set BEFORE any app import ───────────────────────────────────────
# Modules like app/db/database.py and app/core/security.py read these env
# vars at import time.  Setting them here guarantees SQLite is used instead
# of MySQL and that the JWT / API-key secrets are deterministic in tests.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("MASTER_API_KEY", "test-master-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("YOUTUBE_API_KEY", "test-yt-key")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient
from main import app  # imported AFTER env vars are set


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient for the entire test session.
    Entering the context triggers the app lifespan (startup/shutdown).
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    """Valid JWT access token obtained with the master API key.
    Cached for the whole session so login only happens once.
    """
    response = client.post("/api/v1/auth/login", json={"api_key": "test-master-key"})
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]
