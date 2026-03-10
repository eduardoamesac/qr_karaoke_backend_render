from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import crud, schemas, models
import re # Importar para el filtro de groserías
import datetime
from app.database import SessionLocal
from app.auth import verify_token, log_admin_action
from app.utils.cache_manager import cache_manager as cache
router = APIRouter()

# Lista de palabras inapropiadas (puedes expandirla según sea necesario)
PROFANITY_LIST = {
    "puta","pene","vagina","parolo", "pendejo", "cabron", "mierda", "coño", "gilipollas", "joder",
    "culero", "chinga", "verga", "mamón", "idiota", "imbecil", "zorra",
    "maricon", "puto", "fuck", "shit", "asshole", "bitch", "cunt", "dick",
    "bastard", "whore", "faggot", "perra", "cagon", "caca", "culo", "lameculo","teta"
}

def contains_profanity(text: str) -> bool:
    """Verifica si el texto contiene palabras inapropiadas (case-insensitive y por palabra)."""
    normalized_text = re.sub(r'[_\-.]', ' ', text.lower()) # Reemplazar separadores comunes con espacios
    words = normalized_text.split()
    return any(word in PROFANITY_LIST for word in words)

# Dependencia para obtener la sesión de la base de datos en cada request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[schemas.Mesa], summary="Listar todas las mesas", dependencies=[Depends(verify_token)])
def get_mesas(db: Session = Depends(get_db)):
    """
    **[Admin]** Devuelve una lista de todas las mesas creadas en el sistema.
    """
    mesas = crud.get_mesas(db)
    return mesas

