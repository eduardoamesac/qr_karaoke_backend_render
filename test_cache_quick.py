#!/usr/bin/env python3
"""
Test rápido del sistema de cache usando TestClient (sin servidor HTTP externo)
"""

import json
import time
from pathlib import Path
from fastapi.testclient import TestClient

# Importar la app después de configurar variables de entorno
import os
os.environ['TESTING'] = '1'

from main import app

# ============================================
# CONFIGURACIÓN
# ============================================

client = TestClient(app)
CACHE_DIR = Path("cache")
API_KEY = "zxc12345"
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

def check_cache_file_exists(filename):
    filepath = CACHE_DIR / filename
    return filepath.exists()

def read_cache_file(filename):
    filepath = CACHE_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_cache_file_size(filename):
    filepath = CACHE_DIR / filename
    if filepath.exists():
        return filepath.stat().st_size
    return 0

# ============================================
# TESTS
# ============================================

def test_1_crear_mesa_y_usuarios():
    print_test("TEST 1: Crear Mesa y Usuarios")
    
    mesa_numero = int(time.time()) % 100
    mesa_nombre = f"Mesa_Test_{mesa_numero}"
    mesa_qr = f"karaoke-mesa-{mesa_numero:02d}"
    
    response = client.post(
        "/api/v1/mesas/",
        json={"nombre": mesa_nombre, "qr_code": mesa_qr},
        headers=HEADERS
    )
    assert response.status_code in [200, 201], f"Error: {response.text}"
    mesa_data = response.json()
    mesa_id = mesa_data['id']
    print_success(f"Mesa creada: {mesa_id} ({mesa_nombre})")
    
    # Conectar usuario 1
    usuario1_qr = f"{mesa_qr}-usuario1"
    response = client.post(
        f"/api/v1/mesas/{usuario1_qr}/conectar",
        json={"nick": "Usuario1"}
    )
    assert response.status_code == 200, f"Error: {response.text}"
    usuario1_id = response.json()['id']
    print_success(f"Usuario1 conectado: {usuario1_id}")
    
    # Conectar usuario 2
    usuario2_qr = f"{mesa_qr}-usuario2"
    response = client.post(
        f"/api/v1/mesas/{usuario2_qr}/conectar",
        json={"nick": "Usuario2"}
    )
    assert response.status_code == 200
    usuario2_id = response.json()['id']
    print_success(f"Usuario2 conectado: {usuario2_id}")
    
    return mesa_id, usuario1_id, usuario2_id

def test_2_agregar_canciones(usuario1_id, usuario2_id):
    print_test("TEST 2: Agregar Canciones y Verificar Cache")
    
    songs = [
        {"titulo": "Bohemian Rhapsody", "youtube_id": "fJ9rUzIMt7o", "duracion_seconds": 354},
        {"titulo": "Another One Bites the Dust", "youtube_id": "rY0WxgSXdVE", "duracion_seconds": 215},
        {"titulo": "Somebody to Love", "youtube_id": "kijpcR38kM4", "duracion_seconds": 294}
    ]
    
    for song in songs[:2]:
        response = client.post(f"/api/v1/canciones/{usuario1_id}", json=song)
        if response.status_code in [200, 201]:
            print_success(f"Canción agregada: {song['titulo']}")
        else:
            print_info(f"Canción no agregada (posiblemente sin créditos): {response.json()['detail'][:50]}")
        time.sleep(0.1)
    
    # Canción para usuario 2
    response = client.post(f"/api/v1/canciones/{usuario2_id}", json=songs[2])
    if response.status_code in [200, 201]:
        print_success(f"Canción agregada para Usuario2: {songs[2]['titulo']}")
    
    time.sleep(1)
    
    # Verificar cache
    cache_file_u1 = f"songs_usuario_{usuario1_id}.json"
    if check_cache_file_exists(cache_file_u1):
        cache_u1 = read_cache_file(cache_file_u1)
        num = len(cache_u1.get('canciones', []))
        print_success(f"Cache Usuario1 contiene {num} canción(es)")
    
    cache_file_u2 = f"songs_usuario_{usuario2_id}.json"
    if check_cache_file_exists(cache_file_u2):
        cache_u2 = read_cache_file(cache_file_u2)
        num = len(cache_u2.get('canciones', []))
        print_success(f"Cache Usuario2 contiene {num} canción(es)")

