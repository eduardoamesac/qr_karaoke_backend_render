#!/usr/bin/env python3
"""
Script de diagnóstico para verificar que el Autoplay está correctamente configurado.
Ejecutar: python diagnose_autoplay.py
"""

import sys
import requests
from database import SessionLocal
from models import Cancion
from sqlalchemy import func

def print_status(step, success, details=""):
    """Imprime el estado de una verificación."""
    status_icon = "✅" if success else "❌"
    print(f"{status_icon} {step}")
    if details:
        print(f"   └─ {details}")
    return success

def main():
    print("\n" + "="*60)
    print("🎵 DIAGNÓSTICO DE AUTOPLAY")
    print("="*60 + "\n")
    
    all_good = True
    
    # 1. Verificar que la base de datos tiene canciones con duración
    print("📋 Verificando Base de Datos...")
    try:
        db = SessionLocal()
        
        # Contar canciones
        total_songs = db.query(Cancion).count()
        all_good &= print_status(
            "Conexión a base de datos",
            True,
            f"Total de canciones: {total_songs}"
        )
        
        # Verificar canciones con duración
        songs_with_duration = db.query(Cancion).filter(Cancion.duracion_seconds > 0).count()
        all_good &= print_status(
            "Canciones con duración > 0",
            songs_with_duration > 0,
            f"{songs_with_duration}/{total_songs} tienen duración"
        )
        
        # Verificar que hay canción reproduciendo
        playing = db.query(Cancion).filter(Cancion.estado == "reproduciendo").first()
        all_good &= print_status(
            "Canción en reproducción",
            playing is not None,
            f"Estado: {playing.estado if playing else 'Ninguna'}"
        )
        
        # Verificar cola aprobada
        approved = db.query(Cancion).filter(Cancion.estado == "aprobado").count()
        all_good &= print_status(
            "Canciones aprobadas (siguiente)",
            approved > 0,
            f"{approved} canción(es) en cola"
        )
        
        db.close()
        
    except Exception as e:
        all_good &= print_status("Base de datos", False, str(e))
    
    # 2. Verificar servidor
    print("\n🌐 Verificando Servidor...")
    try:
        response = requests.get("http://localhost:8000/api/v1/canciones/cola/extended", timeout=5)
        all_good &= print_status(
            "Servidor accesible",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        # Verificar que la respuesta incluye duración
        data = response.json()
        has_duration = False
        if data.get("now_playing") and data["now_playing"].get("duracion_seconds"):
            has_duration = True
        elif data.get("upcoming") and len(data["upcoming"]) > 0:
            has_duration = data["upcoming"][0].get("duracion_seconds", 0) > 0
        
        all_good &= print_status(
            "Cola con duración",
            has_duration,
            "Endpoint /canciones/cola/extended retorna duracion"
        )
        
    except requests.exceptions.ConnectionError:
        all_good &= print_status("Servidor accesible", False, "No se pudo conectar a localhost:8000")
    except Exception as e:
        all_good &= print_status("Servidor accesible", False, str(e))
    
    # 3. Verificar búsqueda de YouTube
    print("\n🔍 Verificando Búsqueda YouTube...")
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/youtube/public-search?q=happy+birthday+karaoke",
            timeout=10
        )
        all_good &= print_status(
            "API YouTube accesible",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        results = response.json()
        has_duration = False
        if isinstance(results, list) and len(results) > 0:
            has_duration = "duration_seconds" in results[0] and results[0]["duration_seconds"] > 0
        
        all_good &= print_status(
            "YouTube retorna duración",
            has_duration,
            f"Resultados encontrados: {len(results) if isinstance(results, list) else 0}"
        )
        
    except requests.exceptions.Timeout:
        print_status("API YouTube", False, "Timeout - YouTube API puede estar lenta o sin conexión")
    except Exception as e:
        print_status("API YouTube", False, str(e))
    
    # 4. Verificar código del player
    print("\n📝 Verificando Código del Player...")
    try:
        with open("static/player.html", "r", encoding="utf-8") as f:
            player_code = f.read()
        
        # Buscar fallback timer
        has_fallback_timer = "autoplayTimer" in player_code and "setTimeout" in player_code
        all_good &= print_status(
            "Fallback timer en código",
            has_fallback_timer,
            "Código contiene lógica de temporizador"
        )
        
        # Buscar manejo de play_song
        has_play_song = "play_song" in player_code
        all_good &= print_status(
            "Manejo de play_song",
            has_play_song,
            "Código escucha eventos play_song"
        )
        
        # Buscar duración_seconds
        has_duration_var = "duracion_seconds" in player_code or "duration_seconds" in player_code
        all_good &= print_status(
            "Duración en player",
            has_duration_var,
            "Código procesa duracion"
        )
        
    except Exception as e:
        print_status("Código del player", False, str(e))
    
    # 5. Verificar configuración de backend
    print("\n⚙️ Verificando Backend...")
    try:
        with open("websocket_manager.py", "r", encoding="utf-8") as f:
            ws_code = f.read()
        
        has_broadcast_duration = "duration_seconds" in ws_code and "broadcast_play_song" in ws_code
        all_good &= print_status(
            "WebSocket envía duración",
            has_broadcast_duration,
            "broadcast_play_song especifica duration_seconds"
        )
        
        with open("crud.py", "r", encoding="utf-8") as f:
            crud_code = f.read()
        
        # Buscar que las llamadas a broadcast_play_song incluyen duración
        has_duration_in_calls = "duracion_seconds or 0" in crud_code
        all_good &= print_status(
            "CRUD envía duración",
            has_duration_in_calls,
            "avanzar_cola_automaticamente() pasa duración"
        )
        
    except Exception as e:
        print_status("Configuración backend", False, str(e))
    
    # Resumen final
    print("\n" + "="*60)
    if all_good:
        print("✨ AUTOPLAY ESTÁ CORRECTAMENTE CONFIGURADO ✨")
        print("\n🎵 Próximos pasos:")
        print("1. Abre http://localhost:8000/static/player.html")
        print("2. Abre la consola (F12 → Console)")
        print("3. Agrega canciones desde el admin")
        print("4. Verifica que las canciones se reproducen automáticamente")
    else:
        print("⚠️ FALTAN CONFIGURACIONES O HAY ERRORES")
        print("\nRevisa los items marcados con ❌ arriba")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
