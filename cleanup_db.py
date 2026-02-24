"""
Script para limpiar tablas innecesarias de la BD
"""
import sys
sys.path.insert(0, 'c:\\Users\\MARCO_MESA\\Documents\\qr_karaoke_backend_render')

import os
os.environ["YOUTUBE_API_KEY"] = "test_key"

from database import engine
from sqlalchemy import text

print("Limpiando tablas innecesarias...")

try:
    with engine.connect() as conn:
        # Drop table if exists
        conn.execute(text("DROP TABLE IF EXISTS configuracion_global"))
        conn.commit()
        print("[OK] Tabla configuracion_global eliminada")
except Exception as e:
    print(f"[INFO] {e}")

print("Verificando tablas restantes...")
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tablas en BD: {tables}")

expected = ['admin_api_keys', 'pagos', 'productos', 'usuarios']
for table in expected:
    if table in tables:
        print(f"  [OK] {table}")
    else:
        print(f"  [ERROR] {table} FALTA")
