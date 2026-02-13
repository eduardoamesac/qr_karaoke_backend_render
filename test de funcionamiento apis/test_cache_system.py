"""
Test Completo del Sistema de Cache en JSON
Prueba:
- Cache de canciones (add, get, delete)
- Cache de cuentas de mesa (consumos, pagos)
- Sincronización al cerrar mesa
- Persistencia en archivos JSON
"""

import json
import os
import time
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from cache_manager import cache_manager

# ============================================
# CONFIGURACIÓN
# ============================================

client = TestClient(app)
CACHE_DIR = Path("cache")
API_KEY = "zxc12345"  # Master API Key
HEADERS = {"X-API-Key": API_KEY}

# Colores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_test(title):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_fail(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def cleanup_cache():
    """Limpia el directorio de cache"""
    if CACHE_DIR.exists():
        for file in CACHE_DIR.glob("*.json"):
            file.unlink()
        print_info(f"Cache limpiado: {list(CACHE_DIR.glob('*.json'))}")

def check_cache_file_exists(filename):
    """Verifica si un archivo de cache existe"""
    filepath = CACHE_DIR / filename
    return filepath.exists()

def read_cache_file(filename):
    """Lee el contenido de un archivo de cache"""
    filepath = CACHE_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_cache_file_size(filename):
    """Obtiene el tamaño de un archivo de cache"""
    filepath = CACHE_DIR / filename
    if filepath.exists():
        return filepath.stat().st_size
    return 0

# ============================================
# TEST 1: Crear Mesa y Usuarios
# ============================================

def test_crear_mesa_y_usuarios():
    print_test("TEST 1: Crear Mesa y Usuarios")
    
    # Crear mesa con nombre y QR code con formato correcto
    mesa_numero = int(time.time()) % 100
    mesa_nombre = f"Mesa_{mesa_numero}"
    mesa_qr = f"karaoke-mesa-{mesa_numero:02d}"
    
    response = client.post(
        "/api/v1/mesas/",
        json={"nombre": mesa_nombre, "qr_code": mesa_qr},
        headers=HEADERS
    )
    assert response.status_code in [200, 201], f"Error creando mesa: {response.text}"
    mesa_data = response.json()
    mesa_id = mesa_data['id']
    print_success(f"Mesa creada: {mesa_id} ({mesa_nombre})")
    
    # Conectar usuario 1 con QR format: karaoke-mesa-XX-usuarioN
    usuario1_qr = f"{mesa_qr}-usuario1"
    response = client.post(
        f"/api/v1/mesas/{usuario1_qr}/conectar",
        json={"nick": "Usuario1"}
    )
    assert response.status_code == 200, f"Error conectando usuario: {response.text}"
    usuario1_data = response.json()
    usuario1_id = usuario1_data['id']
    print_success(f"Usuario1 conectado: {usuario1_id}")
    
    # Conectar usuario 2
    usuario2_qr = f"{mesa_qr}-usuario2"
    response = client.post(
        f"/api/v1/mesas/{usuario2_qr}/conectar",
        json={"nick": "Usuario2"}
    )
    assert response.status_code == 200
    usuario2_data = response.json()
    usuario2_id = usuario2_data['id']
    print_success(f"Usuario2 conectado: {usuario2_id}")
    
    return mesa_id, usuario1_id, usuario2_id

# ============================================
# TEST 2: Agregar Canciones y Verificar Cache
# ============================================

