#!/usr/bin/env python3
"""
Test de la función get_actividad_por_hora con sintaxis MySQL
"""
import sys
sys.path.insert(0, '.')
from database import SessionLocal
import crud

db = SessionLocal()

try:
    print("Testing get_actividad_por_hora with MySQL HOUR() function...")
    data = crud.get_actividad_por_hora(db)
    print(f"Success! Retrieved {len(data)} hourly records")
    
    if data:
        first = data[0]
        print(f"First record: hora={first[0]}, canciones_cantadas={first[1]}")
        print("OK - No errors with MySQL syntax")
    else:
        print("No data available (empty result, but query executed fine)")
        
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    
finally:
    db.close()
