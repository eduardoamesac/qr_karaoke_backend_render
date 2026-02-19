
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, or_, and_, desc
import secrets
from typing import List, Optional
import datetime
import models, schemas
from timezone_utils import now_bogota, safe_datetime_diff, ensure_aware
from decimal import Decimal # Importar Decimal
from settings_storage import load_settings

def get_mesa_by_qr(db: Session, qr_code: str):
    """Busca una mesa por su cÃƒÂƒÃ‚Â³digo QR."""
    return db.query(models.Mesa).filter(models.Mesa.qr_code == qr_code).first()

def get_mesas(db: Session):
    """Devuelve todas las mesas de la base de datos."""
    return db.query(models.Mesa).order_by(models.Mesa.id).all()

def create_mesa(db: Session, mesa: schemas.MesaCreate):
    """Crea una nueva mesa en la base de datos."""
    db_mesa = models.Mesa(nombre=mesa.nombre, qr_code=mesa.qr_code)
    db.add(db_mesa)
    db.commit()
    db.refresh(db_mesa)
    return db_mesa

def create_usuario_en_mesa(db: Session, usuario: schemas.UsuarioCreate, mesa_id: int):
    """Crea un nuevo usuario y lo asocia a una mesa."""
    db_usuario = models.Usuario(nick=usuario.nick, mesa_id=mesa_id)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

def get_usuario_by_id(db: Session, usuario_id: int):
    """Busca un usuario por su ID."""
    return db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

def get_usuario_by_nick(db: Session, nick: str):
    """Busca un usuario por su nick (case-insensitive)."""
    return db.query(models.Usuario).filter(func.lower(models.Usuario.nick) == func.lower(nick)).first()

def get_total_consumido_por_usuario(db: Session, usuario_id: int):
    """Calcula el total consumido por un usuario."""
    return db.query(func.sum(models.Consumo.valor_total)).filter(models.Consumo.usuario_id == usuario_id).scalar() or 0

def get_canciones_por_usuario(db: Session, usuario_id: int):
    """Busca todas las canciones de un usuario especÃƒÂƒÃ‚Â­fico."""
    return db.query(models.Cancion).filter(models.Cancion.usuario_id == usuario_id).order_by(
        case((models.Cancion.orden_manual.is_(None), 1), else_=0),
        models.Cancion.orden_manual.asc(),
        models.Cancion.created_at.asc()
    ).all()

def create_cancion_para_usuario(db: Session, cancion: schemas.CancionCreate, usuario_id: int):
    """Crea una nueva canción y la asocia a un usuario."""
    from queue_manager import queue_manager
    # Usar model_dump() (Pydantic v2) en vez de dict()
    db_cancion = models.Cancion(**cancion.model_dump(), usuario_id=usuario_id)
    db.add(db_cancion)
    db.commit()
    db.refresh(db_cancion)
    
    # Sincronizar cache
    queue_manager.refresh_all(db)
    return db_cancion

def check_if_song_in_user_list(db: Session, usuario_id: int, youtube_id: str):
    """
    Verifica si ALGÃƒÂƒÃ‚ÂšN USUARIO DE LA MISMA MESA ya tiene esta canciÃƒÂƒÃ‚Â³n en la cola.
    CAMBIO: Ahora verifica a nivel de mesa para evitar duplicados entre usuarios de la misma mesa.
    """
    # Obtener el usuario y su mesa
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario or not usuario.mesa_id:
        return None
    
    # Buscar si algÃƒÂƒÃ‚Âºn usuario de la misma mesa ya tiene esta canciÃƒÂƒÃ‚Â³n en cola
    return db.query(models.Cancion).join(
        models.Usuario, models.Cancion.usuario_id == models.Usuario.id
    ).filter(
        models.Usuario.mesa_id == usuario.mesa_id,
        models.Cancion.youtube_id == youtube_id,
        models.Cancion.estado.in_(['pendiente', 'aprobado', 'reproduciendo'])
    ).first()
def get_cancion_by_id(db: Session, cancion_id: int):
    """Busca una canciÃƒÂƒÃ‚Â³n por su ID."""
    return db.query(models.Cancion).filter(models.Cancion.id == cancion_id).first()

def get_cancion_actual(db: Session):
    """
    Retorna la canciÃƒÂƒÃ‚Â³n que estÃƒÂƒÃ‚Â¡ actualmente en reproducciÃƒÂƒÃ‚Â³n,
    o None si no hay ninguna activa.
    """
    return db.query(models.Cancion).filter(models.Cancion.estado == "reproduciendo").first()


def get_canciones_pendientes(db: Session):
    """Busca todas las canciones en estado 'pendiente'."""
    return db.query(models.Cancion).filter(models.Cancion.estado == 'pendiente').order_by(models.Cancion.id).all()

def get_duracion_total_cola_aprobada(db: Session) -> int:
    """Calcula la suma de la duraciÃƒÂƒÃ‚Â³n de todas las canciones aprobadas."""
    total_seconds = db.query(func.sum(models.Cancion.duracion_seconds)).filter(models.Cancion.estado == 'aprobado').scalar()
    return total_seconds or 0

def update_cancion_estado(db: Session, cancion_id: int, nuevo_estado: str):
    """Actualiza el estado de una canción específica."""
    from queue_manager import queue_manager
    db_cancion = db.query(models.Cancion).filter(models.Cancion.id == cancion_id).first()
    if db_cancion:
        db_cancion.estado = nuevo_estado
        db.commit()
        db.refresh(db_cancion)
        
        # Sincronizar cache
        queue_manager.refresh_all(db)
    return db_cancion

def get_cola_priorizada(db: Session):
    """
    Obtiene la lista de canciones aprobadas, ordenadas por el algoritmo de "Cola Justa".
    
    Reglas:
    1. Orden Manual: Las canciones con `orden_manual` tienen prioridad absoluta y mantienen su orden relativo.
    2. AgrupaciÃƒÂƒÃ‚Â³n por Mesa: El resto de canciones se agrupan por su mesa de origen.
    3. CategorÃƒÂƒÃ‚Â­as de Mesa (basado en consumo total de la mesa):
        - ORO (> $150.000): Cupo de 3 canciones por turno.
        - PLATA (> $50.000): Cupo de 2 canciones por turno.
        - BRONCE (<= $50.000): Cupo de 1 canciÃƒÂƒÃ‚Â³n por turno.
    4. Round Robin: Se iteran las mesas (ordenadas por la hora de llegada de su primera canciÃƒÂƒÃ‚Â³n pendiente)
       y se toman N canciones (segÃƒÂƒÃ‚Âºn su cupo) en cada turno.
    """
    from queue_manager import queue_manager
    return queue_manager.get_queue(db)

def get_producto_by_nombre(db: Session, nombre: str):
    """Busca un producto por su nombre."""
    return db.query(models.Producto).filter(models.Producto.nombre == nombre).first()

def get_productos(db: Session, skip: int = 0, limit: int = 100):
    """Obtiene una lista de todos los productos del catÃƒÂƒÃ‚Â¡logo."""
    return db.query(models.Producto).offset(skip).limit(limit).all()

def create_producto(db: Session, producto: schemas.ProductoCreate):
    """Crea un nuevo producto en el catÃƒÂƒÃ‚Â¡logo."""
    # Aseguramos que el producto se cree como activo por defecto.
    producto_data = producto.model_dump()
    # El schema ProductoCreate ya tiene `is_active` con un valor por defecto.
    # Al pasarlo directamente, evitamos el error de "multiple values for keyword argument".
    # Si el schema no lo tuviera, podrÃƒÂƒÃ‚Â­amos hacer `producto_data.pop('is_active', None)`
    # antes de pasarlo como argumento extra.
    db_producto = models.Producto(**producto_data)
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto

def get_producto_by_id(db: Session, producto_id: int):
    """Busca un producto por su ID."""
    return db.query(models.Producto).filter(models.Producto.id == producto_id).first()

def update_producto_imagen(db: Session, producto_id: int, imagen_url: str):
    """Actualiza solo la URL de la imagen de un producto."""
    db_producto = get_producto_by_id(db, producto_id)
    if db_producto:
        db_producto.imagen_url = imagen_url
        db.flush()  # Sincronizar cambios sin hacer commit
        db.refresh(db_producto)  # Obtener datos actualizados
        db.commit()  # Hacer commit de la transacciÃ³n
    return db_producto

def create_consumo_para_usuario(db: Session, consumo: schemas.ConsumoCreate, usuario_id: int):
    """
    Crea un nuevo consumo. CAMBIO: El consumo se asigna a la MESA, no al usuario individual.
    Todos los consumos de los 10 usuarios en una mesa se consolidan en la cuenta de la mesa.
    """
    # 1. Obtener el usuario y su mesa
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None, "Usuario no encontrado."
    
    if not db_usuario.mesa_id:
        return None, "El usuario no esta activado¡ asociado a ninguna mesa."

    # 2. Obtener el producto del catÃƒÂƒÃ‚Â¡logo para saber su precio
    db_producto = db.query(models.Producto).filter(models.Producto.id == consumo.producto_id).first()
    if not db_producto:
        return None, "Producto no encontrado en el catalogo¡logo."

    if db_producto.stock < consumo.cantidad:
        return None, f"No hay suficiente stock para '{db_producto.nombre}'. Disponible: {db_producto.stock}"

    if consumo.cantidad <= 0:
        return None, "La cantidad debe ser mayor que cero."

    if not db_producto.is_active:
        return None, "El producto no esta disponible¡ disponible actualmente."

    # 3. Calcular el valor total de la transaccion
    valor_total_transaccion = db_producto.valor * consumo.cantidad

    # 4. Crear el registro de consumo ASIGNADO A LA MESA (no al usuario)
    # Obtener o crear cuenta activa
    active_cuenta = get_active_cuenta(db, db_usuario.mesa_id)
    if not active_cuenta:
         active_cuenta = create_new_active_cuenta(db, db_usuario.mesa_id)

    db_consumo = models.Consumo(
        producto_id=consumo.producto_id,
        cantidad=consumo.cantidad,
        valor_total=valor_total_transaccion,
        mesa_id=db_usuario.mesa_id,  # CAMBIO: Asignar a mesa
        usuario_id=usuario_id,  # Mantener referencia al usuario que pidiÃƒÂƒÃ‚Â³ (tracking)
        cuenta_id=active_cuenta.id
    )

    # 5. Descontar del stock
    db_producto.stock -= consumo.cantidad

    # 6. Otorgar puntos al usuario individual (ej: 1 punto por cada 10 de moneda gastados)
    db_usuario.puntos += int(valor_total_transaccion / 10)
    
    # NUEVO: Agregar crÃ©ditos de canciones por el valor del producto en pesos
    # 5000 pesos = 5000 crÃ©ditos (100 crÃ©ditos se pierden cada minuto)
    credit_value = int(float(valor_total_transaccion))
    add_song_credits(db, usuario_id, credit_value)

    db.add(db_consumo)
    db.commit()
    db.refresh(db_consumo)

    # 7. Actualizar el nivel del usuario basado en su consumo individual
    total_consumido_usuario = db.query(func.sum(models.Consumo.valor_total)).filter(
        models.Consumo.usuario_id == usuario_id
    ).scalar() or 0

    SILVER_THRESHOLD = 50.0
    GOLD_THRESHOLD = 150.0

    if total_consumido_usuario >= GOLD_THRESHOLD:
        db_usuario.nivel = "oro"
    elif total_consumido_usuario >= SILVER_THRESHOLD:
        db_usuario.nivel = "plata"

    db.commit()
    db.refresh(db_usuario)
    return db_consumo, None

