#!/usr/bin/env python3
"""
Test que simula exactamente lo que cada endpoint retorna
"""
import sys
sys.path.insert(0, '/c/Users/MARCO_MESA/Documents/qr_karaoke_backend_render')

from database import SessionLocal
import crud
import schemas
import json
from typing import List

db = SessionLocal()

def simulate_endpoint(func_name, db_func, schema_class, description):
    """Simula un endpoint y muestra exactamente qué retorna"""
    print(f"\n[{description}]")
    print("-" * 80)
    
    try:
        # Llamar la función CRUD
        data = db_func(db)
        print(f"Datos sin procesar: {type(data)}, {len(data)} registros")
        
        if data:
            print(f"Primer Row: {data[0]}")
            print(f"Acceso directo: {data[0]}")
        
        # Procesar según el endpoint específico
        if func_name == "top-songs":
            report = [
                schemas.CancionMasCantada(
                    titulo=titulo,
                    youtube_id=youtube_id,
                    veces_cantada=veces_cantada
                )
                for titulo, youtube_id, veces_cantada in data
            ]
        elif func_name == "songs-by-table":
            report = [
                schemas.ReporteCancionesPorMesa(
                    mesa_nombre=nombre,
                    canciones_cantadas=count
                )
                for nombre, count in data
            ]
        elif func_name == "songs-by-user":
            report = [
                schemas.ReporteCancionesPorUsuario(
                    nick=nick,
                    canciones_cantadas=count
                )
                for nick, count in data
            ]
        elif func_name == "top-rejected-songs":
            report = [
                schemas.ReporteCancionesRechazadas(
                    titulo=titulo,
                    youtube_id=youtube_id,
                    veces_rechazada=veces_rechazada
                )
                for titulo, youtube_id, veces_rechazada in data
            ]
        else:
            report = data
        
        # Convertir a JSON (como haría FastAPI)
        json_data = json.loads(json.dumps([r.dict() for r in report]))
        print(f"\n✓ Convertido a JSON sin errores")
        print(f"Primer elemento JSON:\n{json.dumps(json_data[0], indent=2, ensure_ascii=False)}")
        
        # Verificar valores
        first = json_data[0]
        has_none = any(v is None for v in first.values())
        has_str_undefined = any(v == "undefined" for v in first.values() if isinstance(v, str))
        
        if has_none:
            print("⚠️  PROBLEMA: Contiene None")
        elif has_str_undefined:
            print("⚠️  PROBLEMA: Contiene 'undefined'")
        else:
            print("✓ OK: Todos los valores son válidos")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

try:
    print("=" * 80)
    print("SIMULACIÓN DE ENDPOINTS")
    print("=" * 80)
    
    # Test los que funcionan
    simulate_endpoint(
        "top-songs",
        lambda db: crud.get_canciones_mas_cantadas(db, limit=10),
        schemas.CancionMasCantada,
        "✓ top-songs (FUNCIONA)"
    )
    
    # Test los "arreglados"
    simulate_endpoint(
        "songs-by-table",
        lambda db: crud.get_canciones_cantadas_por_mesa(db),
        schemas.ReporteCancionesPorMesa,
        "❓ songs-by-table (ARREGLÉ - ¿funciona?)"
    )
    
    simulate_endpoint(
        "songs-by-user",
        lambda db: crud.get_canciones_cantadas_por_usuario(db),
        schemas.ReporteCancionesPorUsuario,
        "❓ songs-by-user (ARREGLÉ - ¿funciona?)"
    )
    
    simulate_endpoint(
        "top-rejected-songs",
        lambda db: crud.get_canciones_mas_rechazadas(db, limit=10),
        schemas.ReporteCancionesRechazadas,
        "❓ top-rejected-songs (ARREGLÉ - ¿funciona?)"
    )
    
    print("\n" + "=" * 80)

finally:
    db.close()
