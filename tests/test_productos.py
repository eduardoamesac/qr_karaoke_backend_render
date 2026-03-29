"""
Product (Producto) CRUD tests.
Products are stored in the SQL database (SQLite in tests).
Tests run in definition order — create comes before list-after-create.
"""


def test_list_products_returns_empty_on_fresh_db(client):
    """GET /api/v1/productos/ on a fresh DB must return an empty list."""
    response = client.get("/api/v1/productos/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_product_requires_auth(client):
    """POST /api/v1/productos/ without a token must be rejected (401 or 403)."""
    response = client.post(
        "/api/v1/productos/",
        json={"nombre": "Unauthorized Beer", "categoria": "Bebidas", "valor": "5.00", "stock": 1},
    )
    assert response.status_code in (401, 403)


def test_create_product_with_admin_token(client, admin_token):
    """POST /api/v1/productos/ with a valid token must create and return the product."""
    payload = {
        "nombre": "Test Beer",
        "categoria": "Bebidas",
        "valor": "5.00",
        "costo": "2.00",
        "stock": 10,
        "is_active": True,
    }
    response = client.post(
        "/api/v1/productos/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "Test Beer"
    assert data["categoria"] == "Bebidas"
    assert data["stock"] == 10


def test_list_products_as_admin_includes_created(client, admin_token):
    """GET /api/v1/productos/ as admin must include the product created above."""
    response = client.get(
        "/api/v1/productos/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    productos = response.json()
    assert isinstance(productos, list)
    names = [p["nombre"] for p in productos]
    assert "Test Beer" in names

