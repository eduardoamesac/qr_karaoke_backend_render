"""
Script de prueba del sistema - Verificar endpoints básicos
"""
import sys
sys.path.insert(0, 'c:\\Users\\MARCO_MESA\\Documents\\qr_karaoke_backend_render')

import os
os.environ["YOUTUBE_API_KEY"] = "test_key"

from fastapi.testclient import TestClient
import main

# Crear cliente de prueba
client = TestClient(main.app)

print("=" * 60)
print("PRUEBAS DEL SISTEMA - QR KARAOKE")
print("=" * 60)

# Test 1: Health Check
print("\n[TEST 1] Health Check")
try:
    response = client.get("/salud")
    if response.status_code == 200:
        print("  [OK] GET /salud -> 200")
        print(f"  Response: {response.json()}")
    else:
        print(f"  [ERROR] Status: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 2: OpenAPI Schema
print("\n[TEST 2] OpenAPI Schema")
try:
    response = client.get("/openapi.json")
    if response.status_code == 200:
        print("  [OK] GET /openapi.json -> 200")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 3: Usuarios API
print("\n[TEST 3] Usuarios API")
try:
    response = client.get("/api/v1/usuarios")
    print(f"  [OK] GET /api/v1/usuarios -> {response.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 4: Productos API
print("\n[TEST 4] Productos API")
try:
    response = client.get("/api/v1/productos")
    print(f"  [OK] GET /api/v1/productos -> {response.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

# Test 5: Verificar bases de datos
print("\n[TEST 5] Verificar tablas de BD")
try:
    from models import Usuario, Producto, Pago, AdminApiKey
    from database import engine
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"  Tablas en BD: {tables}")
    expected = ['admin_api_keys', 'pagos', 'productos', 'usuarios']
    
    for table in expected:
        if table in tables:
            print(f"    [OK] {table}")
        else:
            print(f"    [ERROR] {table} FALTA")
    
    extra = [t for t in tables if t not in expected]
    if extra:
        print(f"    [WARNING] Tablas extra encontradas: {extra}")
    
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()

# Test 6: Verificar cache
print("\n[TEST 6] Verificar Cache Manager")
try:
    from cache_manager import cache_manager
    print(f"  [OK] Cache manager importado")
    print(f"  Canciones en cache: {len(cache_manager.get_all_songs())}")
    print(f"  Mesas en cache: {len(cache_manager.get_all_mesas())}")
    print(f"  Consumos en cache: {len(cache_manager.get_all_consumos())}")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n" + "=" * 60)
print("PRUEBAS COMPLETADAS")
print("=" * 60)
