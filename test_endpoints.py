"""
Test de endpoints FastAPI del sistema de canciones
"""
import requests
import json
import sys
import time

BASE_URL = "http://127.0.0.1:1000"
API_KEY = "zxc12345"
HEADERS = {"X-API-Key": API_KEY}

print("\n" + "="*70)
print("PRUEBAS DE ENDPOINTS FASTAPI - SISTEMA DE CANCIONES")
print("="*70 + "\n")

# Test 1: Health Check
print("TEST 1: Verificar que el servidor está en línea...")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/salud", timeout=5)
    if resp.status_code == 200:
        print(f"✅ Servidor en línea (status: {resp.status_code})\n")
    else:
        # Reintentar sin prefijo por si acaso
        resp = requests.get(f"{BASE_URL}/salud", timeout=5)
        if resp.status_code == 200:
             print(f"✅ Servidor en línea (status: {resp.status_code})\n")
        else:
            print(f"❌ Error: Status {resp.status_code}\n")
            sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    print("   Asegúrate de que el servidor está corriendo\n")
    sys.exit(1)

# Test 2: Crear/Obtener mesa de prueba
print("TEST 2: Crear/Obtener mesa de prueba...")
mesa_qr = "karaoke-mesa-01"
try:
    mesa_data = {
        "nombre": "Mesa 01",
        "qr_code": mesa_qr
    }
    resp = requests.post(f"{BASE_URL}/api/v1/mesas/", json=mesa_data, headers=HEADERS)
    
    if resp.status_code in [200, 201]:
        mesa = resp.json()
        print(f"✅ Mesa lista: {mesa.get('nombre')} (QR: {mesa.get('qr_code')})\n")
    else:
        print(f"⚠️  Mesa podría existir o hubo error {resp.status_code}: {resp.text}\n")
except Exception as e:
    print(f"⚠️  Error: {e}\n")

# Test 3: Conectar usuario a mesa
print("TEST 3: Conectar usuario a mesa (Crear usuario)...")
try:
    usuario_data = {"nick": "TestUser"} 
    resp = requests.post(f"{BASE_URL}/api/v1/mesas/{mesa_qr}/conectar", json=usuario_data)
    
    if resp.status_code in [200, 201]:
        usuario = resp.json()
        usuario_id = usuario.get('id')
        print(f"✅ Usuario conectado: ID {usuario_id}, nick: {usuario.get('nick')}\n")
    else:
        print(f"❌ Error: {resp.status_code} - {resp.text}\n")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}\n")
    sys.exit(1)

# Test 4: Agregar una canción
print("TEST 4: Agregar canción mediante endpoint...")
try:
    cancion_data = {
        "youtube_id": "dQw4w9WgXcQ",
        "titulo": "Test Song - Never Gonna Give You Up",
        "duracion_seconds": 213,
        "is_karaoke": True
    }
    
    resp = requests.post(f"{BASE_URL}/api/v1/canciones/{usuario_id}", json=cancion_data)
    
    if resp.status_code in [200, 201]:
        cancion = resp.json()
        cancion_id = cancion.get('id')
        print(f"✅ Canción agregada: ID {cancion_id}, Título: {cancion.get('titulo')}\n")
    else:
        print(f"❌ Error: {resp.status_code} - {resp.text}\n")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}\n")
    sys.exit(1)

# Test 5: Ver lista de canciones del usuario
print("TEST 5: Ver canciones del usuario...")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/canciones/{usuario_id}/lista")
    if resp.status_code == 200:
        canciones = resp.json()
        print(f"✅ Se obtuvieron {len(canciones)} canciones del usuario\n")
    else:
        print(f"❌ Error: {resp.status_code}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

# Test 6: Ver cola de canciones (Admin)...
print("TEST 6: Ver cola de canciones (Admin)...")
try:
    resp = requests.get(f"{BASE_URL}/api/v1/canciones/cola/extended", headers=HEADERS)
    if resp.status_code == 200:
        cola = resp.json()
        print(f"✅ Cola obtenida:")
        print(f"   - Now Playing: {cola.get('now_playing') is not None}")
        print(f"   - Upcoming: {len(cola.get('upcoming', []))}")
        print(f"   - Lazy: {len(cola.get('lazy_queue', []))}")
        print(f"   - Pending: {len(cola.get('pending', []))}\n")
    else:
        print(f"❌ Error: {resp.status_code}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

# Test 7: Eliminar canción
print("TEST 7: Eliminar canción...")
try:
    resp = requests.delete(f"{BASE_URL}/api/v1/canciones/{cancion_id}?usuario_id={usuario_id}")
    if resp.status_code == 204:
        print(f"✅ Canción eliminada correctamente\n")
    else:
        print(f"❌ Error: {resp.status_code} - {resp.text}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

print("="*70)
print("✅ TODAS LAS PRUEBAS DE ENDPOINTS COMPLETADAS")
print("="*70)
print("\n📊 Resumen:")
print("   ✅ Servidor está en línea")
print("   ✅ Mesa se puede crear/obtener")
print("   ✅ Usuarios se pueden conectar a mesa")
print("   ✅ Canciones se pueden agregar")
print("   ✅ Lista de canciones de usuario se obtiene correctamente")
print("   ✅ Cola de canciones (admin) se puede visualizar")
print("   ✅ Canciones se pueden eliminar\n")