@router.post("/", response_model=schemas.Mesa, status_code=201, summary="Crear una nueva mesa")
def create_mesa_endpoint(
    mesa: schemas.MesaCreate, 
    db: Session = Depends(get_db),
    admin: dict = Depends(verify_token)
):
    """
    Crea una nueva mesa en el sistema con un nombre y un código QR único.
    El código QR debe ser único en todo el sistema.
    """
    log_admin_action(admin.get("sub"), "create_mesa", f"Mesa: {mesa.nombre}, QR: {mesa.qr_code}")
    db_mesa = crud.get_mesa_by_qr(db, qr_code=mesa.qr_code)
    if db_mesa:
        # db_mesa es un dict si viene del cache
        is_active = db_mesa.get('is_active', True)
        mesa_nombre = db_mesa.get('nombre')
        mesa_id = db_mesa.get('id')
        
        if not is_active:
            # Reactivar mesa si existe pero está inactiva
            crud.set_mesa_active_status(db, mesa_id=mesa_id, is_active=True)
            if mesa.nombre and mesa_nombre != mesa.nombre:
                # Actualizar nombre si es necesario (asumiendo que crud tiene esta lógica o la implementamos)
                db_mesa['nombre'] = mesa.nombre
                cache.update_mesa(mesa_id, db_mesa)
            return db_mesa
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"El código QR '{mesa.qr_code}' ya está registrado para la mesa '{mesa_nombre}'. Por favor, usa un código QR diferente."
            )
    try:
        return crud.create_mesa(db=db, mesa=mesa)
    except Exception as e:
        # Manejar colisiones de unique constraint en caso de condiciones de carrera
        try:
            from sqlalchemy.exc import IntegrityError
            if isinstance(e, IntegrityError):
                raise HTTPException(
                    status_code=400, 
                    detail=f"El código QR '{mesa.qr_code}' ya está registrado (conflicto de concurrencia). Intenta nuevamente."
                )
        except Exception:
            # si sqlalchemy no está disponible por alguna razón, continuar con manejo genérico
            pass
        # Si no es un IntegrityError, relanzamos como 500 para no ocultar errores inesperados
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{qr_code}/conectar", response_model=schemas.Usuario, summary="Conectar un usuario a una mesa")
def conectar_usuario_a_mesa(
    qr_code: str, usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)
):
    """
    Busca una mesa por su QR y crea un nuevo usuario asociado a ella.
    COMPATIBILIDAD: Acepta dos formatos de QR:
    - Nuevo: 'karaoke-mesa-XX-usuarioN' (N = 1-10) - Asigna usuario específico
    - Antiguo: 'karaoke-mesa-XX' - Asigna automáticamente al siguiente usuario disponible
    """
    # Intentar extraer el número de mesa y usuario del QR code (formato nuevo)
    match_nuevo = re.match(r'karaoke-mesa-(\d+)-usuario(\d+)', qr_code)
    
    if match_nuevo:
        # Formato nuevo: karaoke-mesa-05-usuario1
        mesa_numero = match_nuevo.group(1)
        usuario_numero = match_nuevo.group(2)
        
        # Validar que el número de usuario esté entre 1 y 10
        if not (1 <= int(usuario_numero) <= 10):
            raise HTTPException(
                status_code=400,
                detail=f"El número de usuario debe estar entre 1 y 10. Recibido: {usuario_numero}"
            )
    else:
        # Intentar formato antiguo: karaoke-mesa-05
        match_antiguo = re.match(r'karaoke-mesa-(\d+)$', qr_code)
        
        if not match_antiguo:
            raise HTTPException(
                status_code=400, 
                detail=f"El código QR '{qr_code}' no tiene un formato válido. Debe ser 'karaoke-mesa-XX' o 'karaoke-mesa-XX-usuarioN'."
            )
        
        mesa_numero = match_antiguo.group(1)
        
        # Buscar la mesa para asignar el siguiente usuario disponible
        qr_code_mesa_base = f"karaoke-mesa-{mesa_numero}"
        db_mesa_temp = crud.get_mesa_by_qr(db, qr_code=qr_code_mesa_base)
        
        if not db_mesa_temp:
            qr_code_mesa_base_int = f"karaoke-mesa-{int(mesa_numero)}"
            db_mesa_temp = crud.get_mesa_by_qr(db, qr_code=qr_code_mesa_base_int)
            
        if not db_mesa_temp:
            raise HTTPException(
                status_code=404, 
                detail=f"La mesa '{qr_code_mesa_base}' no existe. Por favor, contacta al personal."
            )
        
        mesa_id = db_mesa_temp.get('id')
        mesa_nombre = db_mesa_temp.get('nombre')
        
        # Encontrar el siguiente número de usuario disponible (1-10)
        usuario_numero = None
        for num in range(1, 11):
            nick_test = f"{mesa_nombre}-Usuario{num}"
            usuario_existente = db.query(models.Usuario).filter(
                models.Usuario.mesa_id == mesa_id,
                models.Usuario.nick == nick_test,
                models.Usuario.is_active == True
            ).first()
            
            if not usuario_existente:
                usuario_numero = str(num)
                break
        
        if not usuario_numero:
            raise HTTPException(
                status_code=429,
                detail="La mesa ha alcanzado el máximo de 10 usuarios activos. Por favor, usa un QR específico de usuario o intenta más tarde."
            )
    
    # Buscar la mesa base (sin el sufijo de usuario)
    qr_code_mesa_base = f"karaoke-mesa-{mesa_numero}"
    db_mesa = crud.get_mesa_by_qr(db, qr_code=qr_code_mesa_base)
    
    if not db_mesa:
        qr_code_mesa_base_int = f"karaoke-mesa-{int(mesa_numero)}"
        db_mesa = crud.get_mesa_by_qr(db, qr_code=qr_code_mesa_base_int)
        
    if not db_mesa:
        raise HTTPException(
            status_code=404, 
            detail=f"La mesa '{qr_code_mesa_base}' no existe. Por favor, contacta al personal."
        )

    is_active = db_mesa.get('is_active', True)
    mesa_id = db_mesa.get('id')
    mesa_nombre = db_mesa.get('nombre')

    if not is_active:
        raise HTTPException(
            status_code=403, 
            detail="Esta mesa se encuentra desactivada temporalmente. Por favor, contacta al personal."
        )
    
    # Generar automáticamente el nick basado en la mesa y el número de usuario
    nick_automatico = f"{mesa_nombre}-Usuario{usuario_numero}"
    
    # Verificar si ya existe un usuario con este número en esta mesa
    db_usuario_existente = db.query(models.Usuario).filter(
        models.Usuario.mesa_id == mesa_id,
        models.Usuario.nick == nick_automatico
    ).first()
    
    if db_usuario_existente:
        # Si el usuario ya existe y está activo, retornarlo
        if db_usuario_existente.is_active:
            return db_usuario_existente
        else:
            # Si existe pero está inactivo, reactivarlo
            db_usuario_existente.is_active = True
            db_usuario_existente.last_active = datetime.datetime.utcnow()
            db.commit()
            db.refresh(db_usuario_existente)
            return db_usuario_existente
    
    # Crear el nuevo usuario con el nick automático
    usuario_data = schemas.UsuarioCreate(nick=nick_automatico)
    return crud.create_usuario_en_mesa(db=db, usuario=usuario_data, mesa_id=mesa_id)