def create_pedido_from_carrito(db: Session, carrito: schemas.CarritoCreate, usuario_id: int):
    """
    Crea mÃƒÂƒÃ‚Âºltiples registros de consumo a partir de un carrito de compras.
    CAMBIO: Los consumos se asignan a la MESA, no al usuario individual.
    Toda la operaciÃƒÂƒÃ‚Â³n se maneja como una ÃƒÂƒÃ‚Âºnica transacciÃƒÂƒÃ‚Â³n.
    """
    SILVER_THRESHOLD = 50.0
    GOLD_THRESHOLD = 150.0

    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None, "Usuario no encontrado."
    
    if not db_usuario.mesa_id:
        return None, "El usuario no estÃƒÂƒÃ‚Â¡ asociado a ninguna mesa."

    consumos_creados = []
    valor_total_pedido = Decimal(0)

    try:
        # Iteramos sobre una copia para poder modificarla si es necesario
        for item in carrito.items:
            if item.cantidad <= 0:
                raise ValueError("La cantidad de cada producto debe ser mayor que cero.")

            db_producto = db.query(models.Producto).filter(models.Producto.id == item.producto_id).first()
            if not db_producto:
                raise ValueError(f"Producto con ID {item.producto_id} no encontrado.")
            if not db_producto.is_active:
                raise ValueError(f"El producto '{db_producto.nombre}' no estÃƒÂƒÃ‚Â¡ disponible.")
            if db_producto.stock < item.cantidad:
                raise ValueError(f"No hay stock suficiente para '{db_producto.nombre}'. Disponible: {db_producto.stock}.")

            # Calculamos el valor de esta lÃƒÂƒÃ‚Â­nea del pedido
            valor_linea = db_producto.valor * item.cantidad
            valor_total_pedido += valor_linea

            # Asegurar cuenta activa (solo una vez)
            active_cuenta = get_active_cuenta(db, db_usuario.mesa_id)
            if not active_cuenta:
                active_cuenta = create_new_active_cuenta(db, db_usuario.mesa_id)

            # Creamos el objeto Consumo ASIGNADO A LA MESA
            db_consumo = models.Consumo(
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                valor_total=valor_linea,
                mesa_id=db_usuario.mesa_id,  # CAMBIO: Asignar a mesa
                usuario_id=usuario_id,  # Mantener referencia al usuario que pidiÃƒÂƒÃ‚Â³
                cuenta_id=active_cuenta.id
            )
            db.add(db_consumo)
            consumos_creados.append(db_consumo)

            # Descontamos el stock
            db_producto.stock -= item.cantidad

        # Si todo fue bien, actualizamos los puntos y el nivel del usuario INDIVIDUAL
        db_usuario.puntos += int(valor_total_pedido / 10)
        
        # NUEVO: Agregar crÃ©ditos de canciones por el total del pedido
        credit_value = int(float(valor_total_pedido))
        add_song_credits(db, usuario_id, credit_value)
        total_consumido_historico = (db.query(func.sum(models.Consumo.valor_total)).filter(
            models.Consumo.usuario_id == usuario_id
        ).scalar() or 0) + valor_total_pedido

        if total_consumido_historico >= GOLD_THRESHOLD:
            db_usuario.nivel = "oro"
        elif total_consumido_historico >= SILVER_THRESHOLD:
            db_usuario.nivel = "plata"

        db.commit() # Guardamos todos los cambios a la vez
        for consumo in consumos_creados:
            db.refresh(consumo)
        return consumos_creados, None
    except ValueError as e:
        db.rollback() # Si algo falla, revertimos TODOS los cambios de esta transacciÃƒÂƒÃ‚Â³n
        return None, str(e)

def marcar_cancion_actual_como_cantada(db: Session):
    """
    Busca la canciÃƒÂƒÃ‚Â³n que se estÃƒÂƒÃ‚Â¡ reproduciendo, la marca como 'cantada' y le da puntos al usuario.
    Simula una puntuaciÃƒÂƒÃ‚Â³n de IA.
    """
    import os
    import random_scorer # Importamos nuestro nuevo mÃƒÂƒÃ‚Â³dulo de IA

    # 1. Buscar la canciÃƒÂƒÃ‚Â³n que estÃƒÂƒÃ‚Â¡ actualmente en estado 'reproduciendo'
    cancion_actual = db.query(models.Cancion).filter(models.Cancion.estado == "reproduciendo").first()
    
    if not cancion_actual:
        return None  # No hay ninguna canciÃƒÂƒÃ‚Â³n reproduciÃƒÂƒÃ‚Â©ndose
    
    # 2. Calcular puntaje solo si es modo karaoke
    if cancion_actual.is_karaoke:
        puntuacion = random_scorer.calculate_score(cancion_actual.youtube_id, "")
        cancion_actual.puntuacion_ia = puntuacion
    else:
        cancion_actual.puntuacion_ia = 0
        puntuacion = 0

    # 3. Actualizar el estado de la canciÃƒÂƒÃ‚Â³n a 'cantada'
    cancion_actual.estado = "cantada"
    cancion_actual.finished_at = now_bogota()

    # 4. Dar puntos al usuario por cantar (puntos base + puntaje de IA)
    if cancion_actual.usuario:
        cancion_actual.usuario.puntos += (10 + puntuacion) # 10 puntos base + el puntaje de la IA

    db.commit()
    db.refresh(cancion_actual)
    
    # Sincronizar cache
    from queue_manager import queue_manager
    queue_manager.refresh_all(db)
    return cancion_actual

def marcar_siguiente_como_reproduciendo(db: Session):
    """Busca la siguiente canciÃƒÂƒÃ‚Â³n en la cola y la marca como 'reproduciendo'."""
    from queue_manager import queue_manager
    return queue_manager.pop_next_song(db)

def get_tiempo_espera_para_cancion(db: Session, cancion_id: int) -> int:
    """
    Calcula el tiempo de espera estimado en segundos para una canciÃƒÂƒÃ‚Â³n especÃƒÂƒÃ‚Â­fica.
    """
    # 1. Obtener la canciÃƒÂƒÃ‚Â³n que se estÃƒÂƒÃ‚Â¡ reproduciendo
    cancion_actual = db.query(models.Cancion).filter(models.Cancion.estado == "reproduciendo").first()
    
    tiempo_espera_total = 0
    if cancion_actual:
        tiempo_transcurrido = (now_bogota() - cancion_actual.started_at).total_seconds()
        tiempo_restante_actual = max(0, cancion_actual.duracion_seconds - tiempo_transcurrido)
        tiempo_espera_total += tiempo_restante_actual

    # 2. Obtener la cola de canciones aprobadas
    cola_aprobada = get_cola_priorizada(db)

    # 3. Sumar la duraciÃƒÂƒÃ‚Â³n de las canciones que estÃƒÂƒÃ‚Â¡n antes de la nuestra
    for cancion_en_cola in cola_aprobada:
        if cancion_en_cola.id == cancion_id:
            # Llegamos a nuestra canciÃƒÂƒÃ‚Â³n, dejamos de sumar
            break
        tiempo_espera_total += cancion_en_cola.duracion_seconds
    else:
        # Si la canciÃƒÂƒÃ‚Â³n no se encuentra en la cola (ya se cantÃƒÂƒÃ‚Â³, fue rechazada, etc.)
        # devolvemos -1 para indicar que no hay tiempo de espera.
        return -1

    return int(tiempo_espera_total)

def get_ranking_usuarios(db: Session):
    """
    Obtiene un ranking de todos los usuarios ordenado por su consumo total.
    Devuelve una lista de tuplas (Usuario, total_consumido).
    """
    # Subconsulta para calcular el consumo total por cada usuario
    consumo_total_subq = (
        db.query(
            models.Consumo.usuario_id.label("usuario_id"),
            func.sum(models.Consumo.valor_total).label("total_consumido"),
        )
        .group_by(models.Consumo.usuario_id)
        .subquery()
    )

    # Consulta principal que une usuarios con su consumo total y ordena
    return db.query(models.Usuario, func.coalesce(consumo_total_subq.c.total_consumido, 0).label("total_consumido_calc")).outerjoin(consumo_total_subq, models.Usuario.id == consumo_total_subq.c.usuario_id).order_by(func.coalesce(consumo_total_subq.c.total_consumido, 0).desc()).all()

def reset_database_for_new_night(db: Session):
    """
    Borra todos los datos de las tablas transaccionales para empezar una nueva noche.
    El orden es importante para respetar las restricciones de clave forÃƒÂƒÃ‚Â¡nea.
    """
    # El orden de borrado es inverso al de creaciÃƒÂƒÃ‚Â³n de dependencias
    db.query(models.Consumo).delete()
    db.query(models.Cancion).delete()
    db.query(models.Usuario).delete()
    db.query(models.Mesa).delete()
    
    db.commit()

def get_canciones_mas_cantadas(db: Session, limit: int = 10):
    """
    Obtiene un reporte de las canciones mÃƒÂƒÃ‚Â¡s cantadas, agrupadas y contadas.
    """
    return (
        db.query(
            models.Cancion.titulo,
            models.Cancion.youtube_id,
            func.count(models.Cancion.id).label("veces_cantada"),
        )
        .filter(models.Cancion.estado == "cantada")
        .group_by(models.Cancion.titulo, models.Cancion.youtube_id)
        .order_by(func.count(models.Cancion.id).desc())
        .limit(limit)
        .all()
    )

def delete_cancion(db: Session, cancion_id: int):
    """Elimina una canción de la base de datos por su ID."""
    from queue_manager import queue_manager
    db_cancion = db.query(models.Cancion).filter(models.Cancion.id == cancion_id).first()
    if db_cancion:
        db.delete(db_cancion)
        db.commit()
        # Sincronizar cache
        queue_manager.refresh_all(db)
        return True
    return False

def get_productos_mas_consumidos(db: Session, limit: int = 10):
    """
    Obtiene un reporte de los productos mÃƒÂƒÃ‚Â¡s consumidos, agrupados y sumada su cantidad.
    """
    return (
        db.query(
            models.Producto.nombre,
            func.sum(models.Consumo.cantidad).label("cantidad_total"),
        )
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .group_by(models.Producto.nombre)
        .order_by(func.sum(models.Consumo.cantidad).desc())
        .limit(limit)
        .all()
    )

def delete_producto(db: Session, producto_id: int):
    """Elimina un producto de la base de datos por su ID."""
    db_producto = db.query(models.Producto).options(joinedload(models.Producto.consumos)).filter(models.Producto.id == producto_id).first()
    if not db_producto:
        return None, "Producto no encontrado."

    # Si el producto tiene consumos asociados, no lo borramos, solo lo desactivamos.
    if db_producto.consumos:
        db_producto.is_active = False
        db.commit()
        db.refresh(db_producto)
        return db_producto, "El producto tiene consumos asociados y ha sido desactivado en lugar de borrado."
    else:
        # Si no hay consumos, se puede borrar de forma segura.
        db.delete(db_producto)
        db.commit()
        return None, "Producto eliminado permanentemente."

def get_total_ingresos(db: Session):
    """Calcula la suma total de todos los pagos recibidos durante la noche."""
    total = db.query(func.sum(models.Pago.monto)).scalar()
    return total or 0

def get_ganancias_totales(db: Session):
    """
    Calcula las ganancias reales: (precio_venta - costo) * cantidad
    Solo de productos que ya fueron pagados (mesas con pagos registrados).
    """
    from decimal import Decimal
    
    # Obtener todas las mesas que tienen al menos un pago
    mesas_con_pagos = db.query(models.Pago.mesa_id).distinct().all()
    mesas_ids = [mesa_id for (mesa_id,) in mesas_con_pagos]
    
    if not mesas_ids:
        return Decimal("0")
    
    # Obtener todos los consumos de esas mesas
    consumos = (
        db.query(models.Consumo)
        .join(models.Usuario)
        .filter(models.Usuario.mesa_id.in_(mesas_ids))
        .all()
    )
    
    ganancias_total = Decimal("0")
    for consumo in consumos:
        producto = consumo.producto
        # Ganancia = (precio_venta - costo) * cantidad
        ganancia_item = (producto.valor - producto.costo) * consumo.cantidad
        ganancias_total += ganancia_item
    
    return ganancias_total


def get_ingresos_por_mesa(db: Session):
    """
    Calcula los ingresos totales (pagos recibidos) agrupados por cada mesa.
    """
    return (
        db.query(
            models.Mesa.nombre,
            func.sum(models.Pago.monto).label("ingresos_totales")
        )
        .join(models.Pago, models.Mesa.id == models.Pago.mesa_id)
        .group_by(models.Mesa.nombre)
        .order_by(func.sum(models.Pago.monto).desc())
        .all()
    )