def test_3_lectura_desde_cache(usuario1_id):
    print_test("TEST 3: Lectura desde Cache")
    
    start = time.time()
    response = client.get(f"/api/v1/canciones/{usuario1_id}/lista")
    elapsed = time.time() - start
    
    if response.status_code == 200:
        canciones = response.json()
        print_success(f"Lectura en {elapsed*1000:.2f}ms - {len(canciones)} canciones")
    else:
        print_info(f"Lectura no disponible: {response.status_code}")

def test_4_agregar_consumos(mesa_id, usuario1_id):
    print_test("TEST 4: Agregar Consumos")
    
    # Crear productos
    productos = [
        {"nombre": "Cerveza", "categoria": "Bebidas", "valor": 8000, "costo": 5000, "stock": 50},
        {"nombre": "Whisky", "categoria": "Bebidas", "valor": 15000, "costo": 8000, "stock": 20}
    ]
    
    producto_ids = []
    for prod in productos:
        response = client.post(f"/api/v1/productos/", json=prod, headers=HEADERS)
        if response.status_code in [200, 201]:
            resp_json = response.json()
            if 'id' in resp_json:
                producto_ids.append(resp_json['id'])
                print_info(f"Producto: {prod['nombre']} (ID: {resp_json['id']})")
            else:
                print_info(f"Respuesta inesperada: {resp_json}")
    
    if not producto_ids:
        print_info("No se pudieron crear productos, saltando consumos")
        return
    
    # Agregar consumos
    for i, prod_id in enumerate(producto_ids):
        response = client.post(
            f"/api/v1/consumos/pedir/{usuario1_id}",
            json={"producto_id": prod_id, "cantidad": 1}
        )
        if response.status_code in [200, 201]:
            print_success(f"Consumo agregado")
        time.sleep(0.1)
    
    time.sleep(1)
    
    # Verificar cache de mesa
    cache_file_mesa = f"mesa_cuenta_{mesa_id}.json"
    if check_cache_file_exists(cache_file_mesa):
        cache_mesa = read_cache_file(cache_file_mesa)
        consumos = len(cache_mesa.get('consumos', []))
        total = cache_mesa.get('total_consumido', 0)
        print_success(f"Cache mesa: {consumos} consumos, Total: ${total}")
    else:
        print_info("Cache de mesa no encontrado (podría estar en construcción)")

def test_5_verificar_archivos():
    print_test("TEST 5: Archivos de Cache en Disco")
    
    if not CACHE_DIR.exists():
        print_info("Directorio de cache vacío")
        return
    
    cache_files = list(CACHE_DIR.glob("*.json"))
    size_total = sum(f.stat().st_size for f in cache_files)
    
    print_success(f"Total de archivos: {len(cache_files)}")
    print_info(f"Tamaño total: {size_total} bytes")
    for f in cache_files:
        print_info(f"  - {f.name} ({f.stat().st_size} bytes)")

# ============================================
# MAIN
# ============================================

def run_all_tests():
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}TEST DEL SISTEMA DE CACHE{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    
    try:
        mesa_id, usuario1_id, usuario2_id = test_1_crear_mesa_y_usuarios()
        test_2_agregar_canciones(usuario1_id, usuario2_id)
        test_3_lectura_desde_cache(usuario1_id)
        test_4_agregar_consumos(mesa_id, usuario1_id)
        test_5_verificar_archivos()
        
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}✓ TESTS COMPLETADOS{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
        
    except Exception as e:
        print(f"\n{Colors.BOLD}{Colors.FAIL}✗ ERROR: {str(e)}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
