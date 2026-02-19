#!/usr/bin/env python3
"""
Test interno: Comparar estructura de datos retornada vs schema esperado
"""
import sys
sys.path.insert(0, '/c/Users/MARCO_MESA/Documents/qr_karaoke_backend_render')

from database import SessionLocal
import crud
import schemas
from pydantic import ValidationError

db = SessionLocal()

try:
    print("=" * 80)
    print("ANÁLISIS DETALLADO DE ESTRUCTURA DE DATOS")
    print("=" * 80)
    
    # Test 1: top-songs (QUE FUNCIONA)
    print("\n[REFERENCIA] top-songs (funciona correctamente)")
    print("-" * 80)
    top_songs_data = crud.get_canciones_mas_cantadas(db, limit=1)
    if top_songs_data:
        row = top_songs_data[0]
        print(f"Tipo: {type(row)}")
        print(f"Row.__dict__: {row.__dict__ if hasattr(row, '__dict__') else 'N/A'}")
        print(f"Acceso por índice: row[0]={row[0]}, row[1]={row[1]}, row[2]={row[2]}")
        print(f"Acceso por atributo: row.titulo={row.titulo}, row.youtube_id={row.youtube_id}, row.veces_cantada={row.veces_cantada}")
        
        # Intentar desempaquetar como en el código actual
        try:
            titulo, youtube_id, veces_cantada = row
            print(f"✓ Desempaquetamiento: titulo={titulo}, youtube_id={youtube_id}, veces_cantada={veces_cantada}")
            
            # Crear schema
            schema_obj = schemas.CancionMasCantada(
                titulo=titulo,
                youtube_id=youtube_id,
                veces_cantada=veces_cantada
            )
            print(f"✓ Schema válido: {schema_obj}")
        except ValueError as e:
            print(f"✗ Error desempaquetando: {e}")
    
    # Test 2: songs-by-table (QUE NO FUNCIONA)
    print("\n[PROBLEMA] songs-by-table (devuelve undefined)")
    print("-" * 80)
    songs_by_table = crud.get_canciones_cantadas_por_mesa(db)
    if songs_by_table:
        row = songs_by_table[0]
        print(f"Tipo: {type(row)}")
        print(f"Row.keys(): {row.keys() if hasattr(row, 'keys') else 'N/A'}")
        print(f"Acceso por índice: row[0]={row[0]}, row[1]={row[1]}")
        
        # Verificar qué atributos tiene
        print(f"\nIntentos de acceso por atributo:")
        attrs_to_try = ['nombre', 'mesa_nombre', 'canciones_cantadas', 0, 1]
        for attr in attrs_to_try:
            try:
                val = row[attr] if isinstance(attr, int) else getattr(row, attr, "NO EXISTE")
                print(f"  row.{attr if not isinstance(attr, int) else f'[{attr}]'} = {val}")
            except Exception as e:
                print(f"  row.{attr if not isinstance(attr, int) else f'[{attr}]'} = ERROR: {e}")
        
        # Intentar desempaquetar (cómo funciona top-songs)
        try:
            col1, col2 = row
            print(f"\n✓ Desempaquetamiento directo: col1={col1}, col2={col2}")
        except ValueError as e:
            print(f"\n✗ Error desempaquetando: {e}")
        
        # Intentar acceso por row.nombre y row.canciones_cantadas
        print(f"\nIntento con row.nombre y row.canciones_cantadas:")
        try:
            mesa_name = row.nombre
            count = row.canciones_cantadas
            print(f"  row.nombre = {mesa_name}")
            print(f"  row.canciones_cantadas = {count}")
            
            # Crear schema con lo que obtuvimos
            schema_obj = schemas.ReporteCancionesPorMesa(
                mesa_nombre=mesa_name,
                canciones_cantadas=count
            )
            print(f"  ✓ Schema válido: {schema_obj}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Test 3: songs-by-user (QUE DEBERÍA FUNCIONAR DESPUÉS DE MI ARREGLO)
    print("\n[ARREGLADO] songs-by-user ¿funciona?")
    print("-" * 80)
    songs_by_user = crud.get_canciones_cantadas_por_usuario(db)
    if songs_by_user:
        row = songs_by_user[0]
        print(f"Tipo: {type(row)}")
        print(f"Keys: {list(row.keys()) if hasattr(row, 'keys') else 'N/A'}")
        print(f"Acceso por índice: row[0]={row[0]}, row[1]={row[1]}")
        
        # Intentar desempaquetar
        try:
            col1, col2 = row
            print(f"✓ Desempaquetamiento: col1={col1}, col2={col2}")
            
            schema_obj = schemas.ReporteCancionesPorUsuario(
                nick=col1,
                canciones_cantadas=col2
            )
            print(f"✓ Schema válido: {schema_obj}")
        except Exception as e:
            print(f"✗ Desempaquetamiento: {e}")
        
        # Intentar acceso por atributo
        print(f"\nIntento con row.nick y row.canciones_cantadas:")
        try:
            nick_val = row.nick
            count_val = row.canciones_cantadas
            print(f"  row.nick = {nick_val}")
            print(f"  row.canciones_cantadas = {count_val}")
            
            schema_obj = schemas.ReporteCancionesPorUsuario(
                nick=nick_val,
                canciones_cantadas=count_val
            )
            print(f"  ✓ Schema válido: {schema_obj}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("RESUMEN Y RECOMENDACIÓN")
    print("=" * 80)
    
finally:
    db.close()