def reordenar_cola_manual(db: Session, canciones_ids: List[int]):
    """
    Actualiza el orden manual de las canciones en la cola.
    """
    # Primero, reseteamos el orden manual de todas las canciones aprobadas
    db.query(models.Cancion).filter(models.Cancion.estado == 'aprobado').update({"orden_manual": None})
    
    # Luego, asignamos el nuevo orden
    for i, cancion_id in enumerate(canciones_ids):
        db.query(models.Cancion).filter(models.Cancion.id == cancion_id).update({"orden_manual": i + 1})
    
    db.commit()
    # Sincronizar cache unificado
    from queue_manager import queue_manager
    queue_manager.refresh_all(db)
    return True

def get_usuarios_sin_consumo(db: Session):
    """
    Obtiene una lista de todos los usuarios que no han realizado ningÃƒÂƒÃ‚Âºn consumo.
    """
    return (
        db.query(models.Usuario)
        .outerjoin(models.Consumo)
        .group_by(models.Usuario.id)
        .having(func.count(models.Consumo.id) == 0)
        .all()
    )

def get_mesa_by_id(db: Session, mesa_id: int):
    """Busca una mesa por su ID."""
    return db.query(models.Mesa).filter(models.Mesa.id == mesa_id).first()

def delete_mesa(db: Session, mesa_id: int):
    """Elimina una mesa de la base de datos por su ID."""
    db_mesa = db.query(models.Mesa).filter(models.Mesa.id == mesa_id).first()
    if db_mesa:
        db.delete(db_mesa)
        db.commit()

def move_song_to_top(db: Session, cancion_id: int):
    """
    Mueve una canciÃƒÂƒÃ‚Â³n especÃƒÂƒÃ‚Â­fica al principio de la cola manual.
    """
    # 1. Validar que la canciÃƒÂƒÃ‚Â³n existe y estÃƒÂƒÃ‚Â¡ aprobada
    cancion_a_mover = db.query(models.Cancion).filter(
        models.Cancion.id == cancion_id,
        models.Cancion.estado == 'aprobado'
    ).first()

    if not cancion_a_mover:
        return None

    # 2. Encontrar el valor de orden manual mÃƒÂƒÃ‚Â¡s bajo actual
    min_orden = db.query(func.min(models.Cancion.orden_manual)).scalar()

    nuevo_orden = 1
    if min_orden is not None:
        nuevo_orden = min_orden - 1
    
    # 3. Asignar el nuevo orden a la canciÃƒÂƒÃ‚Â³n
    cancion_a_mover.orden_manual = nuevo_orden
    db.commit()
    db.refresh(cancion_a_mover)
    
    # Sincronizar cache unificado
    from queue_manager import queue_manager
    queue_manager.refresh_all(db)
    return cancion_a_mover

def get_canciones_cantadas_por_usuario(db: Session):
    """
    Obtiene un reporte de la cantidad de canciones cantadas por cada usuario.
    """
    return (
        db.query(
            models.Usuario.nick,
            func.count(models.Cancion.id).label("canciones_cantadas"),
        )
        .join(models.Cancion, models.Usuario.id == models.Cancion.usuario_id)
        .filter(models.Cancion.estado == "cantada")
        .group_by(models.Usuario.nick)
        .order_by(func.count(models.Cancion.id).desc())
        .all()
    )

def update_usuario_nick(db: Session, usuario_id: int, nuevo_nick: str):
    """
    Actualiza el nick de un usuario especÃƒÂƒÃ‚Â­fico.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if db_usuario:
        db_usuario.nick = nuevo_nick
        db.commit()
        db.refresh(db_usuario)
    return db_usuario

def get_ingresos_promedio_por_usuario(db: Session):
    """
    Calcula los ingresos promedio por cada usuario que ha consumido.
    """
    # Calcular ingresos totales
    total_ingresos = db.query(func.sum(models.Consumo.valor_total)).scalar() or 0

    # Contar el nÃƒÂƒÃ‚Âºmero de usuarios ÃƒÂƒÃ‚Âºnicos con consumo
    usuarios_con_consumo = db.query(models.Consumo.usuario_id).distinct().count()

    if usuarios_con_consumo == 0:
        return 0

    return total_ingresos / usuarios_con_consumo

def update_usuario_mesa(db: Session, usuario_id: int, nueva_mesa_id: int):
    """
    Actualiza la mesa de un usuario especÃƒÂƒÃ‚Â­fico.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if db_usuario:
        db_usuario.mesa_id = nueva_mesa_id
        db.commit()
        db.refresh(db_usuario)
    return db_usuario

def get_usuarios_una_cancion(db: Session):
    """
    Obtiene una lista de usuarios que han cantado exactamente una canciÃƒÂƒÃ‚Â³n.
    """
    return (
        db.query(models.Usuario)
        .join(models.Cancion, models.Usuario.id == models.Cancion.usuario_id)
        .filter(models.Cancion.estado == "cantada")
        .group_by(models.Usuario.id)
        .having(func.count(models.Cancion.id) == 1)
        .all()
    )

def add_puntos_a_usuario(db: Session, usuario_id: int, puntos_a_anadir: int):
    """
    AÃƒÂƒÃ‚Â±ade una cantidad de puntos a un usuario especÃƒÂƒÃ‚Â­fico.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if db_usuario:
        db_usuario.puntos += puntos_a_anadir
        db.commit()
        db.refresh(db_usuario)
    return db_usuario

def get_mesas_vacias(db: Session):
    """
    Obtiene una lista de todas las mesas que no tienen usuarios conectados.
    """
    return (
        db.query(models.Mesa)
        .outerjoin(models.Usuario)
        .group_by(models.Mesa.id)
        .having(func.count(models.Usuario.id) == 0)
        .all()
    )

def delete_usuario(db: Session, usuario_id: int):
    """
    Elimina un usuario y todos sus datos asociados (canciones, consumos).
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None

    # Borrar datos dependientes primero para evitar errores de clave forÃƒÂƒÃ‚Â¡nea
    db.query(models.Consumo).filter(models.Consumo.usuario_id == usuario_id).delete(synchronize_session=False)
    db.query(models.Cancion).filter(models.Cancion.usuario_id == usuario_id).delete(synchronize_session=False)

    # Finalmente, borrar el usuario
    db.delete(db_usuario)
    db.commit()
    return db_usuario

def get_ingresos_promedio_por_usuario_por_mesa(db: Session):
    """
    Calcula los ingresos promedio por usuario para cada mesa.
    """
    # Consulta que calcula el total consumido y el nÃƒÂƒÃ‚Âºmero de usuarios ÃƒÂƒÃ‚Âºnicos por mesa
    return (
        db.query(
            models.Mesa.nombre,
            (
                func.coalesce(func.sum(models.Consumo.valor_total), 0) / 
                func.greatest(func.count(func.distinct(models.Usuario.id)), 1)
            ).label("ingresos_promedio")
        )
        .select_from(models.Mesa)
        .outerjoin(models.Usuario, models.Mesa.id == models.Usuario.mesa_id)
        .outerjoin(models.Consumo, models.Usuario.id == models.Consumo.usuario_id)
        .group_by(models.Mesa.nombre)
        .order_by(func.coalesce(func.sum(models.Consumo.valor_total), 0).desc())
        .all()
    )

def is_nick_banned(db: Session, nick: str):
    """Verifica si un nick estÃƒÂƒÃ‚Â¡ en la lista de baneados (case-insensitive)."""
    return db.query(models.BannedNick).filter(models.BannedNick.nick.ilike(nick)).first() is not None

def ban_usuario(db: Session, usuario_id: int):
    """
    Banea a un usuario: aÃƒÂƒÃ‚Â±ade su nick a la lista de baneados y luego lo elimina.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None

    # 1. AÃƒÂƒÃ‚Â±adir el nick a la lista de baneados si no existe
    nick_baneado_existente = db.query(models.BannedNick).filter(models.BannedNick.nick.ilike(db_usuario.nick)).first()
    if not nick_baneado_existente:
        banned_nick_entry = models.BannedNick(nick=db_usuario.nick)
        db.add(banned_nick_entry)
        # Hacemos un commit intermedio para asegurar que el nick baneado se guarde
        # antes de proceder con el borrado del usuario.
        db.commit()

    # 2. Eliminar al usuario y sus datos asociados (reutilizamos la funciÃƒÂƒÃ‚Â³n existente)
    delete_usuario(db, usuario_id=usuario_id)

    return db_usuario

def get_tiempo_promedio_espera(db: Session):
    """
    Calcula el tiempo promedio en segundos desde que una canciÃƒÂƒÃ‚Â³n se aÃƒÂƒÃ‚Â±ade hasta que se canta.
    """
    # Para SQLite, usamos julianday para calcular la diferencia en dÃƒÂƒÃ‚Â­as y luego convertimos a segundos.
    # Para PostgreSQL, serÃƒÂƒÃ‚Â­a: func.avg(func.extract('epoch', models.Cancion.finished_at - models.Cancion.created_at))
    avg_seconds = db.query(func.avg((func.julianday(models.Cancion.finished_at) - func.julianday(models.Cancion.created_at)) * 86400)).filter(
        models.Cancion.estado == "cantada",
        models.Cancion.finished_at.isnot(None)
    ).scalar()
    return avg_seconds or 0

def get_actividad_por_hora(db: Session):
    """
    Obtiene un reporte de la cantidad de canciones cantadas por cada hora del dia.
    Usa HOUR() para MySQL.
    """
    return (
        db.query(
            # Usamos HOUR() para MySQL para extraer la hora.
            func.hour(models.Cancion.started_at).label("hora"),
            func.count(models.Cancion.id).label("canciones_cantadas"),
        )
        .filter(models.Cancion.estado == "cantada", models.Cancion.started_at.isnot(None))
        .group_by(func.hour(models.Cancion.started_at))
        .order_by(func.count(models.Cancion.id).desc())
        .all()
    )

def get_canciones_cantadas_por_mesa(db: Session):
    """
    Obtiene un reporte de la cantidad de canciones cantadas por cada mesa.
    """
    return (
        db.query(
            models.Mesa.nombre,
            func.count(models.Cancion.id).label("canciones_cantadas"),
        )
        .join(models.Usuario, models.Mesa.id == models.Usuario.mesa_id)
        .join(models.Cancion, models.Usuario.id == models.Cancion.usuario_id)
        .filter(models.Cancion.estado == "cantada")
        .group_by(models.Mesa.nombre)
        .order_by(func.count(models.Cancion.id).desc())
        .all()
    )

def set_usuario_silenciado(db: Session, usuario_id: int, silenciar: bool):
    """
    Actualiza el estado 'silenciado' de un usuario.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if db_usuario:
        db_usuario.is_silenced = silenciar
        db.commit()
        db.refresh(db_usuario)
    return db_usuario

def unban_nick(db: Session, nick: str):
    """
    Elimina un nick de la lista de baneados para permitir que se vuelva a registrar.
    """
    banned_nick_entry = db.query(models.BannedNick).filter(models.BannedNick.nick.ilike(nick)).first()
    if banned_nick_entry:
        db.delete(banned_nick_entry)
        db.commit()
    return banned_nick_entry

def get_banned_nicks(db: Session):
    """
    Obtiene una lista de todos los nicks baneados.
    """
    return db.query(models.BannedNick).order_by(models.BannedNick.banned_at.desc()).all()

def get_canciones_mas_rechazadas(db: Session, limit: int = 10):
    """
    Obtiene un reporte de las canciones mÃƒÂƒÃ‚Â¡s rechazadas, agrupadas y contadas.
    """
    return (
        db.query(
            models.Cancion.titulo,
            models.Cancion.youtube_id,
            func.count(models.Cancion.id).label("veces_rechazada"),
        )
        .filter(models.Cancion.estado == "rechazada")
        .group_by(models.Cancion.titulo, models.Cancion.youtube_id)
        .order_by(func.count(models.Cancion.id).desc())
        .limit(limit)
        .all()
    )

def get_usuarios_mas_rechazados(db: Session, limit: int = 10):
    """
    Obtiene un reporte de los usuarios a los que mÃƒÂƒÃ‚Â¡s se les han rechazado canciones.
    """
    return (
        db.query(
            models.Usuario.nick,
            func.count(models.Cancion.id).label("canciones_rechazadas"),
        )
        .join(models.Cancion, models.Usuario.id == models.Cancion.usuario_id)
        .filter(models.Cancion.estado == "rechazada")
        .group_by(models.Usuario.nick)
        .order_by(func.count(models.Cancion.id).desc())
        .limit(limit)
        .all()
    )

