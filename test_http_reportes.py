#!/usr/bin/env python3
"""
Test detallado de los endpoints de reportes usando urllib
"""
import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_report(report_type, description):
    """Test un endpoint de reporte individual"""
    print(f"\n[TEST] {description}")
    print("-" * 80)
    
    url = f"{BASE_URL}/admin/reports/{report_type}"
    print(f"URL: {url}")
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status_code = response.status
            data = json.loads(response.read().decode('utf-8'))
            
            print(f"Status Code: {status_code}")
            
            if isinstance(data, list) and len(data) > 0:
                print(f"Registros retornados: {len(data)}")
                first = data[0]
                print(f"Primer registro:\n{json.dumps(first, indent=2, ensure_ascii=False)}")
                
                # Verificar si tiene valores válidos
                has_nulls = any(v is None for v in first.values())
                has_undefined = any("undefined" in str(v).lower() for v in first.values())
                
                if has_nulls:
                    print("⚠️  PROBLEMA: Contiene valores None")
                    return False
                elif has_undefined:
                    print("⚠️  PROBLEMA: Contiene valores 'undefined'")
                    return False
                else:
                    print("✓ OK: Todos los valores son válidos")
                    return True
            else:
                print("⚠️  ADVERTENCIA: Lista vacía o no es lista")
                return False
                
    except urllib.error.URLError as e:
        if "Connection refused" in str(e):
            print(f"❌ ERROR: No se pudo conectar - ¿El servidor está ejecutando en {BASE_URL}?")
        else:
            print(f"❌ ERROR de conexión: {str(e)}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ ERROR al parsear JSON: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    reports = [
        ("top-songs", "🎵 Top Canciones Más Cantadas (funciona bien)"),
        ("top-products", "🥤 Top Productos Más Consumidos (funciona bien)"),
        ("songs-by-table", "🎶 Canciones por Mesa (SIN ARREGLAR)"),
        ("songs-by-user", "👥 Canciones por Usuario (ARREGLÉ)"),
        ("top-rejected-songs", "👎 Canciones Más Rechazadas (ARREGLÉ)"),
    ]
    
    print("=" * 80)
    print("PRUEBA DE ENDPOINTS DE REPORTES")
    print("=" * 80)
    print(f"\nServidor esperado: {BASE_URL}\n")
    
    results = {}
    for report_type, description in reports:
        results[report_type] = test_report(report_type, description)
        time.sleep(0.5)  # Pequeño delay entre requests
    
    print("\n" + "=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    for report_type, description in reports:
        status = "✓ OK" if results[report_type] else "✗ FALLO"
        print(f"{status} - {description}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nPasaron: {passed}/{total} pruebas")

if __name__ == "__main__":
    main()
