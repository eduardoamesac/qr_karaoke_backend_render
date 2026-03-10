"""
conftest.py — Fixtures compartidos para los tests de QR Karaoke Backend.

Proporciona:
- Fixture de base de datos en memoria (SQLite) para tests aislados
- Fixture de cliente de test FastAPI (TestClient)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
import models
from database import SessionLocal


# =====================================================
# BASE DE DATOS EN MEMORIA PARA TESTS
# =====================================================

TEST_DATABASE_URL = "sqlite:///./test_karaoke.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Crea las tablas de la base de datos de test al inicio de la sesión
    y las elimina al finalizar.
    """
    models.Base.metadata.create_all(bind=test_engine)
    yield
    models.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db():
    """
    Fixture que proporciona una sesión de base de datos para cada test.
    Hace rollback al finalizar para mantener los tests aislados.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client():
    """
    Fixture que proporciona un TestClient de FastAPI para tests de endpoints.
    """
    with TestClient(main.app) as c:
        yield c