def get_ingresos_por_categoria(db: Session):
    """
    Calcula los ingresos totales agrupados por cada categorÃƒÂƒÃ‚Â­a de producto.
    """
    return (
        db.query(
            models.Producto.categoria,
            func.sum(models.Consumo.valor_total).label("ingresos_totales")
        )
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .group_by(models.Producto.categoria)
        .order_by(func.sum(models.Consumo.valor_total).desc())
        .all()
    )

def create_admin_log_entry(db: Session, action: str, details: Optional[str] = None):
    """Crea una nueva entrada en el log de administraciÃƒÂƒÃ‚Â³n."""
    log_entry = models.AdminLog(action=action, details=details)
    db.add(log_entry)
    db.commit()
    return log_entry

def get_admin_logs(db: Session, limit: int = 100):
    """Obtiene las ÃƒÂƒÃ‚Âºltimas entradas del log de administraciÃƒÂƒÃ‚Â³n."""
    return db.query(models.AdminLog).order_by(models.AdminLog.timestamp.desc()).limit(limit).all()

def get_productos_menos_consumidos(db: Session, limit: int = 5):
    """
    Obtiene un reporte de los productos menos consumidos, agrupados y sumada su cantidad.
    """
    return (
        db.query(
            models.Producto.nombre,
            func.sum(models.Consumo.cantidad).label("cantidad_total"),
        )
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .group_by(models.Producto.nombre)
        .order_by(func.sum(models.Consumo.cantidad).asc())  # Orden ascendente
        .limit(limit)
        .all()
    )

def get_productos_no_consumidos(db: Session):
    """
    Obtiene una lista de productos del catÃƒÂƒÃ‚Â¡logo que nunca han sido consumidos.
    """
    return (
        db.query(models.Producto)
        .outerjoin(models.Consumo)
        .group_by(models.Producto.id)
        .having(func.count(models.Consumo.id) == 0)
        .all()
    )

def update_producto(db: Session, producto_id: int, producto_update: schemas.ProductoCreate):
    """
    Actualiza los datos de un producto especÃƒÂƒÃ‚Â­fico.
    """
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        for key, value in producto_update.model_dump(exclude_unset=True).items():
            setattr(db_producto, key, value)
        db.flush()  # Sincronizar cambios sin hacer commit
        db.refresh(db_producto)  # Obtener datos actualizados
        db.commit()  # Hacer commit de la transacciÃ³n
    return db_producto

def update_producto_valor(db: Session, producto_id: int, nuevo_valor: Decimal):
    """
    Actualiza el valor de un producto especÃƒÂƒÃ‚Â­fico en el catÃƒÂƒÃ‚Â¡logo.
    """
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db_producto.valor = nuevo_valor
        db.flush()  # Sincronizar cambios sin hacer commit
        db.refresh(db_producto)  # Obtener datos actualizados
        db.commit()  # Hacer commit de la transacciÃ³n
    return db_producto

def update_producto_active_status(db: Session, producto_id: int, is_active: bool):
    """
    Actualiza el estado de activaciÃƒÂƒÃ‚Â³n de un producto.
    """
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        db_producto.is_active = is_active
        db.flush()  # Sincronizar cambios sin hacer commit
        db.refresh(db_producto)  # Obtener datos actualizados
        db.commit()  # Hacer commit de la transacciÃ³n
    return db_producto

def get_usuarios_por_nivel(db: Session, nivel: str):
    """
    Obtiene una lista de todos los usuarios que tienen un nivel especÃƒÂƒÃ‚Â­fico.
    """
    return db.query(models.Usuario).filter(models.Usuario.nivel == nivel).all()

def get_resumen_noche(db: Session):
    """
    Obtiene un resumen de las mÃƒÂƒÃ‚Â©tricas clave de la noche.
    """
    ingresos_totales = db.query(func.sum(models.Consumo.valor_total)).scalar() or 0
    canciones_cantadas = db.query(func.count(models.Cancion.id)).filter(models.Cancion.estado == "cantada").scalar() or 0
    usuarios_activos = db.query(func.count(models.Usuario.id)).scalar() or 0
    return {
        "ingresos_totales": ingresos_totales,
        "canciones_cantadas": canciones_cantadas,
        "usuarios_activos": usuarios_activos,
    }

def get_resumen_mesa(db: Session, mesa_id: int):
    """
    Obtiene un resumen detallado de una mesa especÃƒÂƒÃ‚Â­fica, incluyendo usuarios,
    consumo total y canciones pendientes/reproduciÃƒÂƒÃ‚Â©ndose.
    """
    db_mesa = db.query(models.Mesa).filter(models.Mesa.id == mesa_id).first()
    if not db_mesa:
        return None

    # Usuarios en la mesa
    usuarios_mesa = db.query(models.Usuario).filter(models.Usuario.mesa_id == mesa_id).all()

    # Consumo total de la mesa
    consumo_total_mesa = (
        db.query(func.sum(models.Consumo.valor_total))
        .join(models.Usuario)
        .filter(models.Usuario.mesa_id == mesa_id)
        .scalar() or 0
    )

    # Canciones pendientes y reproduciendo de la mesa
    canciones_mesa = (
        db.query(models.Cancion)
        .join(models.Usuario)
        .filter(models.Usuario.mesa_id == mesa_id, models.Cancion.estado.in_(['pendiente', 'aprobado', 'reproduciendo']))
        .all()
    )
    canciones_pendientes = [c for c in canciones_mesa if c.estado in ['pendiente', 'aprobado']]
    cancion_reproduciendo = next((c for c in canciones_mesa if c.estado == 'reproduciendo'), None)

    return {
        "mesa_nombre": db_mesa.nombre,
        "usuarios": usuarios_mesa,
        "consumo_total_mesa": consumo_total_mesa,
        "canciones_pendientes_mesa": canciones_pendientes,
        "canciones_reproduciendo_mesa": cancion_reproduciendo,
    }

def get_usuarios_sin_canciones_cantadas(db: Session):
    """
    Obtiene una lista de usuarios que no han cantado ninguna canciÃƒÂƒÃ‚Â³n.
    """
    # Subconsulta para obtener los IDs de los usuarios que SÃƒÂƒÃ‚Â han cantado.
    subquery = db.query(models.Usuario.id).join(models.Cancion).filter(models.Cancion.estado == 'cantada').distinct()

    # Consulta principal para obtener los usuarios cuyo ID NO ESTÃƒÂƒÃ‚Â en la subconsulta.
    return db.query(models.Usuario).filter(models.Usuario.id.notin_(subquery)).all()

def get_estado_mesas(db: Session):
    """
    Obtiene un listado de todas las mesas con su estado (ocupada/vacÃƒÂƒÃ‚Â­a),
    nÃƒÂƒÃ‚Âºmero de usuarios y consumo total.
    """
    # Subconsulta para el conteo de usuarios por mesa
    user_count_subq = (
        db.query(
            models.Mesa.id.label("mesa_id"),
            func.count(models.Usuario.id).label("user_count")
        )
        .outerjoin(models.Usuario)
        .group_by(models.Mesa.id)
        .subquery()
    )

    # Subconsulta para el consumo total por mesa
    consumo_total_subq = (
        db.query(
            models.Mesa.id.label("mesa_id"),
            func.sum(models.Consumo.valor_total).label("total_consumido")
        )
        .outerjoin(models.Usuario).outerjoin(models.Consumo)
        .group_by(models.Mesa.id)
        .subquery()
    )

    # Consulta principal que une los datos
    return db.query(
        models.Mesa,
        func.coalesce(user_count_subq.c.user_count, 0),
        func.coalesce(consumo_total_subq.c.total_consumido, 0)
    ).outerjoin(user_count_subq, models.Mesa.id == user_count_subq.c.mesa_id).outerjoin(consumo_total_subq, models.Mesa.id == consumo_total_subq.c.mesa_id).order_by(models.Mesa.nombre).all()

def get_ranking_puntos_usuarios(db: Session, limit: int = 10):
    """
    Obtiene un ranking de usuarios ordenado por la cantidad de puntos acumulados.
    """
    return (
        db.query(models.Usuario)
        .order_by(models.Usuario.puntos.desc())
        .limit(limit)
        .all()
    )

def get_usuarios_cantan_pero_no_consumen(db: Session):
    """
    Obtiene una lista de usuarios que han cantado al menos una canciÃƒÂƒÃ‚Â³n
    pero no han realizado ningÃƒÂƒÃ‚Âºn consumo.
    """
    # Subconsulta para obtener los IDs de los usuarios que SÃƒÂƒÃ‚Â han cantado.
    subquery_cantan = db.query(models.Cancion.usuario_id).filter(models.Cancion.estado == 'cantada').distinct()

    # Subconsulta para obtener los IDs de los usuarios que SÃƒÂƒÃ‚Â han consumido.
    subquery_consumen = db.query(models.Consumo.usuario_id).distinct()

    # Consulta principal para obtener los usuarios que estÃƒÂƒÃ‚Â¡n en la primera subconsulta pero NO en la segunda.
    return db.query(models.Usuario).filter(
        models.Usuario.id.in_(subquery_cantan),
        models.Usuario.id.notin_(subquery_consumen)
    ).all()

def get_consumos_por_usuario(db: Session, usuario_id: int):
    """
    Obtiene el historial de consumo de un usuario especÃƒÂƒÃ‚Â­fico.
    """
    return db.query(models.Consumo).filter(models.Consumo.usuario_id == usuario_id).order_by(models.Consumo.created_at.desc()).all()


def get_recent_consumos(db: Session, limit: int = 10):
    """
    Devuelve los consumos mÃƒÂƒÃ‚Â¡s recientes junto con el nombre del producto,
    nick del usuario y nombre de la mesa (si existe).
    """
    # Hacemos las uniones necesarias para obtener la info deseada
    rows = (
        db.query(
            models.Consumo.id,
            models.Consumo.cantidad,
            models.Consumo.valor_total,
            models.Producto.nombre.label('producto_nombre'),
            models.Usuario.nick.label('usuario_nick'),
            models.Mesa.nombre.label('mesa_nombre'),
            models.Consumo.created_at
        )
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
        .outerjoin(models.Mesa, models.Usuario.mesa_id == models.Mesa.id)
        .order_by(models.Consumo.created_at.desc())
        .limit(limit)
        .all()
    )

    # Mapear a diccionarios/objetos que Pydantic pueda serializar fÃƒÂƒÃ‚Â¡cilmente
    result = []
    for r in rows:
        result.append({
            'id': r.id,
            'cantidad': r.cantidad,
            'valor_total': r.valor_total,
            'producto_nombre': r.producto_nombre,
            'usuario_nick': r.usuario_nick,
            'mesa_nombre': r.mesa_nombre,
            'created_at': r.created_at,
        })
    return result

def get_usuarios_mayor_gasto_por_categoria(db: Session, categoria: str, limit: int = 10):
    """
    Obtiene un reporte de los usuarios que mÃƒÂƒÃ‚Â¡s han gastado en una categorÃƒÂƒÃ‚Â­a de producto especÃƒÂƒÃ‚Â­fica.
    """
    return (
        db.query(
            models.Usuario.nick,
            func.sum(models.Consumo.valor_total).label("total_gastado")
        )
        .join(models.Consumo, models.Usuario.id == models.Consumo.usuario_id)
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .filter(models.Producto.categoria.ilike(categoria))
        .group_by(models.Usuario.nick)
        .order_by(func.sum(models.Consumo.valor_total).desc())
        .limit(limit)
        .all()
    )

def registrar_compra_producto(db: Session, compra: schemas.CompraProducto):
    """
    Registra una compra para un producto existente, aumentando su stock.
    Opcionalmente, actualiza el precio de compra.
    """
    db_producto = db.query(models.Producto).filter(models.Producto.id == compra.producto_id).first()
    if not db_producto:
        return None, f"Producto con ID {compra.producto_id} no encontrado."

    if compra.cantidad_comprada <= 0:
        return None, "La cantidad comprada debe ser mayor que cero."

    db_producto.stock += compra.cantidad_comprada
    if compra.nuevo_precio_compra is not None:
        db_producto.precio_compra = compra.nuevo_precio_compra

    db.commit()
    db.refresh(db_producto)
    return db_producto, "Compra registrada y stock actualizado correctamente."

