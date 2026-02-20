#!/usr/bin/env python
"""
Script para aplicar la migración de optimización de base de datos.
Ejecuta: python apply_optimization_migration.py
"""

import subprocess
import sys

def main():
    print("=" * 80)
    print("🚀 APLICANDO MIGRACIÓN DE OPTIMIZACIÓN DE BASE DE DATOS")
    print("=" * 80)
    print()
    print("Esta migración va a:")
    print("✓ Agregar columna 'is_banned' a la tabla 'usuarios'")
    print("✓ Migrar datos de 'banned_nicks' a 'usuarios'")
    print("✓ Eliminar tabla 'banned_nicks' (innecesaria)")
    print("✓ Eliminar tabla 'admin_logs' (solo auditoría)")
    print("✓ Eliminar tabla 'configuracion_global' (usa JSON en lugar)")
    print()
    
    confirm = input("¿Deseas continuar? (s/n): ").strip().lower()
    if confirm != 's':
        print("Migración cancelada.")
        return
    
    print()
    print("Ejecutando alembic upgrade head...")
    print()
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=".",
            capture_output=False
        )
        
        if result.returncode == 0:
            print()
            print("=" * 80)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 80)
            print()
            print("Cambios realizados:")
            print("1. ✓ Columna 'is_banned' agregada a usuarios")
            print("2. ✓ Datos migrados de banned_nicks a usuarios")
            print("3. ✓ Tabla 'banned_nicks' eliminada")
            print("4. ✓ Tabla 'admin_logs' eliminada")
            print("5. ✓ Tabla 'configuracion_global' eliminada")
            print()
            print("Tu base de datos está ahora optimizada y más ligera.")
            print()
        else:
            print()
            print("❌ Error durante la migración.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error ejecutando migración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