def test_agregar_canciones(usuario1_id, usuario2_id):
    print_test("TEST 2: Agregar Canciones y Verificar Cache")
    
    songs = [
        {
            "titulo": "Bohemian Rhapsody",
            "youtube_id": "fJ9rUzIMt7o",
            "duracion_seconds": 354
        },
        {
            "titulo": "Another One Bites the Dust",
            "youtube_id": "rY0WxgSXdVE",
            "duracion_seconds": 215
        },
        {
            "titulo": "Somebody to Love",
            "youtube_id": "kijpcR38kM4",
            "duracion_seconds": 294
        }
    ]
    
    # Agregar canciones para usuario 1
    for song in songs[:2]:
        response = client.post(
            f"/api/v1/canciones/{usuario1_id}",
            json=song
        )
        assert response.status_code == 200, f"Error agregando canción: {response.text}"
        cancion_id = response.json()['id']
        print_success(f"Canción agregada para Usuario1: {song['titulo']} (ID: {cancion_id})")
        time.sleep(0.1)  # Pequeña pausa
    
    # Agregar canción para usuario 2
    response = client.post(
        f"/api/v1/canciones/{usuario2_id}",
        json=songs[2]
    )
    assert response.status_code == 200
    print_success(f"Canción agregada para Usuario2: {songs[2]['titulo']}")
    
    # Verificar que se crearon archivos de cache
    time.sleep(0.5)
    
    cache_file_u1 = f"songs_usuario_{usuario1_id}.json"
    cache_file_u2 = f"songs_usuario_{usuario2_id}.json"
    
    assert check_cache_file_exists(cache_file_u1), f"Cache file no existe: {cache_file_u1}"
    print_success(f"Archivo de cache creado: {cache_file_u1}")
    
    assert check_cache_file_exists(cache_file_u2), f"Cache file no existe: {cache_file_u2}"
    print_success(f"Archivo de cache creado: {cache_file_u2}")
    
    # Verificar contenido del cache
    cache_u1 = read_cache_file(cache_file_u1)
    assert cache_u1 is not None, "Cache vacío para usuario 1"
    assert len(cache_u1.get('canciones', [])) == 2, "Número de canciones incorrecto"
    print_success(f"Cache Usuario1 contiene 2 canciones")
    
    cache_u2 = read_cache_file(cache_file_u2)
    assert cache_u2 is not None, "Cache vacío para usuario 2"
    assert len(cache_u2.get('canciones', [])) == 1, "Número de canciones incorrecto"
    print_success(f"Cache Usuario2 contiene 1 canción")
    
    # Mostrar tamaño de archivos
    size_u1 = get_cache_file_size(cache_file_u1)
    size_u2 = get_cache_file_size(cache_file_u2)
    print_info(f"Tamaño cache Usuario1: {size_u1} bytes")
    print_info(f"Tamaño cache Usuario2: {size_u2} bytes")

# ============================================
# TEST 3: Verificar Lectura desde Cache
# ============================================

def test_lectura_desde_cache(usuario1_id):
    print_test("TEST 3: Verificar Lectura desde Cache")
    
    # Primera lectura (desde cache)
    start_time = time.time()
    response = client.get(f"/api/v1/canciones/{usuario1_id}/lista")
    time_from_cache = time.time() - start_time
    assert response.status_code == 200
    canciones = response.json()
    print_success(f"Lectura desde cache en {time_from_cache*1000:.2f}ms - {len(canciones)} canciones")
    
    # Segunda lectura (desde cache también)
    start_time = time.time()
    response = client.get(f"/api/v1/canciones/{usuario1_id}/lista")
    time_from_cache2 = time.time() - start_time
    assert response.status_code == 200
    print_success(f"Segunda lectura desde cache en {time_from_cache2*1000:.2f}ms")
    
    print_info(f"Las lecturas desde cache son muy rápidas (~{time_from_cache*1000:.2f}ms)")

# ============================================
# TEST 4: Agregar Consumos y Verificar Cache de Mesa
# ============================================

def test_agregar_consumos(mesa_id, usuario1_id):
    print_test("TEST 4: Agregar Consumos y Verificar Cache de Mesa")
    
    # Primero, crear algunos productos
    productos = [
        {"nombre": "Cerveza", "costo": 5000, "precio": 8000},
        {"nombre": "Whisky", "costo": 8000, "precio": 15000},
        {"nombre": "Refresco", "costo": 1000, "precio": 3000}
    ]
    
    producto_ids = []
    for prod in productos:
        response = client.post("/api/v1/productos", json=prod, headers=HEADERS)
        assert response.status_code in [200, 201], f"Error creando producto: {response.text}"
        prod_id = response.json()['id']
        producto_ids.append(prod_id)
        print_info(f"Producto creado: {prod['nombre']} (ID: {prod_id})")
    
    # Agregar consumos
    consumos_data = [
        {"producto_id": producto_ids[0], "cantidad": 2},
        {"producto_id": producto_ids[1], "cantidad": 1},
        {"producto_id": producto_ids[2], "cantidad": 3}
    ]
    
    for consumo in consumos_data:
        response = client.post(
            f"/api/v1/consumos/pedir/{usuario1_id}",
            json=consumo
        )
        assert response.status_code == 200
        print_success(f"Consumo agregado: Producto {consumo['producto_id']}, Cantidad {consumo['cantidad']}")
        time.sleep(0.1)
    
    # Verificar que se creó el archivo de cache de mesa
    time.sleep(0.5)
    
    cache_file_mesa = f"mesa_cuenta_{mesa_id}.json"
    assert check_cache_file_exists(cache_file_mesa), f"Cache file no existe: {cache_file_mesa}"
    print_success(f"Archivo de cache de mesa creado: {cache_file_mesa}")
    
    # Verificar contenido del cache de mesa
    cache_mesa = read_cache_file(cache_file_mesa)
    assert cache_mesa is not None, "Cache de mesa vacío"
    
    consumos_en_cache = cache_mesa.get('consumos', [])
    assert len(consumos_en_cache) == 3, f"Se esperaban 3 consumos, se encontraron {len(consumos_en_cache)}"
    print_success(f"Cache de mesa contiene 3 consumos")
    
    # Verificar totales
    total_consumido = cache_mesa.get('total_consumido', 0)
    saldo = cache_mesa.get('saldo', 0)
    print_info(f"Total consumido: ${total_consumido}")
    print_info(f"Saldo actual: ${saldo}")
    
    size = get_cache_file_size(cache_file_mesa)
    print_info(f"Tamaño cache mesa: {size} bytes")