def get_productos_mas_consumidos_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """
    Obtiene un reporte de los productos mÃƒÂƒÃ‚Â¡s consumidos en una mesa especÃƒÂƒÃ‚Â­fica.
    """
    return (
        db.query(
            models.Producto.nombre,
            func.sum(models.Consumo.cantidad).label("cantidad_total"),
        )
        .join(models.Consumo, models.Producto.id == models.Consumo.producto_id)
        .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
        .filter(models.Usuario.mesa_id == mesa_id)
        .group_by(models.Producto.nombre)
        .order_by(func.sum(models.Consumo.cantidad).desc())
        .limit(limit)
        .all()
    )

def get_usuarios_oro_activos(db: Session):
    """
    Obtiene una lista de usuarios de nivel "Oro" que han cantado mÃƒÂƒÃ‚Â¡s de 5 canciones.
    """
    return (
        db.query(models.Usuario)
        .join(models.Cancion, models.Usuario.id == models.Cancion.usuario_id)
        .filter(
            models.Usuario.nivel == "oro",
            models.Cancion.estado == "cantada"
        )
        .group_by(models.Usuario.id)
        .having(func.count(models.Cancion.id) > 5)
        .all()
    )

def get_canciones_mas_pedidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """
    Obtiene un reporte de las canciones mÃƒÂƒÃ‚Â¡s pedidas en una mesa especÃƒÂƒÃ‚Â­fica.
    """
    return (
        db.query(
            models.Cancion.titulo,
            models.Cancion.youtube_id,
            func.count(models.Cancion.id).label("veces_pedida"),
        )
        .join(models.Usuario, models.Cancion.usuario_id == models.Usuario.id)
        .filter(models.Usuario.mesa_id == mesa_id)
        .group_by(models.Cancion.titulo, models.Cancion.youtube_id)
        .order_by(func.count(models.Cancion.id).desc())
        .limit(limit)
        .all()
    )

def get_usuarios_consumen_pero_no_cantan(db: Session, umbral_consumo: float = 100.0):
    """
    Obtiene una lista de usuarios que han consumido mÃƒÂƒÃ‚Â¡s de un umbral
    pero no han cantado ninguna canciÃƒÂƒÃ‚Â³n.
    """
    # Subconsulta para obtener los IDs de los usuarios que SÃƒÂƒÃ‚Â han cantado.
    subquery_cantan = db.query(models.Cancion.usuario_id).filter(models.Cancion.estado == 'cantada').distinct()

    # Subconsulta para obtener los IDs de los usuarios que han consumido mÃƒÂƒÃ‚Â¡s del umbral.
    subquery_consumen_mas_de = db.query(models.Usuario.id).join(models.Consumo).group_by(models.Usuario.id).having(func.sum(models.Consumo.valor_total) > umbral_consumo).subquery()

    # Consulta principal para obtener los usuarios que estÃƒÂƒÃ‚Â¡n en la segunda subconsulta pero NO en la primera.
    return db.query(models.Usuario).filter(
        models.Usuario.id.in_(subquery_consumen_mas_de),
        models.Usuario.id.notin_(subquery_cantan)
    ).all()

def get_categorias_mas_consumidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """
    Obtiene un reporte de las categorÃƒÂƒÃ‚Â­as de productos mÃƒÂƒÃ‚Â¡s consumidas en una mesa especÃƒÂƒÃ‚Â­fica.
    """
    return (
        db.query(
            models.Producto.categoria,
            func.sum(models.Consumo.cantidad).label("cantidad_total"),
        )
        .join(models.Consumo, models.Producto.id == models.Consumo.producto_id)
        .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
        .filter(models.Usuario.mesa_id == mesa_id)
        .group_by(models.Producto.categoria)
        .order_by(func.sum(models.Consumo.cantidad).desc())
        .limit(limit)
        .all()
    )

def get_top_consumers_one_song(db: Session, limit: int = 10):
    """
    Obtiene un reporte de los usuarios que mÃƒÂƒÃ‚Â¡s han consumido pero que solo han cantado una canciÃƒÂƒÃ‚Â³n.
    """
    # Subconsulta para obtener los IDs de los usuarios que han cantado exactamente una canciÃƒÂƒÃ‚Â³n.
    subquery_una_cancion = (
        db.query(models.Cancion.usuario_id)
        .filter(models.Cancion.estado == 'cantada')
        .group_by(models.Cancion.usuario_id)
        .having(func.count(models.Cancion.id) == 1)
        .subquery()
    )

    # Consulta principal que filtra por esos usuarios y los ordena por consumo
    return (
        db.query(models.Usuario.nick, func.sum(models.Consumo.valor_total).label("total_gastado"))
        .join(models.Consumo, models.Usuario.id == models.Consumo.usuario_id)
        .filter(models.Usuario.id.in_(subquery_una_cancion))
        .group_by(models.Usuario.nick)
        .order_by(func.sum(models.Consumo.valor_total).desc())
        .limit(limit)
        .all()
    )

def get_usuarios_inactivos_consumo(db: Session, horas: int = 2):
    """
    Obtiene una lista de usuarios cuyo ÃƒÂƒÃ‚Âºltimo consumo fue hace mÃƒÂƒÃ‚Â¡s de X horas,
    o que no han consumido nada.
    """
    hora_limite = datetime.datetime.utcnow() - datetime.timedelta(hours=horas)

    # Subconsulta para obtener el ÃƒÂƒÃ‚Âºltimo consumo de cada usuario
    ultimo_consumo_subq = (
        db.query(
            models.Consumo.usuario_id.label("usuario_id"),
            func.max(models.Consumo.created_at).label("ultimo_consumo_ts"),
        )
        .group_by(models.Consumo.usuario_id)
        .subquery()
    )

    # Consulta principal que une usuarios con su ÃƒÂƒÃ‚Âºltimo consumo
    return db.query(models.Usuario).outerjoin(ultimo_consumo_subq, models.Usuario.id == ultimo_consumo_subq.c.usuario_id).filter(
        (ultimo_consumo_subq.c.ultimo_consumo_ts < hora_limite) |
        (ultimo_consumo_subq.c.ultimo_consumo_ts == None)
    ).all()


def get_admin_api_key(db: Session, key: str) -> Optional[models.AdminApiKey]:
    """
    Busca una clave de API de administrador en la base de datos,
    verifica que estÃƒÂƒÃ‚Â© activa y actualiza su ÃƒÂƒÃ‚Âºltimo uso.
    """
    db_key = db.query(models.AdminApiKey).filter(
        models.AdminApiKey.key == key,
        models.AdminApiKey.is_active == True
    ).first()

    if db_key:
        db_key.last_used = datetime.datetime.utcnow()
        db.commit()

    return db_key

def get_all_admin_api_keys(db: Session) -> List[models.AdminApiKey]:
    """Obtiene todas las claves de API de administrador de la base de datos."""
    return db.query(models.AdminApiKey).order_by(models.AdminApiKey.created_at.desc()).all()

def create_admin_api_key(db: Session, description: str) -> models.AdminApiKey:
    """Genera y almacena una nueva clave de API de administrador."""
    new_key = secrets.token_urlsafe(32)
    db_key = models.AdminApiKey(key=new_key, description=description)
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key

def delete_admin_api_key(db: Session, key_id: int) -> Optional[models.AdminApiKey]:
    """Elimina una clave de API de administrador por su ID."""
    db_key = db.query(models.AdminApiKey).filter(models.AdminApiKey.id == key_id).first()
    if db_key:
        db.delete(db_key)
        db.commit()
    return db_key


def get_consumo_por_mesa(db: Session, mesa_id: int):
    """
    Obtiene el historial de consumo de una mesa especÃƒÂƒÃ‚Â­fica.
    """
    return (
        db.query(models.Consumo)
        .join(models.Usuario)
        .filter(models.Usuario.mesa_id == mesa_id)
        .order_by(models.Consumo.created_at.desc())
        .all()
    )


def delete_consumo(db: Session, consumo_id: int):
    """
    Elimina un consumo, restaura el stock del producto asociado y recalcula
    los puntos y nivel del usuario correspondiente.
    Devuelve True si se eliminÃƒÂƒÃ‚Â³, o None si no se encontrÃƒÂƒÃ‚Â³.
    """
    SILVER_THRESHOLD = 50.0
    GOLD_THRESHOLD = 150.0

    db_consumo = db.query(models.Consumo).filter(models.Consumo.id == consumo_id).first()
    if not db_consumo:
        return None

    # Restaurar stock del producto
    if db_consumo.producto:
        try:
            db_consumo.producto.stock += db_consumo.cantidad
        except Exception:
            # En casos raros, ignoramos
            pass

    usuario = db_consumo.usuario

    # Borramos el registro de consumo
    db.delete(db_consumo)
    db.commit()

    # Recalcular puntos y nivel del usuario
    if usuario:
        total_consumido = db.query(func.sum(models.Consumo.valor_total)).filter(models.Consumo.usuario_id == usuario.id).scalar() or 0
        usuario.puntos = int(total_consumido / 10)
        if total_consumido >= GOLD_THRESHOLD:
            usuario.nivel = 'oro'
        elif total_consumido >= SILVER_THRESHOLD:
            usuario.nivel = 'plata'
        else:
            usuario.nivel = 'bronce'
        db.commit()

    return True

def get_config(db: Session, key: str):
    """Obtiene un valor de configuraciÃƒÂƒÃ‚Â³n por su clave (clave)."""
    return db.query(models.ConfiguracionGlobal).filter(models.ConfiguracionGlobal.clave == key).first()

def update_config(db: Session, key: str, value: str):
    """Establece o actualiza un valor de configuraciÃƒÂƒÃ‚Â³n (clave)."""
    db_config = db.query(models.ConfiguracionGlobal).filter(models.ConfiguracionGlobal.clave == key).first()
    if db_config:
        db_config.value = value
    else:
        db_config = models.ConfiguracionGlobal(clave=key, valor=value)
        db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

def get_or_create_dj_user(db: Session) -> models.Usuario:
    """
    Busca al usuario 'DJ'. Si no existe, lo crea sin asociarlo a una mesa.
    Este usuario se usa para las canciones aÃƒÂƒÃ‚Â±adidas por el administrador.
    """
    dj_user = db.query(models.Usuario).filter(models.Usuario.nick == "DJ").first()
    if not dj_user:
        dj_user = models.Usuario(nick="DJ", mesa_id=None) # No pertenece a ninguna mesa
        db.add(dj_user)
        db.commit()
        db.refresh(dj_user)
    return dj_user

def get_o_crear_usuario_admin_para_mesa(db: Session, mesa_id: int) -> models.Usuario:
    """
    Busca o crea un usuario administrador para una mesa especÃƒÂƒÃ‚Â­fica.
    Este usuario se utiliza para las canciones aÃƒÂƒÃ‚Â±adidas por el admin a travÃƒÂƒÃ‚Â©s del dashboard.
    El nick serÃƒÂƒÃ‚Â¡ "ADMIN_Mesa_{mesa_id}".
    """
    admin_nick = f"ADMIN_Mesa_{mesa_id}"
    admin_user = db.query(models.Usuario).filter(models.Usuario.nick == admin_nick).first()
    
    if not admin_user:
        admin_user = models.Usuario(nick=admin_nick, mesa_id=mesa_id)
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    
    return admin_user

def get_canciones_pendientes_por_aprobar(db: Session):
    """
    Obtiene las canciones que están en estado 'pendiente' (no aprobadas aún).
    Retorna desde el cache unificado.
    """
    from queue_manager import queue_manager
    state = queue_manager.get_full_state(db)
    return state["pending"]

