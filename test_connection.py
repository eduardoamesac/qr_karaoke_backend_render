#!/usr/bin/env python3
from database_config import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("OK Conectado a Laragon exitosamente")
except Exception as e:
    print(f"ERROR {str(e)}")