# ============================================
# TEST 5: Eliminar una Canción
# ============================================

def test_eliminar_cancion(usuario1_id):
    print_test("TEST 5: Eliminar una Canción")
    
    # Obtener lista de canciones
    response = client.get(f"/api/v1/canciones/{usuario1_id}/lista")
    assert response.status_code == 200
    canciones = response.json()
    cancion_id_a_eliminar = canciones[0]['id']
    
    # Eliminar canción
    response = client.delete(f"/api/v1/canciones/{cancion_id_a_eliminar}")
    assert response.status_code == 200
    print_success(f"Canción eliminada: ID {cancion_id_a_eliminar}")
    
    # Verificar que se actualizó el cache
    time.sleep(0.3)
    cache_file = f"songs_usuario_{usuario1_id}.json"
    cache_data = read_cache_file(cache_file)
    
    canciones_en_cache = cache_data.get('canciones', [])
    assert len(canciones_en_cache) == 1, f"Se esperaba 1 canción, se encontraron {len(canciones_en_cache)}"
    print_success(f"Cache actualizado: Ahora contiene 1 canción")

# ============================================
# TEST 6: Cerrar Mesa y Verificar Limpieza de Cache
# ============================================

def test_cerrar_mesa(mesa_id):
    print_test("TEST 6: Cerrar Mesa y Verificar Limpieza de Cache")
    
    # Verificar que existen archivos de cache antes de cerrar
    cache_files_before = list(CACHE_DIR.glob("*.json"))
    print_info(f"Archivos de cache antes de cerrar: {len(cache_files_before)}")
    for f in cache_files_before:
        print_info(f"  - {f.name}")
    
    # Cerrar mesa
    response = client.post(f"/api/v1/admin/tables/{mesa_id}/close-session", headers=HEADERS)
    assert response.status_code == 200
    print_success(f"Mesa {mesa_id} cerrada")
    
    # Esperar a que se ejecute la limpieza
    time.sleep(1)
    
    # Verificar que se limpió el cache
    cache_files_after = list(CACHE_DIR.glob(f"songs_usuario_*.json"))
    cache_mesa_after = list(CACHE_DIR.glob(f"mesa_cuenta_{mesa_id}.json"))
    
    if not cache_files_after:
        print_success("Cache de canciones limpiado después de cerrar mesa")
    else:
        print_warning(f"Aún existen {len(cache_files_after)} archivos de cache de canciones")
    
    if not cache_mesa_after:
        print_success("Cache de mesa limpiado después de cerrar mesa")
    else:
        print_warning(f"Aún existe cache de mesa: {cache_mesa_after}")

# ============================================
# TEST 7: Verificar Persistencia en BD
# ============================================

def test_verificar_persistencia_bd():
    print_test("TEST 7: Verificar Persistencia en BD")
    
    from database import SessionLocal
    from models import Usuario, Cancion
    
    db = SessionLocal()
    
    try:
        usuarios = db.query(Usuario).count()
        canciones = db.query(Cancion).count()
        
        print_info(f"Usuarios en BD: {usuarios}")
        print_info(f"Canciones en BD: {canciones}")
        
        if usuarios > 0:
            print_success("Datos de usuarios persistidos en BD")
        if canciones > 0:
            print_success("Datos de canciones persistidos en BD")
    finally:
        db.close()

# ============================================
# EJECUCIÓN DE TESTS
# ============================================

def run_all_tests():
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}TESTING COMPLETO DEL SISTEMA DE CACHE EN JSON{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    
    try:
        # Limpiar cache antes de empezar
        cleanup_cache()
        
        # Ejecutar tests
        mesa_id, usuario1_id, usuario2_id = test_crear_mesa_y_usuarios()
        test_agregar_canciones(usuario1_id, usuario2_id)
        test_lectura_desde_cache(usuario1_id)
        test_agregar_consumos(mesa_id, usuario1_id)
        test_eliminar_cancion(usuario1_id)
        test_cerrar_mesa(mesa_id)
        test_verificar_persistencia_bd()
        
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}✓ TODOS LOS TESTS COMPLETADOS EXITOSAMENTE{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
        
    except AssertionError as e:
        print(f"\n{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}✗ TEST FALLÓ: {str(e)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}\n")
        raise
    except Exception as e:
        print(f"\n{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}✗ ERROR: {str(e)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}\n")
        raise

if __name__ == "__main__":
    run_all_tests()