def auto_approve_songs_after_10_minutes(db: Session):
    """
    Aprueba automÃ¡ticamente canciones pendientes que ya han pasado 10 minutos desde su creaciÃ³n.
    RESPETA EL LÃMITE DE COLA: Solo aprueba si hay espacio en la cola de aprobados (max 1).
    """
    from datetime import timedelta
    
    # Verificar cupo en cola aprobada
    approved_count = db.query(models.Cancion).filter(models.Cancion.estado == 'aprobado').count()
    if approved_count >= 1:
        return [] # No hay cupo, no aprobamos nada automÃ¡ticamente por tiempo
        
    # Calcular cuÃ¡ntas podemos aprobar (solo 1 para llenar el cupo)
    cupo_disponible = 1 - approved_count # DeberÃ­a ser 1
    
    # Obtener canciones pendientes que tienen mÃ¡s de 10 minutos
    time_threshold = now_bogota() - timedelta(minutes=10)
    
    songs_to_auto_approve = db.query(models.Cancion).filter(
        models.Cancion.estado == 'pendiente',
        models.Cancion.created_at <= time_threshold
    ).order_by(models.Cancion.created_at.asc()).limit(cupo_disponible).all()
    
    # Aprobar las canciones seleccionadas
    for cancion in songs_to_auto_approve:
        cancion.estado = 'aprobado'
        cancion.approved_at = now_bogota()
        db.add(cancion)
    
    if songs_to_auto_approve:
        db.commit()
        # Notificar al gestor de cola para refrescar cache unificado
        from queue_manager import queue_manager
        queue_manager.refresh_all(db)
    
    return songs_to_auto_approve

def approve_song_by_admin(db: Session, cancion_id: int):
    """
    Aprueba una canción manualmente desde el admin.
    Cambia el estado de 'pendiente' a 'aprobado'.
    """
    from queue_manager import queue_manager
    db_cancion = db.query(models.Cancion).filter(
        models.Cancion.id == cancion_id,
        models.Cancion.estado == 'pendiente'
    ).first()
    
    if db_cancion:
        db_cancion.estado = 'aprobado'
        db_cancion.approved_at = now_bogota()
        db.commit()
        db.refresh(db_cancion)
        # Sincronizar cache unificado
        queue_manager.refresh_all(db)
        return db_cancion
    return None

def get_cola_completa(db: Session):
    """
    Obtiene la cola completa, incluyendo:
    - CanciÃƒÂƒÃ‚Â³n actualmente reproduciendo
    - Cola aprobada (upcoming)
    - Cola pendiente por aprobar
    """
    # Aplicar aprobaciÃƒÂƒÃ‚Â³n automÃƒÂƒÃ‚Â¡tica despuÃƒÂƒÃ‚Â©s de 10 minutos
    auto_approve_songs_after_10_minutes(db)
    
    now_playing = db.query(models.Cancion).filter(models.Cancion.estado == "reproduciendo").first()
    approved_queue = get_cola_priorizada(db)
    pending_queue = get_canciones_pendientes_por_aprobar(db)

    # Si la canciÃƒÂƒÃ‚Â³n que se estÃƒÂƒÃ‚Â¡ reproduciendo sigue en la lista de 'upcoming', la quitamos.
    if now_playing:
        approved_queue = [song for song in approved_queue if song.id != now_playing.id]

    return {
        "now_playing": now_playing, 
        "upcoming": approved_queue,
        "pending": pending_queue
    }

def set_mesa_active_status(db: Session, mesa_id: int, is_active: bool) -> Optional[models.Mesa]:
    """
    Actualiza el estado de activaciÃƒÂƒÃ‚Â³n de una mesa.
    """
    db_mesa = db.query(models.Mesa).filter(models.Mesa.id == mesa_id).first()
    if db_mesa:
        db_mesa.is_active = is_active
        db.commit()
        db.refresh(db_mesa)
    return db_mesa

def get_all_tables_consumption_summaries(db: Session) -> List[dict]:
    """
    Obtiene un resumen detallado del consumo para todas las mesas,
    incluyendo el valor total y los productos consumidos.
    """
    # Obtener todas las mesas
    mesas = db.query(models.Mesa).order_by(models.Mesa.nombre).all()
    
    results = []
    for mesa in mesas:
        # Calcular el consumo total para esta mesa
        total_consumido = (
            db.query(func.sum(models.Consumo.valor_total))
            .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
            .filter(models.Usuario.mesa_id == mesa.id)
            .scalar() or Decimal('0.00')
        )
        
        # Obtener los detalles de cada consumo para esta mesa
        consumos_detalle = (
            db.query(
                models.Producto.nombre.label('producto_nombre'),
                models.Consumo.cantidad,
                models.Consumo.valor_total,
                models.Consumo.created_at
            )
            .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
            .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
            .filter(models.Usuario.mesa_id == mesa.id)
            .order_by(models.Consumo.created_at.desc())
            .all()
        )
        
        results.append({
            "mesa_id": mesa.id,
            "mesa_nombre": mesa.nombre,
            "total_consumido": total_consumido,
            "consumos": [
                {"producto_nombre": c.producto_nombre, "cantidad": c.cantidad, "valor_total": c.valor_total, "created_at": c.created_at}
                for c in consumos_detalle
            ]
        })
        
    return results

def create_pago_for_mesa(db: Session, pago: schemas.PagoCreate) -> models.Pago:
    """
    Registra un nuevo pago para una mesa especÃƒÂƒÃ‚Â­fica.
    """
    db_mesa = get_mesa_by_id(db, mesa_id=pago.mesa_id)
    if not db_mesa:
        return None

    # Obtener o crear cuenta activa
    active_cuenta = get_active_cuenta(db, pago.mesa_id)
    if not active_cuenta:
         active_cuenta = create_new_active_cuenta(db, pago.mesa_id)

    db_pago = models.Pago(
        monto=pago.monto,
        metodo_pago=pago.metodo_pago,
        mesa_id=pago.mesa_id,
        cuenta_id=active_cuenta.id
    )
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    return db_pago

def get_all_tables_payment_status(db: Session) -> List[dict]:
    """
    Obtiene un estado de cuenta detallado para todas las mesas ACTIVAS, incluyendo
    consumos, pagos y saldo pendiente. Solo devuelve mesas que estÃ¡n activas (is_active=True).
    """
    mesas = db.query(models.Mesa).filter(models.Mesa.is_active == True).order_by(models.Mesa.nombre).all()
    
    results = []
    for mesa in mesas:
        # 1. Calcular total consumido
        total_consumido = (
            db.query(func.sum(models.Consumo.valor_total))
            .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
            .filter(models.Usuario.mesa_id == mesa.id)
            .scalar() or Decimal('0.00')
        )

        # 2. Calcular total pagado
        total_pagado = (
            db.query(func.sum(models.Pago.monto))
            .filter(models.Pago.mesa_id == mesa.id)
            .scalar() or Decimal('0.00')
        )

        # 3. Calcular saldo pendiente
        saldo_pendiente = total_consumido - total_pagado

        # 4. Obtener detalles de consumos y pagos
        consumos_detalle = db.query(models.Consumo).join(models.Usuario).filter(models.Usuario.mesa_id == mesa.id).all()
        pagos_detalle = db.query(models.Pago).filter(models.Pago.mesa_id == mesa.id).order_by(models.Pago.created_at.desc()).all()

        # Mapear consumos a ConsumoItemDetalle
        consumos_items = [
            schemas.ConsumoItemDetalle(
                producto_nombre=c.producto.nombre,
                cantidad=c.cantidad,
                valor_total=c.valor_total,
                created_at=c.created_at
            ) for c in consumos_detalle
        ]

        # 5. Obtener ID de cuenta activa
        active_account = get_active_cuenta(db, mesa.id)
        cuenta_id = active_account.id if active_account else None

        # 6. Calcular Nivel (Oro/Plata/Bronce)
        nivel_mesa = "bronce"
        try:
             total_val = float(total_consumido)
             if total_val >= 150000:
                 nivel_mesa = "oro"
             elif total_val >= 50000:
                 nivel_mesa = "plata"
        except:
             pass

        results.append({
            "mesa_id": mesa.id,
            "cuenta_id": cuenta_id,
            "mesa_nombre": mesa.nombre,
            "qr_code": mesa.qr_code,
            "total_consumido": total_consumido,
            "total_pagado": total_pagado,
            "saldo_pendiente": saldo_pendiente,
            "consumos": consumos_items,
            "pagos": pagos_detalle,
            "nivel": nivel_mesa
        })
        
    return results

def get_table_payment_status(db: Session, mesa_id: int) -> Optional[dict]:
    """
    Obtiene un estado de cuenta detallado para una mesa especÃƒÂƒÃ‚Â­fica.
    CAMBIO: Se obtiene el estado de la CUENTA ACTIVA de la mesa.
    """
    # 1. Obtener la cuenta activa
    # Nota: Usamos la funciÃƒÂƒÃ‚Â³n helper definida abajo. Como Python permite referencias forward en runtime,
    # esto funcionarÃƒÂƒÃ‚Â¡ siempre que se llame despuÃƒÂƒÃ‚Â©s de definir get_active_cuenta.
    # Pero para estar seguros, la importaremos o asumiremos que estÃƒÂƒÃ‚Â¡ en el scope global del mÃƒÂƒÃ‚Â³dulo.
    # Dado que get_active_cuenta estÃƒÂƒÃ‚Â¡ en este mismo archivo, estÃƒÂƒÃ‚Â¡ bien.
    
    active_cuenta = get_active_cuenta(db, mesa_id)
    
    if not active_cuenta:
         # Si no hay cuenta activa, devolvemos un estado vacÃƒÂƒÃ‚Â­o pero vÃƒÂƒÃ‚Â¡lido
         mesa = get_mesa_by_id(db, mesa_id)
         if not mesa: return None
         return schemas.MesaEstadoPago(
             mesa_id=mesa.id, cuenta_id=None, mesa_nombre=mesa.nombre, qr_code=mesa.qr_code,
             total_consumido=Decimal(0), total_pagado=Decimal(0), saldo_pendiente=Decimal(0), consumos=[], pagos=[]
         ).model_dump()
         
    return get_cuenta_payment_status(db, active_cuenta.id)

async def start_next_song_if_autoplay_and_idle(db: Session):
    """
    Verifica si no hay nada sonando y si hay canciones en la cola.
    Si se cumplen las condiciones, inicia la siguiente canciÃƒÂƒÃ‚Â³n automÃƒÂƒÃ‚Â¡ticamente.
    """
    import websocket_manager

    # Verificamos si ya hay una canciÃƒÂƒÃ‚Â³n en estado 'reproduciendo'
    is_playing = db.query(models.Cancion).filter(models.Cancion.estado == "reproduciendo").first()
    if is_playing:
        return

    # Si no hay nada sonando, marcamos la siguiente como 'reproduciendo'
    next_song = marcar_siguiente_como_reproduciendo(db)

    if next_song:
        # Si se encontrÃƒÂƒÃ‚Â³ una siguiente canciÃƒÂƒÃ‚Â³n, notificamos a todos los clientes
        # para que la cola se actualice y el reproductor comience a reproducir.
        await websocket_manager.manager.broadcast_queue_update()
        await websocket_manager.manager.broadcast_play_song(next_song.youtube_id, next_song.duracion_seconds or 0)
        create_admin_log_entry(db, action="AUTO_START", details=f"Iniciada automÃƒÂƒÃ‚Â¡ticamente la canciÃƒÂƒÃ‚Â³n '{next_song.titulo}'.")

async def avanzar_cola_automaticamente(db: Session):
    """
    Función central para avanzar la cola: marca la canción actual como cantada,
    inicia la siguiente y notifica a todos los clientes.
    Esta función es llamada tanto por el autoplay como por el botón manual.
    """
    import websocket_manager

    # 1. Marcar la canción actual como 'cantada' y obtener sus datos
    cancion_cantada = marcar_cancion_actual_como_cantada(db)
    if cancion_cantada:
        # Notificar a todos que la canción terminó (para mostrar puntajes, etc.)
        await websocket_manager.manager.broadcast_song_finished(cancion_cantada)

    # 2. Marcar la siguiente canción como 'reproduciendo'
    siguiente_cancion = marcar_siguiente_como_reproduciendo(db)

    # 3. Aprobar la siguiente canción lazy si es necesario
    # IMPORTANTE: Esto debe suceder ANTES del broadcast_queue_update
    check_and_approve_next_lazy_song(db)

    # 4. Notificar a todos los clientes sobre la actualización de la cola
    await websocket_manager.manager.broadcast_queue_update()

    # 5. Si hay una nueva canción, enviar la orden de reproducción al player
    if siguiente_cancion:
        await websocket_manager.manager.broadcast_play_song(siguiente_cancion.youtube_id, siguiente_cancion.duracion_seconds or 0)

    return siguiente_cancion
