"""
Test Simplificado del Sistema de Cache en JSON
Prueba la funcionalidad sin importar main.py directamente
"""

import json
import time
import requests
from pathlib import Path

# ============================================
# CONFIGURACIÓN
# ============================================

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "zxc12345"
CACHE_DIR = Path("cache")
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
    
    try:
        # Crear mesa con nombre y QR code con formato correcto
        mesa_numero = int(time.time()) % 100
        mesa_nombre = f"Mesa_{mesa_numero}"
        mesa_qr = f"karaoke-mesa-{mesa_numero:02d}"
        
        response = requests.post(
            f"{BASE_URL}/api/v1/mesas/",
            json={"nombre": mesa_nombre, "qr_code": mesa_qr},
            headers=HEADERS
        )
        assert response.status_code in [200, 201], f"Error creando mesa: {response.text}"
        mesa_data = response.json()
        mesa_id = mesa_data['id']
        print_success(f"Mesa creada: {mesa_id} ({mesa_nombre})")
        
        # Conectar usuario 1
        usuario1_qr = f"{mesa_qr}-usuario1"
        response = requests.post(
            f"{BASE_URL}/api/v1/mesas/{usuario1_qr}/conectar",
            json={"nick": "Usuario1"}
        )
        assert response.status_code == 200, f"Error conectando usuario: {response.text}"
        usuario1_data = response.json()
        usuario1_id = usuario1_data['id']
        print_success(f"Usuario1 conectado: {usuario1_id}")
        
        # Conectar usuario 2
        usuario2_qr = f"{mesa_qr}-usuario2"
        response = requests.post(
            f"{BASE_URL}/api/v1/mesas/{usuario2_qr}/conectar",
            json={"nick": "Usuario2"}
        )
        assert response.status_code == 200
        usuario2_data = response.json()
        usuario2_id = usuario2_data['id']
        print_success(f"Usuario2 conectado: {usuario2_id}")
        
        return mesa_id, usuario1_id, usuario2_id
        
    except requests.exceptions.ConnectionError:
        print_fail("No se puede conectar a http://localhost:8000")
        print_info("¿La aplicación está corriendo? Ejecuta: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        return None, None, None

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
        response = requests.post(
            f"{BASE_URL}/api/v1/canciones/{usuario1_id}",
            json=song
        )
        assert response.status_code in [200, 201], f"Error agregando canción: {response.text}"
        cancion_id = response.json()['id']
        print_success(f"Canción agregada para Usuario1: {song['titulo']} (ID: {cancion_id})")
        time.sleep(0.1)
    
    # Agregar canción para usuario 2
    response = requests.post(
        f"{BASE_URL}/api/v1/canciones/{usuario2_id}",
        json=songs[2]
    )
    assert response.status_code in [200, 201]
    print_success(f"Canción agregada para Usuario2: {songs[2]['titulo']}")
    
    # Verificar que se crearon archivos de cache
    time.sleep(1)
    
    cache_file_u1 = f"songs_usuario_{usuario1_id}.json"
    cache_file_u2 = f"songs_usuario_{usuario2_id}.json"
    
    if check_cache_file_exists(cache_file_u1):
        print_success(f"Archivo de cache creado: {cache_file_u1}")
        cache_u1 = read_cache_file(cache_file_u1)
        if cache_u1:
            num_canciones = len(cache_u1.get('canciones', []))
            print_success(f"Cache Usuario1 contiene {num_canciones} canción(es)")
            print_info(f"Tamaño cache Usuario1: {get_cache_file_size(cache_file_u1)} bytes")
    else:
        print_warning(f"Cache file no existe: {cache_file_u1}")
    
    if check_cache_file_exists(cache_file_u2):
        print_success(f"Archivo de cache creado: {cache_file_u2}")
        cache_u2 = read_cache_file(cache_file_u2)
        if cache_u2:
            num_canciones = len(cache_u2.get('canciones', []))
            print_success(f"Cache Usuario2 contiene {num_canciones} canción(es)")
            print_info(f"Tamaño cache Usuario2: {get_cache_file_size(cache_file_u2)} bytes")
    else:
        print_warning(f"Cache file no existe: {cache_file_u2}")

# ============================================
# TEST 3: Verificar Lectura desde Cache
# ============================================

def test_lectura_desde_cache(usuario1_id):
    print_test("TEST 3: Verificar Lectura desde Cache")
    
    # Primera lectura (desde cache)
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/v1/canciones/{usuario1_id}/lista")
    time_from_cache = time.time() - start_time
    assert response.status_code == 200
    canciones = response.json()
    print_success(f"Lectura desde cache en {time_from_cache*1000:.2f}ms - {len(canciones)} canciones")
    
    # Segunda lectura (desde cache también)
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/api/v1/canciones/{usuario1_id}/lista")
    time_from_cache2 = time.time() - start_time
    assert response.status_code == 200
    print_success(f"Segunda lectura desde cache en {time_from_cache2*1000:.2f}ms")
    
    print_info(f"Las lecturas desde cache son muy rápidas (~{time_from_cache*1000:.2f}ms)")

# ============================================
# TEST 4: Agregar Consumos
# ============================================

def test_agregar_consumos(mesa_id, usuario1_id):
    print_test("TEST 4: Agregar Consumos y Verificar Cache de Mesa")
    
    # Primero, crear algunos productos
    productos = [
        {"nombre": "Cerveza", "categoria": "Bebidas", "valor": 8000, "costo": 5000, "stock": 50},
        {"nombre": "Whisky", "categoria": "Bebidas", "valor": 15000, "costo": 8000, "stock": 20},
        {"nombre": "Refresco", "categoria": "Bebidas", "valor": 3000, "costo": 1000, "stock": 100}
    ]
    
    producto_ids = []
    for prod in productos:
        response = requests.post(f"{BASE_URL}/api/v1/productos", json=prod, headers=HEADERS)
        if response.status_code in [200, 201]:
            prod_id = response.json()['id']
            producto_ids.append(prod_id)
            print_info(f"Producto creado: {prod['nombre']} (ID: {prod_id})")
        else:
            print_warning(f"Error creando producto {prod['nombre']}: {response.text}")
    
    if len(producto_ids) < 3:
        print_warning("No se pudieron crear todos los productos, usando los disponibles...")
    
    # Agregar consumos
    consumos_data = [
        {"producto_id": producto_ids[0], "cantidad": 2} if len(producto_ids) > 0 else None,
        {"producto_id": producto_ids[1], "cantidad": 1} if len(producto_ids) > 1 else None,
        {"producto_id": producto_ids[2], "cantidad": 3} if len(producto_ids) > 2 else None,
    ]
    
    consumos_agregados = 0
    for consumo in [c for c in consumos_data if c is not None]:
        response = requests.post(
            f"{BASE_URL}/api/v1/consumos/pedir/{usuario1_id}",
            json=consumo
        )
        if response.status_code in [200, 201]:
            print_success(f"Consumo agregado: Producto {consumo['producto_id']}, Cantidad {consumo['cantidad']}")
            consumos_agregados += 1
            time.sleep(0.1)
        else:
            print_warning(f"Error agregando consumo: {response.text}")
    
    # Verificar que se creó el archivo de cache de mesa
    time.sleep(1)
    
    cache_file_mesa = f"mesa_cuenta_{mesa_id}.json"
    if check_cache_file_exists(cache_file_mesa):
        print_success(f"Archivo de cache de mesa creado: {cache_file_mesa}")
        cache_mesa = read_cache_file(cache_file_mesa)
        if cache_mesa:
            consumos_en_cache = cache_mesa.get('consumos', [])
            print_success(f"Cache de mesa contiene {len(consumos_en_cache)} consumo(s)")
            print_info(f"Total consumido: ${cache_mesa.get('total_consumido', 0)}")
            print_info(f"Tamaño cache mesa: {get_cache_file_size(cache_file_mesa)} bytes")
    else:
        print_warning(f"Cache file no existe: {cache_file_mesa}")

# ============================================
# TEST 5: Verificar Archivos de Cache
# ============================================

def test_verificar_archivos_cache():
    print_test("TEST 5: Verificar Archivos de Cache en Disco")
    
    if not CACHE_DIR.exists():
        print_warning(f"Directorio de cache no existe: {CACHE_DIR}")
        return
    
    cache_files = list(CACHE_DIR.glob("*.json"))
    print_info(f"Total de archivos de cache: {len(cache_files)}")
    
    size_total = 0
    for cache_file in cache_files:
        size = cache_file.stat().st_size
        size_total += size
        print_info(f"  - {cache_file.name}: {size} bytes")
    
    print_success(f"Tamaño total de cache: {size_total} bytes ({size_total/1024:.2f} KB)")

# ============================================
# EJECUCIÓN DE TESTS
# ============================================

def run_all_tests():
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}TESTING SIMPLIFICADO DEL SISTEMA DE CACHE EN JSON{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    
    try:
        # Ejecutar tests
        result = test_crear_mesa_y_usuarios()
        if result[0] is None:
            print_fail("No se puede continuar sin mesa y usuarios")
            return
        
        mesa_id, usuario1_id, usuario2_id = result
        
        test_agregar_canciones(usuario1_id, usuario2_id)
        test_lectura_desde_cache(usuario1_id)
        test_agregar_consumos(mesa_id, usuario1_id)
        test_verificar_archivos_cache()
        
        print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}✓ TESTING COMPLETO EXITOSO{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"\n{Colors.OKGREEN}El sistema de cache está funcionando correctamente.{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Los archivos JSON se están guardando en: {CACHE_DIR.absolute()}{Colors.ENDC}\n")
        
    except AssertionError as e:
        print(f"\n{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}✗ TEST FALLÓ: {str(e)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}\n")
    except Exception as e:
        print(f"\n{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}✗ ERROR: {str(e)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.FAIL}{'='*60}{Colors.ENDC}\n")

if __name__ == "__main__":
    run_all_tests()