@router.get("/{mesa_id}/usuarios-conectados", response_model=List[schemas.UsuarioConectado], summary="Ver usuarios conectados a una mesa")
def get_usuarios_conectados(mesa_id: int, db: Session = Depends(get_db)):
    """
    Devuelve la lista de usuarios conectados actualmente a una mesa específica (máximo 10).
    Incluye nick, puntos, nivel y si están activos.
    """
    mesa = crud.get_mesa_by_id(db, mesa_id=mesa_id)
    if not mesa:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    
    usuarios_activos = db.query(models.Usuario).filter(
        models.Usuario.mesa_id == mesa_id,
        models.Usuario.is_active == True
    ).all()
    
    return usuarios_activos

@router.get("/{mesa_id}/payment-status", response_model=schemas.MesaEstadoPago, summary="Obtener estado de cuenta de una mesa")
def get_mesa_payment_status(mesa_id: int, db: Session = Depends(get_db)):
    """
    Endpoint público que devuelve el estado de cuenta de una mesa específica.
    Incluye total consumido, total pagado, saldo pendiente, y listas de consumos y pagos.
    Este endpoint es accesible desde la dashboard de usuarios para ver "Mi Cuenta".
    """
    status = crud.get_table_payment_status(db, mesa_id=mesa_id)
    if not status:
        raise HTTPException(status_code=404, detail="Mesa no encontrada.")
    return status

@router.get("/{qr_code}", response_model=schemas.Mesa, summary="Obtener información de una mesa por su QR")
def get_mesa_info(qr_code: str, db: Session = Depends(get_db)):
    """
    Devuelve la información pública de una mesa basada en su código QR.
    Soporta formato base ('karaoke-mesa-XX') y formato específico de usuario ('karaoke-mesa-XX-usuarioN').
    Este endpoint resuelve el error 404 al intentar cargar el dashboard con un QR de usuario.
    """
    # Intentar extraer el número de mesa si viene con formato de usuario
    match_nuevo = re.match(r'karaoke-mesa-(\d+)-usuario\d+', qr_code)
    if match_nuevo:
        mesa_numero = match_nuevo.group(1)
        qr_code_mesa_base = f"karaoke-mesa-{mesa_numero}"
    else:
        match_antiguo = re.match(r'karaoke-mesa-(\d+)$', qr_code)
        if match_antiguo:
            mesa_numero = match_antiguo.group(1)
            qr_code_mesa_base = f"karaoke-mesa-{mesa_numero}"
        else:
            # Si no hace match con nada, intentamos buscarlo tal cual por si acaso
            qr_code_mesa_base = qr_code

    db_mesa = crud.get_mesa_by_qr(db, qr_code=qr_code_mesa_base)
    
    if not db_mesa and (match_nuevo or match_antiguo):
        qr_code_mesa_base_int = f"karaoke-mesa-{int(mesa_numero)}"
        db_mesa = crud.get_mesa_by_qr(db, qr_code=qr_code_mesa_base_int)
        
    if not db_mesa:
        raise HTTPException(
            status_code=404, 
            detail=f"La mesa '{qr_code}' no existe. Por favor, verifica el código QR."
        )
        
    return db_mesa