def registrar_compra_producto(db: Session, compra: schemas.CompraProducto):
    """
    Registra una compra para un producto existente, aumentando su stock.
    Opcionalmente, actualiza el precio de compra.
    """
    db_producto = db.query(models.Producto).filter(models.Producto.id == compra.producto_id).first()
    if not db_producto:
        return None, f"Producto con ID {compra.producto_id} no encontrado."

    if compra.cantidad_comprada <= 0:
        return None, "La cantidad comprada debe ser mayor que cero."

    db_producto.stock += compra.cantidad_comprada
    if compra.nuevo_precio_compra is not None:
        db_producto.precio_compra = compra.nuevo_precio_compra

    db.commit()
    db.refresh(db_producto)
    return db_producto, "Compra registrada y stock actualizado correctamente."

def get_consumos_por_usuario(db: Session, usuario_id: int):
    """
    Obtiene el historial de consumo de un usuario especÃƒÂƒÃ‚Â­fico.
    """
    return db.query(models.Consumo).filter(models.Consumo.usuario_id == usuario_id).order_by(models.Consumo.created_at.desc()).all()


def get_recent_consumos(db: Session, limit: int = 10):
    """
    Devuelve los consumos mÃƒÂƒÃ‚Â¡s recientes junto con el nombre del producto,
    nick del usuario y nombre de la mesa (si existe).
    Filtra los consumos que ya han sido despachados.
    """
    # Hacemos las uniones necesarias para obtener la info deseada
    rows = (
        db.query(
            models.Consumo.id,
            models.Consumo.cantidad,
            models.Consumo.valor_total,
            models.Producto.nombre.label('producto_nombre'),
            models.Usuario.nick.label('usuario_nick'),
            models.Mesa.nombre.label('mesa_nombre'),
            models.Consumo.created_at
        )
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .join(models.Usuario, models.Consumo.usuario_id == models.Usuario.id)
        .outerjoin(models.Mesa, models.Usuario.mesa_id == models.Mesa.id)
        .filter(models.Consumo.is_dispatched == False)
        .order_by(models.Consumo.created_at.desc())
        .limit(limit)
        .all()
    )

    # Mapear a diccionarios/objetos que Pydantic pueda serializar fÃƒÂƒÃ‚Â¡cilmente
    result = []
    for r in rows:
        result.append({
            'id': r.id,
            'cantidad': r.cantidad,
            'valor_total': r.valor_total,
            'producto_nombre': r.producto_nombre,
            'usuario_nick': r.usuario_nick,
            'mesa_nombre': r.mesa_nombre,
            'created_at': r.created_at,
        })
    return result

def get_usuarios_mayor_gasto_por_categoria(db: Session, categoria: str, limit: int = 10):
    """
    Obtiene un reporte de los usuarios que mÃƒÂƒÃ‚Â¡s han gastado en una categorÃƒÂƒÃ‚Â­a de producto especÃƒÂƒÃ‚Â­fica.
    """
    return (
        db.query(
            models.Usuario.nick,
            func.sum(models.Consumo.valor_total).label("total_gastado")
        )
        .join(models.Consumo, models.Usuario.id == models.Consumo.usuario_id)
        .join(models.Producto, models.Consumo.producto_id == models.Producto.id)
        .filter(models.Producto.categoria.ilike(categoria))
        .group_by(models.Usuario.nick)
        .order_by(func.sum(models.Consumo.valor_total).desc())
        .limit(limit)
        .all()
    )

