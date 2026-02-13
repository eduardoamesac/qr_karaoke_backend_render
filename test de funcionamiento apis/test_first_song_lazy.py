#!/usr/bin/env python3
"""
Script para probar el sistema de aprobación automática de la primera canción en cola lazy.
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000/api/v1"

def test_first_song_lazy_approval():
    print("=" * 70)
    print("🧪 TEST: Aprobación Automática de Primera Canción en Cola Lazy")
    print("=" * 70)
    
    # 1. Crear/conectar un usuario
    print("\n1️⃣  Conectando usuario a la mesa...")
    mesa_qr = "karaoke-mesa-01"
    nick = f"TestUser_{int(__import__('time').time())}"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/mesas/{mesa_qr}/conectar",
            json={"nick": nick},
            timeout=10
        )
        if not response.ok:
            print(f"❌ Error al conectar: {response.status_code}")
            print(response.text)
            return False
        
        user_data = response.json()
        usuario_id = user_data['id']
        print(f"✅ Usuario conectado: {user_data['nick']} (ID: {usuario_id})")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False
    
    # 2. Obtener la cola actual
    print("\n2️⃣  Obteniendo estado actual de la cola...")
    try:
        response = requests.get(f"{API_BASE_URL}/canciones/cola/extended", timeout=10)
        if response.ok:
            cola_data = response.json()
            print(f"✅ Cola obtenida:")
            print(f"   - Now Playing: {cola_data.get('now_playing', {}).get('titulo') if cola_data.get('now_playing') else 'Nada'}")
            print(f"   - Upcoming: {len(cola_data.get('upcoming', []))} canciones")
            print(f"   - Lazy Queue: {len(cola_data.get('lazy_queue', []))} canciones")
            print(f"   - Pending: {len(cola_data.get('pending', []))} canciones")
        else:
            print(f"⚠️  No se pudo obtener la cola: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Error al obtener cola: {e}")
    
    # 3. Agregar la primera canción
    print("\n3️⃣  Añadiendo PRIMERA canción...")
    primera_cancion = {
        "youtube_id": "dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up
        "titulo": "TEST - Never Gonna Give You Up (PRIMERA)",
        "duracion_seconds": 212,
        "is_karaoke": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/canciones/{usuario_id}",
            json=primera_cancion,
            timeout=10
        )
        if not response.ok:
            print(f"❌ Error al añadir canción: {response.status_code}")
            print(response.text)
            return False
        
        cancion1_data = response.json()
        cancion1_id = cancion1_data['id']
        cancion1_estado = cancion1_data['estado']
        
        print(f"✅ Primera canción añadida:")
        print(f"   - ID: {cancion1_id}")
        print(f"   - Título: {cancion1_data['titulo']}")
        print(f"   - Estado: {cancion1_estado}")
        print(f"   ✨ ESPERADO: aprobado (sin pendiente_lazy)")
        
        if cancion1_estado == "aprobado":
            print(f"   ✅ CORRECTO: La primera canción está en estado APROBADO")
        elif cancion1_estado == "pendiente_lazy":
            print(f"   ⚠️  ALTERNATIVA: La primera canción está en PENDIENTE_LAZY (también válido)")
        else:
            print(f"   ❌ INCORRECTO: La canción tiene estado {cancion1_estado}")
    except Exception as e:
        print(f"❌ Error al añadir primera canción: {e}")
        return False
    
    # 4. Verificar que aparezca en la lista del usuario
    print("\n4️⃣  Verificando la lista de canciones del usuario...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/canciones/{usuario_id}/lista",
            timeout=10
        )
        if response.ok:
            canciones = response.json()
            print(f"✅ Lista obtenida: {len(canciones)} canción(es)")
            for i, cancion in enumerate(canciones, 1):
                print(f"   {i}. {cancion['titulo']} - Estado: {cancion['estado']}")
                
                # Verificar si tiene flechas
                puede_mover = cancion['estado'] in ['pendiente_lazy', 'aprobado']
                if puede_mover:
                    print(f"      ✅ Flechas disponibles (estado {cancion['estado']})")
                else:
                    print(f"      ❌ Sin flechas (estado {cancion['estado']})")
        else:
            print(f"❌ Error al obtener lista: {response.status_code}")
    except Exception as e:
        print(f"❌ Error al obtener lista: {e}")
    
    # 5. Agregar una segunda canción
    print("\n5️⃣  Añadiendo SEGUNDA canción...")
    segunda_cancion = {
        "youtube_id": "y6120QOlsfU",  # Imagine - John Lennon
        "titulo": "TEST - Imagine (SEGUNDA)",
        "duracion_seconds": 183,
        "is_karaoke": True
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/canciones/{usuario_id}",
            json=segunda_cancion,
            timeout=10
        )
        if not response.ok:
            print(f"❌ Error al añadir segunda canción: {response.status_code}")
            print(response.text)
            return False
        
        cancion2_data = response.json()
        cancion2_id = cancion2_data['id']
        cancion2_estado = cancion2_data['estado']
        
        print(f"✅ Segunda canción añadida:")
        print(f"   - ID: {cancion2_id}")
        print(f"   - Título: {cancion2_data['titulo']}")
        print(f"   - Estado: {cancion2_estado}")
        print(f"   ✨ ESPERADO: pendiente_lazy")
        
        if cancion2_estado == "pendiente_lazy":
            print(f"   ✅ CORRECTO: La segunda canción está en PENDIENTE_LAZY")
        else:
            print(f"   ❌ INCORRECTO: La canción tiene estado {cancion2_estado}")
    except Exception as e:
        print(f"❌ Error al añadir segunda canción: {e}")
        return False
    
    # 6. Verificar lista nuevamente
    print("\n6️⃣  Verificando lista final del usuario...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/canciones/{usuario_id}/lista",
            timeout=10
        )
        if response.ok:
            canciones = response.json()
            print(f"✅ Lista final: {len(canciones)} canción(es)")
            for i, cancion in enumerate(canciones, 1):
                puede_mover = cancion['estado'] in ['pendiente_lazy', 'aprobado']
                flecha_status = "✅ Con flechas" if puede_mover else "❌ Sin flechas"
                print(f"   {i}. {cancion['titulo']}")
                print(f"      Estado: {cancion['estado']} - {flecha_status}")
        else:
            print(f"❌ Error al obtener lista: {response.status_code}")
    except Exception as e:
        print(f"❌ Error al obtener lista final: {e}")
    
    # 7. Probar mover flechas
    print("\n7️⃣  Probando movimiento de canciones...")
    if cancion2_id:
        try:
            print(f"   Intentando mover canción {cancion2_id} hacia arriba...")
            response = requests.post(
                f"{API_BASE_URL}/canciones/{cancion2_id}/mover-arriba?usuario_id={usuario_id}",
                timeout=10
            )
            if response.ok:
                print(f"   ✅ Canción movida hacia arriba")
                moved_cancion = response.json()
                print(f"      Nueva posición (orden_manual): {moved_cancion.get('orden_manual')}")
            else:
                print(f"   ❌ Error al mover: {response.status_code}")
                print(f"      {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETADO")
    print("=" * 70)
    return True

if __name__ == "__main__":
    try:
        success = test_first_song_lazy_approval()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrumpido por el usuario")
        sys.exit(1)
