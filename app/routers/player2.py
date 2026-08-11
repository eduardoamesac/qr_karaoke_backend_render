import subprocess
import sys
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.auth import verify_token
from app.services.settings_storage import load_settings

router = APIRouter()

@router.get("/settings", summary="Obtener configuraciones públicas del player2")
def get_player2_public_settings():
    settings = load_settings()
    return {
        "owner_logo": settings.get("owner_logo", None),
        "app_name": settings.get("app_name", "QR Karaoke")
    }


@router.get("/", summary="Cargar página del Reproductor 2 (Onboarding/TV)")
@router.get("", include_in_schema=False)
def get_player2_page():
    return FileResponse("static/player2.html")

player_process = None

@router.post("/launch", summary="Lanzar Reproductor Nativo localmente (Admin)")
def launch_player(api_key: dict = Depends(verify_token)):
    global player_process
    if player_process and player_process.poll() is None:
        return {"status": "running", "message": "El reproductor nativo ya está en ejecución."}
    
    python_exe = sys.executable
    cmd = [python_exe, "launch_player2.py"]
    try:
        # Lanzar en segundo plano sin bloquear el servidor
        player_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"status": "launched", "message": "Reproductor nativo lanzado correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al lanzar el reproductor nativo: {str(e)}")


@router.post("/kill", summary="Cerrar Reproductor Nativo localmente (Admin)")
def kill_player(api_key: dict = Depends(verify_token)):
    global player_process
    if not player_process or player_process.poll() is not None:
        return {"status": "stopped", "message": "El reproductor nativo no está en ejecución."}
    
    try:
        player_process.terminate()
        player_process.wait(timeout=3)
    except Exception:
        try:
            player_process.kill()
        except Exception:
            pass
    player_process = None
    return {"status": "stopped", "message": "Reproductor nativo detenido con éxito."}


@router.get("/status", summary="Obtener estado del Reproductor Nativo local (Admin)")
def get_player_status(api_key: dict = Depends(verify_token)):
    global player_process
    is_running = player_process is not None and player_process.poll() is None
    return {"running": is_running}