# --- Admin API Key Management ---
def create_admin_api_key(db: Session, description: str):
    """
    Creates a new admin API key with a secure random key.
    Returns the full key object including the key itself (shown only once).
    """
    # Generate a secure random API key (32 bytes = 64 hex characters)
    new_key = secrets.token_hex(32)
    
    db_api_key = models.AdminApiKey(
        key=new_key,
        description=description,
        is_active=True
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    return db_api_key

def get_all_admin_api_keys(db: Session):
    """
    Returns all admin API keys without revealing the actual key values.
    """
    return db.query(models.AdminApiKey).all()

def delete_admin_api_key(db: Session, key_id: int):
    """
    Deletes an admin API key by ID.
    Returns the deleted key object or None if not found.
    """
    db_key = db.query(models.AdminApiKey).filter(models.AdminApiKey.id == key_id).first()
    if db_key:
        db.delete(db_key)
        db.commit()
    return db_key

def get_admin_api_key(db: Session, key: str):
    """
    Retrieves an admin API key by its key value.
    Updates the last_used timestamp when found.
    Returns the key object if found and active, None otherwise.
    """
    db_key = db.query(models.AdminApiKey).filter(
        models.AdminApiKey.key == key,
        models.AdminApiKey.is_active == True
    ).first()
    
    if db_key:
        # Update last_used timestamp
        db_key.last_used = datetime.datetime.utcnow()
        db.commit()
    
    return db_key

# --- Account (Cuenta) Management ---

def get_active_cuenta(db: Session, mesa_id: int) -> Optional[models.Cuenta]:
    """Obtiene la cuenta activa actual de una mesa."""
    return db.query(models.Cuenta).filter(models.Cuenta.mesa_id == mesa_id, models.Cuenta.is_active == True).first()

def create_new_active_cuenta(db: Session, mesa_id: int):
    """
    Cierra la cuenta activa actual (si existe) y crea una nueva.
    """
    # 1. Buscar y cerrar cuenta activa existente
    active = get_active_cuenta(db, mesa_id)
    if active:
        active.is_active = False
        active.closed_at = now_bogota()
    
    # 2. Crear nueva cuenta activa
    new_cuenta = models.Cuenta(mesa_id=mesa_id, is_active=True, created_at=now_bogota())
    db.add(new_cuenta)
    db.commit()
    db.refresh(new_cuenta)
    return new_cuenta

def get_previous_cuentas(db: Session, mesa_id: int):
    """Obtiene el historial de cuentas cerradas de una mesa."""
    return db.query(models.Cuenta).filter(models.Cuenta.mesa_id == mesa_id, models.Cuenta.is_active == False).order_by(models.Cuenta.closed_at.desc()).all()

def get_cuenta_by_id(db: Session, cuenta_id: int):
    """Busca una cuenta por su ID."""
    return db.query(models.Cuenta).filter(models.Cuenta.id == cuenta_id).first()

def get_cuenta_payment_status(db: Session, cuenta_id: int) -> Optional[dict]:
    """
    Obtiene el estado de pago de una CUENTA especÃƒÂƒÃ‚Â­fica (activa o cerrada).
    """
    cuenta = get_cuenta_by_id(db, cuenta_id)
    if not cuenta:
        return None
    
    mesa = cuenta.mesa
    
    # 1. Calcular total consumido EN ESTA CUENTA
    total_consumido = (
        db.query(func.sum(models.Consumo.valor_total))
        .filter(models.Consumo.cuenta_id == cuenta.id)
        .scalar() or Decimal('0.00')
    )

    # 2. Calcular total pagado EN ESTA CUENTA
    total_pagado = (
        db.query(func.sum(models.Pago.monto))
        .filter(models.Pago.cuenta_id == cuenta.id)
        .scalar() or Decimal('0.00')
    )

    # 3. Calcular saldo pendiente
    saldo_pendiente = total_consumido - total_pagado

    # 4. Obtener detalles
    consumos_detalle = db.query(models.Consumo).filter(
        models.Consumo.cuenta_id == cuenta.id
    ).order_by(models.Consumo.created_at.asc()).all()
    
    pagos_detalle = db.query(models.Pago).filter(models.Pago.cuenta_id == cuenta.id).order_by(models.Pago.created_at.asc()).all()

    consumos_items = [
        schemas.ConsumoItemDetalle(
            producto_nombre=c.producto.nombre,
            cantidad=c.cantidad,
            valor_total=c.valor_total,
            created_at=c.created_at
        ) for c in consumos_detalle
    ]

    return schemas.MesaEstadoPago(
        mesa_id=mesa.id, 
        cuenta_id=cuenta.id,
        mesa_nombre=mesa.nombre, 
        qr_code=mesa.qr_code,
        total_consumido=total_consumido, 
        total_pagado=total_pagado, 
        saldo_pendiente=saldo_pendiente, 
        consumos=consumos_items, 
        pagos=pagos_detalle,
        nivel=("oro" if total_consumido >= 150000 else "plata" if total_consumido >= 50000 else "bronce")
    ).model_dump()# CÃƒÂƒÃ‚Â³digo para agregar al final de crud.py



# --- Lazy Approval Queue Functions ---



def get_cola_lazy(db: Session):
    """
    Obtiene todas las canciones en estado pendiente_lazy, ordenadas por prioridad.
    Retorna desde el cache unificado.
    """
    from queue_manager import queue_manager
    state = queue_manager.get_full_state(db)
    return state["lazy_queue"]

def aprobar_siguiente_cancion_lazy(db: Session):
    """
    Aprueba la siguiente canción de la cola lazy.
    Llamada automáticamente cuando la canción actual llega al 50%.
    """
    cola_lazy = get_cola_lazy(db)
    if not cola_lazy:
        return None
    
    siguiente = cola_lazy[0]
    siguiente.estado = "aprobado"
    siguiente.approved_at = now_bogota()
    db.commit()
    db.refresh(siguiente)
    
    from queue_manager import queue_manager
    queue_manager.refresh_queue(db)

    create_admin_log_entry(db, action="LAZY_APPROVAL", details=f"Cancion '{siguiente.titulo}' aprobada automaticamente (lazy).")
    return siguiente

def get_cola_completa_con_lazy(db: Session):
    """
    Versión extendida de get_cola_completa que incluye la cola lazy.
    Retorna todo sincronizado desde el cache unificado.
    """
    # Aplicar aprobación automática después de 10 minutos (opcional aquí, puede ser background)
    auto_approve_songs_after_10_minutes(db)
    
    from queue_manager import queue_manager
    state = queue_manager.get_full_state(db)
    
    return state

def check_and_approve_next_lazy_song(db: Session):
    """
    Verifica si hay espacio en la cola de aprobados y aprueba la siguiente lazy.
    Regla: Mantener MÃXIMO 1 canciÃ³n aprobada (upcoming) esperando, aparte de la que suena.
    Esta funciÃ³n es llamada por un background task periÃ³dicamente o al avanzar canciÃ³n.
    """
    # Contar cuÃ¡ntas canciones hay en estado 'aprobado'
    approved_count = db.query(models.Cancion).filter(models.Cancion.estado == "aprobado").count()
    
    # Si hay menos de 1 canciÃ³n aprobada (es decir, 0), aprobamos la siguiente de la lazy
    if approved_count < 1:
        return aprobar_siguiente_cancion_lazy(db)
    
    return None

def update_consumo_cantidad(db: Session, consumo_id: int, delta: int):
    """
    Actualiza la cantidad de un consumo existente.
    delta puede ser positivo (incrementar) o negativo (decrementar).
    Recalcula el valor total y actualiza el stock.
    """
    # 1. Obtener el consumo
    db_consumo = db.query(models.Consumo).filter(models.Consumo.id == consumo_id).first()
    if not db_consumo:
        return None, "Consumo no encontrado."

    # 2. Obtener el producto
    db_producto = db_consumo.producto
    if not db_producto:
        return None, "Producto asociado no encontrado."

    # 3. Validar nueva cantidad
    nueva_cantidad = db_consumo.cantidad + delta
    
    # Si la nueva cantidad es menor que 1, no permitimos la operaciÃ³n (para eliminar, usar delete explÃ­cito)
    if nueva_cantidad < 1:
        return None, "La cantidad mÃ­nima es 1. Elimine el producto si desea removerlo."
    
    # 4. Validar stock si estamos aumentando
    if delta > 0:
        if db_producto.stock < delta:
            return None, f"No hay suficiente stock. Disponible: {db_producto.stock}"
    
    # 5. Actualizar stock
    # Si delta es positivo (aumento), restamos del stock.
    # Si delta es negativo (disminuciÃ³n), sumamos al stock (delta es negativo, asÃ­ que -= delta es restar un negativo -> sumar).
    db_producto.stock -= delta
    
    # 6. Actualizar consumo
    db_consumo.cantidad = nueva_cantidad
    
    # Recalcular valor total
    valor_unitario = db_producto.valor
    db_consumo.valor_total = valor_unitario * nueva_cantidad
    
    # 7. Actualizar puntos del usuario si corresponde (opcional, pero consistente)
    # Revertimos puntos anteriores y sumamos nuevos, o ajustamos por la diferencia.
    # LÃ³gica de puntos: 1 punto por cada 10 de valor.
    # Diferencia de valor:
    diferencia_valor = valor_unitario * delta
    puntos_delta = int(diferencia_valor / 10)
    
    if db_consumo.usuario:
        db_consumo.usuario.puntos += puntos_delta
    
    db.commit()
    db.refresh(db_consumo)
    
    return db_consumo, None
def move_lazy_song_up(db: Session, cancion_id: int, usuario_id: int):
    """
    Mueve una canciÃ³n (pendiente, pendiente_lazy o aprobado) hacia arriba en la cola del usuario.
    Solo funciona para canciones del usuario actual.
    """
    # 1. Validar que la canciÃ³n existe, estÃ¡ en pendiente, pendiente_lazy o aprobado, y pertenece al usuario
    cancion = db.query(models.Cancion).filter(
        models.Cancion.id == cancion_id,
        models.Cancion.estado.in_(['pendiente', 'pendiente_lazy', 'aprobado']),
        models.Cancion.usuario_id == usuario_id
    ).first()
    
    if not cancion:
        return None
    
    # 2. Obtener todas las canciones del usuario en estados pendiente, pendiente_lazy o aprobado, ordenadas
    canciones_usuario = (
        db.query(models.Cancion)
        .filter(
            models.Cancion.usuario_id == usuario_id,
            models.Cancion.estado.in_(['pendiente', 'pendiente_lazy', 'aprobado'])
        )
        .order_by(
            case((models.Cancion.orden_manual.is_(None), 1), else_=0),
            models.Cancion.orden_manual.asc(),
            models.Cancion.id.asc()
        )
        .all()
    )
    
    if len(canciones_usuario) <= 1:
        # Si hay solo una canciÃ³n, no se puede mover
        return cancion
    
    # 3. Encontrar el Ã­ndice de la canciÃ³n actual
    indice_actual = None
    for i, c in enumerate(canciones_usuario):
        if c.id == cancion_id:
            indice_actual = i
            break
    
    if indice_actual is None or indice_actual == 0:
        # No encontrado o ya estÃ¡ al principio
        return cancion
    
    # 4. Intercambiar orden con la canciÃ³n anterior
    cancion_anterior = canciones_usuario[indice_actual - 1]
    
    # Si la canciÃ³n anterior tiene orden_manual, incrementamos el orden de la actual
    if cancion_anterior.orden_manual is not None:
        # Asignar un orden entre la anterior y la siguiente (si existe)
        nuevo_orden = cancion_anterior.orden_manual - 0.5
    else:
        # Ambas sin orden_manual, asignar a la anterior
        cancion_anterior.orden_manual = 1
        nuevo_orden = 0
    
    cancion.orden_manual = nuevo_orden
    db.commit()
    db.refresh(cancion)
    
    return cancion

def move_lazy_song_down(db: Session, cancion_id: int, usuario_id: int):
    """
    Mueve una canciÃ³n (pendiente, pendiente_lazy o aprobado) hacia abajo en la cola del usuario.
    Solo funciona para canciones del usuario actual.
    """
    # 1. Validar que la canciÃ³n existe, estÃ¡ en pendiente, pendiente_lazy o aprobado, y pertenece al usuario
    cancion = db.query(models.Cancion).filter(
        models.Cancion.id == cancion_id,
        models.Cancion.estado.in_(['pendiente', 'pendiente_lazy', 'aprobado']),
        models.Cancion.usuario_id == usuario_id
    ).first()
    
    if not cancion:
        return None
    
    # 2. Obtener todas las canciones del usuario en estados pendiente, pendiente_lazy o aprobado, ordenadas
    canciones_usuario = (
        db.query(models.Cancion)
        .filter(
            models.Cancion.usuario_id == usuario_id,
            models.Cancion.estado.in_(['pendiente', 'pendiente_lazy', 'aprobado'])
        )
        .order_by(
            case((models.Cancion.orden_manual.is_(None), 1), else_=0),
            models.Cancion.orden_manual.asc(),
            models.Cancion.id.asc()
        )
        .all()
    )
    
    if len(canciones_usuario) <= 1:
        # Si hay solo una canciÃ³n, no se puede mover
        return cancion
    
    # 3. Encontrar el Ã­ndice de la canciÃ³n actual
    indice_actual = None
    for i, c in enumerate(canciones_usuario):
        if c.id == cancion_id:
            indice_actual = i
            break
    
    if indice_actual is None or indice_actual == len(canciones_usuario) - 1:
        # No encontrado o ya estÃ¡ al final
        return cancion
    
    # 4. Intercambiar orden con la canciÃ³n siguiente
    cancion_siguiente = canciones_usuario[indice_actual + 1]
    
    # Asignar orden entre la canciÃ³n siguiente y la anterior (si existe)
    if cancion_siguiente.orden_manual is not None:
        nuevo_orden = cancion_siguiente.orden_manual + 0.5
    else:
        # Ambas sin orden_manual, asignar a la siguiente
        cancion_siguiente.orden_manual = 1
        nuevo_orden = 2
    
    cancion.orden_manual = nuevo_orden
    db.commit()
    db.refresh(cancion)
    
    return cancion# ============================================================================
# FUNCIONES PARA SISTEMA DE CRÉDITOS DE CANCIONES
# ============================================================================

def get_lazy_queue_config() -> dict:
    """
    Obtiene la configuración actual de la cola lazy desde settings.
    Retorna un diccionario con los parámetros de control de entrada a la cola lazy.
    """
    settings = load_settings()
    return {
        "credit_multiplier": settings.get("lazy_queue_credit_multiplier", 1.0),
        "decay_rate": settings.get("lazy_queue_decay_rate", 100),
        "allow_unrestricted": settings.get("lazy_queue_allow_unrestricted", False),
        "max_concurrent_songs": settings.get("lazy_queue_max_concurrent_songs", 10)
    }


def add_song_credits(db: Session, usuario_id: int, credit_value: int):
    """
    Agrega créditos de canción a un usuario aplicando el multiplicador configurado.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return None
    
    # Obtener configuración de la cola lazy
    lazy_config = get_lazy_queue_config()
    credit_multiplier = lazy_config.get("credit_multiplier", 1.0)
    
    # Aplicar multiplicador al valor de créditos
    final_credit_value = int(float(credit_value) * credit_multiplier)
    
    # Crear nuevo registro de créditos
    new_credit = models.SongCredits(
        usuario_id=usuario_id,
        credits_value=final_credit_value,
        created_at=now_bogota()
    )
    db.add(new_credit)
    db.commit()
    db.refresh(new_credit)
    
    return new_credit

def get_available_song_credits(db: Session, usuario_id: int) -> int:
    """
    Obtiene los créditos disponibles para un usuario usando la tasa de decaimiento configurada.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return 0
    
    # Obtener configuración (incluyendo si está en modo sin restricciones)
    lazy_config = get_lazy_queue_config()
    allow_unrestricted = lazy_config.get("allow_unrestricted", False)
    
    # Si está en modo sin restricciones, retornar siempre un valor positivo
    if allow_unrestricted:
        return 1  # Retornar 1 para indicar que hay créditos disponibles
    
    # Obtener todos los créditos no consumidos del usuario
    credits = db.query(models.SongCredits).filter(
        models.SongCredits.usuario_id == usuario_id,
        models.SongCredits.consumed_at.is_(None),
        models.SongCredits.consumed_by_song_id.is_(None)
    ).all()
    
    total_credits = 0
    current_time = now_bogota()
    decay_rate = lazy_config.get("decay_rate", 100)  # Tasa de decaimiento por minuto
    
    for credit in credits:
        seconds_elapsed = safe_datetime_diff(current_time, credit.created_at)
        minutes_elapsed = seconds_elapsed / 60
        
        # Restar decay_rate puntos por minuto (configurable)
        remaining_credit = max(0, credit.credits_value - int(minutes_elapsed * decay_rate))
        
        if remaining_credit > 0:
            total_credits += remaining_credit
        else:
            # Marcar como expirado
            if credit.expires_at is None:
                credit.expires_at = ensure_aware(current_time)
                db.commit()
    
    return total_credits

def get_user_credits_detail(db: Session, usuario_id: int) -> dict:
    """
    Obtiene información detallada de los créditos de un usuario con la tasa configurada.
    """
    db_usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not db_usuario:
        return {"available_credits": 0, "credits_detail": [], "needs_purchase": False}
    
    lazy_config = get_lazy_queue_config()
    allow_unrestricted = lazy_config.get("allow_unrestricted", False)
    decay_rate = lazy_config.get("decay_rate", 100)
    
    if allow_unrestricted:
        return {
            "available_credits": 999999,
            "credits_detail": [{"status": "unrestricted"}],
            "needs_purchase": False,
            "minutes_to_zero": -1  # -1 indica modo sin restricciones
        }
    
    credits = db.query(models.SongCredits).filter(
        models.SongCredits.usuario_id == usuario_id,
        models.SongCredits.consumed_at.is_(None),
        models.SongCredits.consumed_by_song_id.is_(None)
    ).all()
    
    total_credits = 0
    current_time = now_bogota()
    credits_detail = []
    
    for credit in credits:
        seconds_elapsed = safe_datetime_diff(current_time, credit.created_at)
        minutes_elapsed = seconds_elapsed / 60
        remaining_credit = max(0, credit.credits_value - int(minutes_elapsed * decay_rate))
        minutes_remaining = max(0, (remaining_credit / decay_rate)) if decay_rate > 0 else 0
        
        if remaining_credit > 0:
            total_credits += remaining_credit
            credits_detail.append({
                "credit_id": credit.id,
                "original_value": credit.credits_value,
                "current_value": remaining_credit,
                "created_at": credit.created_at,
                "minutes_remaining": minutes_remaining
            })
    
    return {
        "available_credits": total_credits,
        "credits_detail": credits_detail,
        "needs_purchase": total_credits == 0,
        "minutes_to_zero": max(0, (total_credits / decay_rate)) if total_credits > 0 and decay_rate > 0 else 0
    }

def consume_song_credit(db: Session, usuario_id: int, cancion_id: int) -> bool:
    """
    Consume un crédito de canción cuando el usuario agrega una canción.
    Retorna True si hay crédito disponible, False si no.
    En modo sin restricciones, retorna True sin consumir crédito real.
    """
    lazy_config = get_lazy_queue_config()
    allow_unrestricted = lazy_config.get("allow_unrestricted", False)
    
    # En modo sin restricciones, permitir agregar sin consumir crédito
    if allow_unrestricted:
        return True
    
    available_credits = get_available_song_credits(db, usuario_id)
    
    if available_credits <= 0:
        return False
    
    decay_rate = lazy_config.get("decay_rate", 100)
    
    # Obtener el primer crédito que tenga valor disponible
    credits = db.query(models.SongCredits).filter(
        models.SongCredits.usuario_id == usuario_id,
        models.SongCredits.consumed_at.is_(None),
        models.SongCredits.consumed_by_song_id.is_(None)
    ).order_by(models.SongCredits.created_at).all()
    
    current_time = now_bogota()
    
    for credit in credits:
        seconds_elapsed = safe_datetime_diff(current_time, credit.created_at)
        minutes_elapsed = seconds_elapsed / 60
        remaining_credit = max(0, credit.credits_value - int(minutes_elapsed * decay_rate))
        
        if remaining_credit > 0:
            # Este crédito tiene valor, lo usamos para esta canción
            credit.consumed_at = ensure_aware(current_time)
            credit.consumed_by_song_id = cancion_id
            db.commit()
            return True
    
    return False
