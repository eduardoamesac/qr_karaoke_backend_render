import subprocess
import sys
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.auth import verify_token
from app.services.settings_storage import load_settings
from app.database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/settings", summary="Obtener configuraciones públicas del player2")
def get_player2_public_settings(
    local_id: Optional[int] = Query(None),
    slug: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    settings = load_settings()
    owner_logo = settings.get("owner_logo", None)
    app_name = settings.get("app_name", "QR Karaoke")
    local_nombre = None
    local_logo = None
    resolved_local_id = local_id

    if local_id or slug:
        from app.db.models.local import Local
        query = db.query(Local)
        if local_id:
            loc = query.filter(Local.id == local_id).first()
        else:
            loc = query.filter(Local.slug == slug).first()

        if loc:
            resolved_local_id = loc.id
            local_nombre = loc.nombre
            local_logo = loc.logo_url
            if loc.logo_url:
                owner_logo = loc.logo_url

    return {
        "owner_logo": owner_logo,
        "local_logo": local_logo,
        "local_nombre": local_nombre,
        "local_id": resolved_local_id,
        "app_name": local_nombre or app_name
    }


@router.get("/", summary="Cargar página del Reproductor 2 (Onboarding/TV)")
@router.get("", include_in_schema=False)
def get_player2_page():
    return FileResponse("static/player2.html")

player_process = None

@router.post("/launch", summary="Lanzar Reproductor Nativo localmente (Admin)")
def launch_player(
    local_id: Optional[int] = Query(None),
    api_key: dict = Depends(verify_token)
):
    global player_process
    if player_process and player_process.poll() is None:
        return {"status": "running", "message": "El reproductor nativo ya está en ejecución."}
    
    python_exe = sys.executable
    cmd = [python_exe, "launch_player2.py"]
    if local_id:
        cmd.extend(["--local", str(local_id)])
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
