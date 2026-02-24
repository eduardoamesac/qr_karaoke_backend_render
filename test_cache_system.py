"""
Script de pruebas para verificar que el sistema de caché de canciones funciona correctamente
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "tu_api_key_aqui"  # Si necesitas API key

def test_health():
    """Test: Verificar que el servidor está funcionando"""
    print("\n" + "="*60)
    print("TEST 1: Verificar que el servidor está en línea")
    print("="*60)
    try:
        resp = requests.get(f"{BASE_URL}/docs", timeout=5)
        if resp.status_code == 200:
            print("✅ Servidor en línea en http://127.0.0.1:8000")
            return True
        else:
            print(f"❌ Error: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return False

def test_cache_manager():
    """Test: Verificar que cache_manager funciona"""
    print("\n" + "="*60)
    print("TEST 2: Verificar que cache_manager está funcionando")
    print("="*60)
    try:
        from cache_manager import cache_manager
        
        # Probar agregar una canción
        test_song = {
            "id": None,
            "usuario_id": 1,
            "youtube_id": "dQw4w9WgXcQ",
            "titulo": "Test Song",
            "duracion_seconds": 213,
            "estado": "pendiente_lazy",
            "is_karaoke": True
        }
        
        song_id = cache_manager.add_song_to_cache(1, test_song)
        print(f"✅ Canción agregada al caché con ID: {song_id}")
        
        # Verificar que se guardó
        retrieved = cache_manager.get_song_by_id(song_id)
        if retrieved and retrieved.get('titulo') == "Test Song":
            print(f"✅ Canción recuperada del caché: {retrieved['titulo']}")
            return True
        else:
            print("❌ No se pudo recuperar la canción del caché")
            return False
    except Exception as e:
        print(f"❌ Error en prueba de cache_manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_files():
    """Test: Verificar que los archivos de caché se crean correctamente"""
    print("\n" + "="*60)
    print("TEST 3: Verificar que los archivos JSON se crean")
    print("="*60)
    try:
        import os
        from pathlib import Path
        
        cache_dir = Path("cache")
        
        # Verificar que directorio existe
        if cache_dir.exists():
            print(f"✅ Directorio de caché existe: {cache_dir.absolute()}")
            
            # Listar archivos
            files = list(cache_dir.glob("*.json"))
            if files:
                print(f"✅ Se encontraron {len(files)} archivos JSON:")
                for f in files:
                    size = os.path.getsize(f)
                    print(f"   - {f.name} ({size} bytes)")
                return True
            else:
                print("⚠️  Directorio vacío (se crearán archivos cuando se agreguen datos)")
                return True
        else:
            print("❌ Directorio cache no existe")
            return False
    except Exception as e:
        print(f"❌ Error verificando archivos: {e}")
        return False

def test_crud_functions():
    """Test: Verificar que funciones de CRUD funcionan"""
    print("\n" + "="*60)
    print("TEST 4: Verificar que funciones CRUD funcionan")
    print("="*60)
    try:
        from database import SessionLocal
        import crud
        
        db = SessionLocal()
        
        # Probar get_canciones_pendientes
        canciones_pendientes = crud.get_canciones_pendientes(db)
        print(f"✅ get_canciones_pendientes devolvió {len(canciones_pendientes)} canciones")
        
        # Probar get_duracion_total_cola_aprobada
        duracion = crud.get_duracion_total_cola_aprobada(db)
        print(f"✅ get_duracion_total_cola_aprobada devolvió: {duracion} segundos")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Error en funciones CRUD: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_models_import():
    """Test: Verificar que los modelos se importan correctamente"""
    print("\n" + "="*60)
    print("TEST 5: Verificar que modelos se importan correctamente")
    print("="*60)
    try:
        import models
        import schemas
        
        # Verificar que Cancion existe en models
        if hasattr(models, 'Cancion'):
            print("ℹ️  models.Cancion existe (ahora es solo histórico, no se usa)")
        
        # Verificar schemas
        if hasattr(schemas, 'Cancion'):
            print("✅ schemas.Cancion existe")
            return True
        else:
            print("❌ schemas.Cancion no existe")
            return False
    except Exception as e:
        print(f"❌ Error importando modelos: {e}")
        return False

def test_imports():
    """Test: Verificar que todos los imports funcionan"""
    print("\n" + "="*60)
    print("TEST 6: Verificar que todos los imports funcionan")
    print("="*60)
    try:
        import canciones
        import crud
        import cache_manager
        import queue_manager
        import websocket_manager
        
        print("✅ canciones importado")
        print("✅ crud importado")
        print("✅ cache_manager importado")
        print("✅ queue_manager importado")
        print("✅ websocket_manager importado")
        
        return True
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  PRUEBAS DEL SISTEMA DE CACHÉ DE CANCIONES (JSON)        ║")
    print("║  Fecha: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " * 28 + "║")
    print("╚" + "="*58 + "╝")
    
    results = []
    
    # Ejecutar pruebas
    results.append(("Health Check", test_health()))
    results.append(("Imports", test_imports()))
    results.append(("Cache Manager", test_cache_manager()))
    results.append(("Cache Files", test_cache_files()))
    results.append(("CRUD Functions", test_crud_functions()))
    results.append(("Models Import", test_models_import()))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBAS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name:.<40} {status}")
    
    print("="*60)
    print(f"Total: {passed}/{total} pruebas pasadas")
    
    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema funciona correctamente.")
    else:
        print(f"\n⚠️  {total - passed} prueba(s) fallaron. Revisar arriba para detalles.")

if __name__ == "__main__":
    main()
