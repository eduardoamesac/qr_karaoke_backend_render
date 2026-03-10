from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services import websocket_manager
import asyncio

router = APIRouter()

class ReactionPayload(BaseModel):
    """
    Define la estructura del payload para una reacción.
    """
    reaction: str  # El emoticono, ej: "😊"
    sender: str    # El nick del usuario que lo envía

@router.post("/reaction", status_code=202, summary="Enviar una reacción a todos")
async def send_reaction(payload: ReactionPayload):
    """
    **[Público]** Endpoint para que cualquier usuario o el admin envíe una
    reacción (emoticono) que será visible para todos en tiempo real.
    """
    # Usamos asyncio.create_task para enviar la notificación en segundo plano
    # y devolver la respuesta al cliente inmediatamente, sin esperar.
    asyncio.create_task(
        websocket_manager.manager.broadcast_reaction(payload.model_dump())
    )
    return {"message": "Reaction sent"}