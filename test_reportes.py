#!/usr/bin/env python3
"""
Script de prueba para validar que los reportes devuelvan datos correctos.
"""
import sys
sys.path.insert(0, '/c/Users/MARCO_MESA/Documents/qr_karaoke_backend_render')

from database import SessionLocal, engine
from sqlalchemy import create_engine
import crud
import admin
import schemas
from fastapi import Depends

# Crear sesión
db = SessionLocal()

try:
    print("=" * 60)
    print("PRUEBA DE REPORTES - Validación de datos")
    print("=" * 60)
    
    # Test 1: Canciones por usuario
    print("\n[1] Probando: Canciones por Usuario")
    print("-" * 60)
    try:
        songs_by_user = crud.get_canciones_cantadas_por_usuario(db)
        print(f"Resultados retornados: {len(songs_by_user)} registros")
        
        if songs_by_user:
            first_row = songs_by_user[0]
            print(f"Tipo de dato: {type(first_row)}")
            print(f"Primer registro: nick={first_row.nick}, canciones_cantadas={first_row.canciones_cantadas}")
            
            # Verificar que los valores no son None
            if first_row.nick is not None and first_row.canciones_cantadas is not None:
                print("✓ EXITOSO: Los valores no son None")
            else:
                print("✗ FALLO: Uno o ambos valores son None")
        else:
            print("⚠ ADVERTENCIA: No hay datos disponibles (lista vacía)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    # Test 2: Canciones por mesa
    print("\n[2] Probando: Canciones por Mesa")
    print("-" * 60)
    try:
        songs_by_table = crud.get_canciones_cantadas_por_mesa(db)
        print(f"Resultados retornados: {len(songs_by_table)} registros")
        
        if songs_by_table:
            first_row = songs_by_table[0]
            print(f"Tipo de dato: {type(first_row)}")
            print(f"Primer registro: nombre={first_row.nombre}, canciones_cantadas={first_row.canciones_cantadas}")
            
            # Verificar que los valores no son None
            if first_row.nombre is not None and first_row.canciones_cantadas is not None:
                print("✓ EXITOSO: Los valores no son None")
            else:
                print("✗ FALLO: Uno o ambos valores son None")
        else:
            print("⚠ ADVERTENCIA: No hay datos disponibles (lista vacía)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    # Test 3: Canciones rechazadas
    print("\n[3] Probando: Canciones Más Rechazadas")
    print("-" * 60)
    try:
        rejected_songs = crud.get_canciones_mas_rechazadas(db, limit=10)
        print(f"Resultados retornados: {len(rejected_songs)} registros")
        
        if rejected_songs:
            first_row = rejected_songs[0]
            print(f"Tipo de dato: {type(first_row)}")
            print(f"Primer registro: titulo={first_row.titulo}, veces_rechazada={first_row.veces_rechazada}")
            
            # Verificar que los valores no son None
            if first_row.titulo is not None and first_row.veces_rechazada is not None:
                print("✓ EXITOSO: Los valores no son None")
            else:
                print("✗ FALLO: Uno o ambos valores son None")
        else:
            print("⚠ ADVERTENCIA: No hay datos disponibles (lista vacía)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    # Test 4: Usuarios rechazados
    print("\n[4] Probando: Usuarios con Canciones Rechazadas")
    print("-" * 60)
    try:
        rejected_users = crud.get_usuarios_mas_rechazados(db, limit=10)
        print(f"Resultados retornados: {len(rejected_users)} registros")
        
        if rejected_users:
            first_row = rejected_users[0]
            print(f"Tipo de dato: {type(first_row)}")
            print(f"Primer registro: nick={first_row.nick}, canciones_rechazadas={first_row.canciones_rechazadas}")
            
            # Verificar que los valores no son None
            if first_row.nick is not None and first_row.canciones_rechazadas is not None:
                print("✓ EXITOSO: Los valores no son None")
            else:
                print("✗ FALLO: Uno o ambos valores son None")
        else:
            print("⚠ ADVERTENCIA: No hay datos disponibles (lista vacía)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    # Test 5: Usuarios sin consumo
    print("\n[5] Probando: Usuarios Inactivos (Sin Consumo)")
    print("-" * 60)
    try:
        inactive_users = crud.get_usuarios_sin_consumo(db)
        print(f"Resultados retornados: {len(inactive_users)} registros")
        
        if inactive_users:
            first_user = inactive_users[0]
            print(f"Tipo de dato: {type(first_user)}")
            print(f"Primer registro: nick={first_user.nick}, mesa_id={first_user.mesa_id}")
            
            # Verificar que tienen mesa_id
            if first_user.nick is not None:
                print("✓ EXITOSO: El usuario tiene nick válido")
            else:
                print("✗ FALLO: El usuario no tiene nick")
        else:
            print("⚠ ADVERTENCIA: No hay datos disponibles (lista vacía)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("RESUMEN: Pruebas completadas")
    print("=" * 60)
    
finally:
    db.close()
