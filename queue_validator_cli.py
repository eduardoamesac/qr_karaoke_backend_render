#!/usr/bin/env python3
"""
VALIDADOR INTERACTIVO DE COLA - Ejecuta desde terminal
====================================================

Uso:
    python queue_validator_cli.py

O desde otra terminal mientras corre el servidor:
    python queue_validator_cli.py --auto --interval 5

Esto permite monitorear la cola desde la terminal y ver exactamente
qué canciones están "escondidas" (en BD pero no en UI).
"""

import requests
import json
import time
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

# Colores para terminal
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

BASE_URL = "http://localhost:8000"

def colored(text: str, color: str) -> str:
    """Agrega color al texto"""
    return f"{color}{text}{Colors.ENDC}"

def print_header(text: str):
    """Imprime un header"""
    print(f"\n{colored('=' * 70, Colors.BOLD)}")
    print(colored(f"  {text}", Colors.HEADER + Colors.BOLD))
    print(f"{colored('=' * 70, Colors.BOLD)}\n")

def print_section(text: str):
    """Imprime una sección"""
    print(colored(f"\n📌 {text}", Colors.OKBLUE + Colors.BOLD))
    print(colored("-" * 60, Colors.OKBLUE))

def get_debug_report() -> Dict[str, Any]:
    """Obtiene el reporte completo de debug"""
    try:
        response = requests.get(f"{BASE_URL}/admin/queue/debug", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(colored(f"❌ ERROR: No se puede conectar a {BASE_URL}", Colors.FAIL))
        sys.exit(1)
    except Exception as e:
        print(colored(f"❌ ERROR: {str(e)}", Colors.FAIL))
        sys.exit(1)

def get_next_to_play() -> Dict[str, Any]:
    """Obtiene la próxima canción a reproducir"""
    try:
        response = requests.get(f"{BASE_URL}/admin/queue/next-to-play", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def compare_ui_vs_reality(ui_state: Dict[str, Any]) -> Dict[str, Any]:
    """Compara UI vs realidad"""
    try:
        response = requests.post(
            f"{BASE_URL}/admin/queue/compare-ui-vs-reality",
            json=ui_state,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def print_now_playing(report: Dict[str, Any]):
    """Muestra qué está reproduciendo"""
    print_section("🎵 QUÉ ESTÁ REPRODUCIENDO AHORA")
    
    next_report = get_next_to_play()
    
    if "error" in next_report:
        print(colored(f"Error: {next_report['error']}", Colors.FAIL))
        return
    
    status = next_report.get("status", "unknown")
    
    if status == "something_is_playing":
        now_playing = next_report.get("now_playing", {})
        print(colored(f"▶ {now_playing.get('titulo', 'N/A')}", Colors.OKGREEN + Colors.BOLD))
        print(f"  ID: {now_playing.get('id')}")
        print(f"  Usuario: {now_playing.get('usuario_id', 'N/A')}")
        progress = now_playing.get("progress_percent", 0)
        print(f"  Progreso: {progress}% [{('█' * (progress // 10)) + ('░' * (10 - progress // 10))}]")
        print(f"  Duración: {now_playing.get('duration', 'N/A')}s")
        
        next_song = next_report.get("next_after_current", {})
        if next_song:
            print(f"\n  Siguiente: {colored(next_song.get('titulo', 'N/A'), Colors.OKBLUE)}")
            print(f"            ID: {next_song.get('id')} (Usuario: {next_song.get('usuario_id')})")
    
    elif status == "empty":
        print(colored("⚠ LA COLA ESTÁ VACÍA - NADA VA A REPRODUCIR", Colors.WARNING))
    else:
        print(f"Estado: {status}")

def print_next_songs(report: Dict[str, Any], limit: int = 20):
    """Muestra las próximas canciones"""
    print_section(f"↓ PRÓXIMAS {limit} CANCIONES EN LA COLA")
    
    what_will_play = report.get("what_will_play", {})
    next_20 = what_will_play.get("next_20_in_queue", [])
    
    if not next_20:
        print(colored("No hay canciones en la cola", Colors.WARNING))
        return
    
    for i, song in enumerate(next_20[:limit], 1):
        song_id = song.get("id", "?")
        titulo = song.get("titulo", "Sin título")
        usuario = song.get("usuario", "?")
        estado = song.get("estado", "?")
        
        print(f"{i:2}. {colored(titulo, Colors.OKCYAN)}")
        print(f"    [ID: {song_id} | Usuario: {usuario} | Estado: {estado}]")

def print_database_state(report: Dict[str, Any]):
    """Muestra el estado completo de la BD"""
    print_section("💾 ESTADO COMPLETO EN BASE DE DATOS")
    
    db_state = report.get("database_state", {})
    
    repr_count = db_state.get("reproduciendo_count", 0)
    print(f"Reproduciendo: {colored(f'{repr_count} canción(es)', Colors.OKGREEN)}")
    
    aprob_count = db_state.get("aprobado_count", 0)
    print(f"Aprobadas: {colored(f'{aprob_count} canciones', Colors.OKBLUE)}")
    
    lazy_count = db_state.get("pendiente_lazy_count", 0)
    print(f"Pendientes (lazy): {colored(f'{lazy_count} canciones', Colors.WARNING)}")
    
    pend_count = db_state.get("pendiente_count", 0)
    print(f"Pendientes: {colored(f'{pend_count} canciones', Colors.WARNING)}")
    
    cumpl_count = db_state.get("cumplida_count", 0)
    print(f"Cumplidas: {cumpl_count} canciones")
    
    rech_count = db_state.get("rechazada_count", 0)
    print(f"Rechazadas: {colored(f'{rech_count} canciones', Colors.FAIL)}")
    
    print(colored("\n📋 Detalle de APROBADAS (van a sonar):", Colors.BOLD))
    aprobada_list = db_state.get("aprobado_list", [])
    if aprobada_list:
        for i, song in enumerate(aprobada_list[:10], 1):
            print(f"  {i}. [{song.get('id')}] {song.get('titulo')} - {song.get('usuario')}")
        if len(aprobada_list) > 10:
            print(f"  ... y {len(aprobada_list) - 10} más")
    else:
        print("  (ninguna)")

def print_integrity_checks(report: Dict[str, Any]):
    """Muestra validaciones de integridad"""
    print_section("🔍 VALIDACIONES DE INTEGRIDAD")
    
    checks = report.get("integrity_checks", {})
    issues = report.get("issues", [])
    
    # Mostrar checks individuales
    check_names = {
        "now_playing_not_in_approved": "now_playing NO está duplicado en aprobadas",
        "no_duplicates": "No hay canciones duplicadas",
        "all_approved_have_correct_status": "Todas las aprobadas tienen estado correcto",
        "issues_detected": "Se detectaron problemas"
    }
    
    for check_key, check_name in check_names.items():
        value = checks.get(check_key, False)
        status = colored("✓ PASS", Colors.OKGREEN) if value else colored("✗ FAIL", Colors.FAIL)
        print(f"{status} - {check_name}")
    
    # Mostrar issues
    if issues:
        print(f"\n{colored('Problemas detectados:', Colors.FAIL + Colors.BOLD)}")
        for issue in issues:
            severity = issue.get("severity", "INFO")
            message = issue.get("message", "Sin detalles")
            
            if severity == "CRITICAL":
                color = Colors.FAIL
                icon = "🔴"
            elif severity == "WARNING":
                color = Colors.WARNING
                icon = "🟡"
            else:
                color = Colors.OKBLUE
                icon = "🔵"
            
            print(f"  {icon} [{severity}] {colored(message, color)}")
    else:
        print(colored("\n✓ No se detectaron problemas", Colors.OKGREEN))

def print_hidden_songs(report: Dict[str, Any]):
    """Identifica y muestra canciones escondidas"""
    print_section("👻 CANCIONES ESCONDIDAS (en BD pero posiblemente no visibles en UI)")
    
    what_will_play = report.get("what_will_play", {})
    next_20 = what_will_play.get("next_20_in_queue", [])
    
    if not next_20:
        print("No hay canciones en cola para mostrar como escondidas")
        return
    
    # En realidad todas las que están en BD pero fuera del UI rendering
    # son candidatas a estar escondidas
    limit_ui = 10  # Asumimos que UI muestra ~10
    
    if len(next_20) > limit_ui:
        hidden = next_20[limit_ui:]
        print(colored(f"⚠ Encontradas {len(hidden)} canciones que podrían estar escondidas:\n", Colors.WARNING))
        
        for i, song in enumerate(hidden, limit_ui + 1):
            print(f"{i:2}. {colored(song.get('titulo', 'Sin título'), Colors.WARNING)}")
            print(f"    [ID: {song.get('id')} | Usuario: {song.get('usuario')}]")
    else:
        print(colored("✓ No hay canciones escondidas (todas visible en UI)", Colors.OKGREEN))

def print_recent_operations(report: Dict[str, Any]):
    """Muestra operaciones recientes"""
    print_section("⏱ OPERACIONES RECIENTES")
    
    ops = report.get("recent_queue_operations", [])
    
    if not ops:
        print("No hay operaciones recientes registradas")
        return
    
    for op in ops[:10]:
        operation = op.get("operation", "?")
        timestamp = op.get("timestamp", "?")
        song_title = op.get("song_title", "?")
        details = op.get("details", "")
        
        print(f"{timestamp}")
        print(f"  {colored(operation, Colors.OKBLUE)} - {song_title}")
        if details:
            print(f"  Detalles: {details}")

def print_diagnostic_report(report: Dict[str, Any]):
    """Imprime el reporte completo de diagnóst"""
    print_header("🔧 REPORTE DE DIAGNÓSTICO - QR KARAOKE QUEUE VALIDATOR")
    
    timestamp = report.get("timestamp", "N/A")
    print(f"Generado: {colored(timestamp, Colors.OKBLUE)}\n")
    
    # Orden: mostrar qué va a sonar, después estado, después problemas
    print_now_playing(report)
    print_next_songs(report, limit=15)
    print_database_state(report)
    print_integrity_checks(report)
    print_hidden_songs(report)
    print_recent_operations(report)
    
    print(f"\n{colored('=' * 70, Colors.BOLD)}\n")

def interactive_menu():
    """Menú interactivo"""
    while True:
        print(colored("\n📊 VALIDADOR DE COLA - MENÚ INTERACTIVO", Colors.HEADER + Colors.BOLD))
        print("=" * 50)
        print("1. Ver reporte completo")
        print("2. Ver qué está reproduciendo")
        print("3. Ver próximas 20 canciones")
        print("4. Ver estado de base de datos")
        print("5. Ver validaciones de integridad")
        print("6. Ver canciones escondidas")
        print("7. Ver operaciones recientes")
        print("8. Ver JSON completo")
        print("9. Comparar UI vs Realidad (custom)")
        print("0. Salir")
        print("=" * 50)
        
        choice = input(colored("\nSelecciona una opción: ", Colors.BOLD)).strip()
        
        if choice == "0":
            print(colored("👋 ¡Hasta luego!", Colors.OKGREEN))
            break
        
        elif choice == "1":
            report = get_debug_report()
            print_diagnostic_report(report)
        
        elif choice == "2":
            report = get_debug_report()
            print_now_playing(report)
        
        elif choice == "3":
            report = get_debug_report()
            limit = input("¿Cuántas canciones ver? (default 20): ").strip()
            try:
                limit = int(limit) if limit else 20
            except:
                limit = 20
            print_next_songs(report, limit)
        
        elif choice == "4":
            report = get_debug_report()
            print_database_state(report)
        
        elif choice == "5":
            report = get_debug_report()
            print_integrity_checks(report)
        
        elif choice == "6":
            report = get_debug_report()
            print_hidden_songs(report)
        
        elif choice == "7":
            report = get_debug_report()
            print_recent_operations(report)
        
        elif choice == "8":
            report = get_debug_report()
            print(colored("\n📋 JSON COMPLETO:\n", Colors.OKBLUE + Colors.BOLD))
            print(json.dumps(report, indent=2, ensure_ascii=False))
        
        elif choice == "9":
            print(colored("\n🔎 COMPARAR UI vs REALIDAD", Colors.OKBLUE + Colors.BOLD))
            print("Ingresa el state actual de la UI (formato JSON)")
            print("Ejemplo: {\"now_playing\": {\"id\": 105}, \"upcoming\": []}")
            try:
                ui_json = input("UI State JSON: ").strip()
                ui_state = json.loads(ui_json)
                result = compare_ui_vs_reality(ui_state)
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print(colored("❌ JSON inválido", Colors.FAIL))
        
        else:
            print(colored("❌ Opción no válida", Colors.FAIL))
        
        input(colored("\nPresiona ENTER para continuar...", Colors.BOLD))

def auto_monitor(interval: int = 5):
    """Monitoreo automático"""
    print_header("🔄 MONITOREO AUTOMÁTICO (Presiona Ctrl+C para salir)")
    print(f"Actualizando cada {interval} segundos...\n")
    
    iteration = 0
    try:
        while True:
            iteration += 1
            print(colored(f"\n{'='*70}", Colors.BOLD))
            print(colored(f"Iteración #{iteration} - {datetime.now().strftime('%H:%M:%S')}", Colors.OKBLUE + Colors.BOLD))
            print(colored(f"{'='*70}\n", Colors.BOLD))
            
            report = get_debug_report()
            
            # Mostrar solo lo esencial
            print_now_playing(report)
            print_next_songs(report, limit=10)
            print_integrity_checks(report)
            
            issues = report.get("issues", [])
            if issues:
                print(colored(f"\n⚠ {len(issues)} Problema(s) detectado(s)", Colors.WARNING))
            
            print(colored(f"\nProxima actualización en {interval}s (Ctrl+C para salir)...", Colors.OKBLUE))
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print(colored("\n\n✓ Monitoreo finalizado", Colors.OKGREEN))
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description="Validador de Cola QR Karaoke - Herramienta de Debug"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Modo monitoreo automático (en lugar de menú interactivo)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Intervalo de actualización en segundos (default: 5)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Mostrar reporte una sola vez y salir"
    )
    
    args = parser.parse_args()
    
    if args.once:
        report = get_debug_report()
        print_diagnostic_report(report)
    elif args.auto:
        auto_monitor(args.interval)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
