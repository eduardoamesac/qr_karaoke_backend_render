"""
Módulo CRUD para Consumos y Reportes Financieros.
Gestiona pedidos (CACHE JSON) y reportes de ingresos.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime
from decimal import Decimal
from collections import Counter
from types import SimpleNamespace

import models
import schemas
from cache_manager import cache_manager as cache


# ================================================================================
# FUNCIONES PARA CONSUMOS (En CACHE JSON)
# ================================================================================

def get_consumos_mesa(db: Session, mesa_id: int):
    """Obtiene todos los consumos de una mesa (CACHE)."""
    return cache.get_consumos_by_mesa(mesa_id)


def create_consumo_para_usuario(db: Session, consumo: schemas.ConsumoCreate, usuario_id: int):
    """
    Crea un nuevo consumo. El consumo se asigna a la MESA, no al usuario individual.
    """
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        return None, "Usuario no encontrado."

    if not usuario.mesa_id:
        return None, "El usuario no está asociado a ninguna mesa."

    db_producto = db.query(models.Producto).filter(
        models.Producto.id == consumo.producto_id
    ).first()
    if not db_producto:
        return None, "Producto no encontrado."

    if db_producto.stock < consumo.cantidad:
        return None, f"Stock insuficiente. Disponible: {db_producto.stock}"

    valor_total = float(db_producto.valor * consumo.cantidad)

    consumo_obj = {
        "cantidad": consumo.cantidad,
        "valor_total": valor_total,
        "mesa_id": usuario.mesa_id,
        "usuario_id": usuario_id,
        "producto_id": consumo.producto_id,
        "created_at": datetime.datetime.now().isoformat(),
        "is_dispatched": False,
        "is_cancelled": False
    }

    consumo_id = cache.create_consumo_in_cache(consumo_obj)
    consumo_obj["id"] = consumo_id

    from settings_storage import load_settings
    settings = load_settings()
    credit_multiplier = settings.get("lazy_queue_credit_multiplier", 1.0)

    creditos_ganados = int(valor_total * credit_multiplier)
    if creditos_ganados > 0:
        usuario.song_credits = (usuario.song_credits or 0) + creditos_ganados
        db.add(usuario)

    db_producto.stock -= consumo.cantidad
    db.add(db_producto)

    db.commit()
    db.refresh(usuario)

    db_consumo = SimpleNamespace(**consumo_obj)
    db_consumo.usuario = usuario
    db_consumo.producto = db_producto
    db_consumo.valor_total = Decimal(str(valor_total))
    db_consumo.created_at = datetime.datetime.fromisoformat(consumo_obj["created_at"])

    return db_consumo, None


def create_pedido_from_carrito(db: Session, carrito: schemas.CarritoCreate, usuario_id: int):
    """Crea múltiples consumos desde un carrito."""
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario or not usuario.mesa_id:
        return None, "Usuario o mesa no encontrados."

    consumos_creados = []
    for item in carrito.items:
        consumo_data = schemas.ConsumoCreate(
            producto_id=item.producto_id, cantidad=item.cantidad
        )
        db_consumo, error = create_consumo_para_usuario(db, consumo_data, usuario_id)
        if error:
            return None, error
        consumos_creados.append(db_consumo)

    return consumos_creados, None


def get_recent_consumos(db: Session, limit: int = 10):
    """Obtiene los consumos más recientes desde el cache e hidrata con nombres de BD."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []

    consumos_pendientes = [c for c in consumos if not c.get("is_dispatched", False)]

    sorted_consumos = sorted(
        consumos_pendientes,
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    recent = sorted_consumos[:limit]

    if not recent:
        return []

    user_ids = {c.get("usuario_id") for c in recent if c.get("usuario_id")}
    prod_ids = {c.get("producto_id") for c in recent if c.get("producto_id")}

    usuarios = (
        db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all()
        if user_ids else []
    )
    productos = (
        db.query(models.Producto).filter(models.Producto.id.in_(prod_ids)).all()
        if prod_ids else []
    )

    user_map = {u.id: u.nick for u in usuarios}
    prod_map = {p.id: p.nombre for p in productos}
    mesa_map = {m.get("id"): m.get("nombre") for m in cache.get_all_mesas()}

    enriched = []
    for c in recent:
        c_copy = dict(c)
        c_copy["usuario_nick"] = user_map.get(c.get("usuario_id"), "Desconocido")
        c_copy["producto_nombre"] = prod_map.get(c.get("producto_id"), "Desconocido")
        if c.get("mesa_id"):
            c_copy["mesa_nombre"] = mesa_map.get(c.get("mesa_id"))
        enriched.append(c_copy)

    return enriched


def delete_consumo(db: Session, consumo_id: int):
    """Elimina un consumo del caché, restaura el stock del producto y recalcula créditos."""
    consumo = cache.get_consumo_by_id(consumo_id)
    if not consumo:
        return False

    db_producto = db.query(models.Producto).filter(
        models.Producto.id == consumo["producto_id"]
    ).first()
    if db_producto:
        db_producto.stock += consumo["cantidad"]
        db.add(db_producto)

    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == consumo["usuario_id"]
    ).first()
    if usuario:
        from settings_storage import load_settings
        settings = load_settings()
        credit_multiplier = settings.get("lazy_queue_credit_multiplier", 1.0)
        creditos_a_restar = int(consumo["valor_total"] * credit_multiplier)
        if creditos_a_restar > 0:
            usuario.song_credits = max(0, (usuario.song_credits or 0) - creditos_a_restar)
            db.add(usuario)

    db.commit()
    return cache.delete_consumo_from_cache(consumo_id)


def update_consumo_cantidad(db: Session, consumo_id: int, delta: int):
    """Incrementa o decrementa la cantidad de un consumo. Actualiza stock y créditos."""
    consumo = cache.get_consumo_by_id(consumo_id)
    if not consumo:
        return None, "Consumo no encontrado"

    nueva_cantidad = consumo["cantidad"] + delta
    if nueva_cantidad < 1:
        return None, "La cantidad mínima es 1. Para eliminar use el botón cancelar."

    db_producto = db.query(models.Producto).filter(
        models.Producto.id == consumo["producto_id"]
    ).first()
    if not db_producto:
        return None, "Producto no encontrado"

    if delta > 0 and db_producto.stock < delta:
        return None, f"Stock insuficiente. Disponible: {db_producto.stock}"

    db_producto.stock -= delta
    db.add(db_producto)

    valor_unitario = float(db_producto.valor)
    valor_delta = valor_unitario * delta
    nuevo_valor_total = float(consumo["valor_total"]) + valor_delta

    usuario = db.query(models.Usuario).filter(
        models.Usuario.id == consumo["usuario_id"]
    ).first()
    if usuario:
        from settings_storage import load_settings
        settings = load_settings()
        credit_multiplier = settings.get("lazy_queue_credit_multiplier", 1.0)
        creditos_delta = int(valor_delta * credit_multiplier)
        if creditos_delta != 0:
            usuario.song_credits = max(0, (usuario.song_credits or 0) + creditos_delta)
            db.add(usuario)

    db.commit()

    updates = {
        "cantidad": nueva_cantidad,
        "valor_total": nuevo_valor_total
    }
    cache.update_consumo_in_cache(consumo_id, updates)

    consumo.update(updates)
    return consumo, None


# ================================================================================
# REPORTES FINANCIEROS
# ================================================================================

def get_total_ingresos(db: Session):
    """Total de ingresos de la noche."""
    consumos = cache.get_all_consumos()
    return sum(float(c.get("valor_total", 0)) for c in consumos)


def get_ganancias_totales(db: Session):
    """Ganancias reales (ventas - costo de productos vendidos)."""
    consumos = cache.get_all_consumos()
    productos = db.query(models.Producto).all()

    costo_map = {p.id: float(p.costo or 0) for p in productos}

    ganancia_real = 0.0
    for c in consumos:
        prod_id = c.get("producto_id")
        cantidad = int(c.get("cantidad", 1))
        venta_total = float(c.get("valor_total", 0))

        costo_unitario = costo_map.get(prod_id, 0.0)
        costo_total = costo_unitario * cantidad

        ganancia_real += (venta_total - costo_total)

    return ganancia_real


def get_ingresos_por_mesa(db: Session):
    """Ingresos totales por mesa."""
    consumos = cache.get_all_consumos()
    mesas_list = cache.get_all_mesas()
    mesas = {m["id"]: m.get("nombre", f"Mesa {m.get('id')}") for m in mesas_list}
    ingresos = {}
    for c in consumos:
        mesa_id = c.get("mesa_id")
        if not mesa_id:
            continue
        val = float(c.get("valor_total", 0))
        ingresos[mesa_id] = ingresos.get(mesa_id, 0) + val
    result = []
    for mid, total in ingresos.items():
        if mid in mesas:
            result.append((mesas[mid], total))
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def get_ingresos_por_categoria(db: Session):
    """Ingresos por categoría de producto."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []

    product_ids = {c.get("producto_id") for c in consumos}
    productos = db.query(models.Producto).filter(
        models.Producto.id.in_(product_ids)
    ).all()
    prod_cat_map = {p.id: p.categoria for p in productos}

    cat_income = Counter()
    for c in consumos:
        cat = prod_cat_map.get(c.get("producto_id"), "Sin Categoría")
        cat_income[cat] += float(c.get("valor_total", 0))

    return sorted(cat_income.items(), key=lambda x: x[1], reverse=True)


def get_ingresos_promedio_por_usuario(db: Session):
    """Ingresos promedio por cada usuario que ha consumido."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return 0

    total_ingresos = sum(float(c.get("valor_total", 0)) for c in consumos)
    num_usuarios = len({c.get("usuario_id") for c in consumos})

    return total_ingresos / num_usuarios if num_usuarios > 0 else 0


def get_ingresos_promedio_por_usuario_por_mesa(db: Session):
    """Reporte de ingresos promedio por usuario en cada mesa."""
    mesas = cache.get_all_mesas()
    consumos = cache.get_all_consumos()

    mesa_income = Counter()
    mesa_users = {m.get("id"): set() for m in mesas}

    usuarios = db.query(models.Usuario).all()
    user_to_mesa = {u.id: u.mesa_id for u in usuarios if u.mesa_id}

    for c in consumos:
        u_id = c.get("usuario_id")
        m_id = user_to_mesa.get(u_id)
        if m_id:
            mesa_income[m_id] += float(c.get("valor_total", 0))
            mesa_users[m_id].add(u_id)

    report = []
    for m in mesas:
        m_id = m.get("id")
        m_name = m.get("nombre", f"Mesa {m_id}")
        num_users = len([u for u in usuarios if u.mesa_id == m_id])
        total = mesa_income[m_id]
        promedio = total / num_users if num_users > 0 else 0
        report.append((m_name, promedio))

    return sorted(report, key=lambda x: x[1], reverse=True)


def get_usuarios_mayor_gasto_por_categoria(db: Session):
    """Usuarios con mayor gasto por categoría de producto."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []

    product_ids = {c.get("producto_id") for c in consumos}
    productos = db.query(models.Producto).filter(
        models.Producto.id.in_(product_ids)
    ).all()
    prod_cat_map = {p.id: p.categoria for p in productos}

    user_cat_spend: dict[int, dict] = {}
    for c in consumos:
        uid = c.get("usuario_id")
        cat = prod_cat_map.get(c.get("producto_id"), "Sin Categoría")
        val = float(c.get("valor_total", 0))
        if uid not in user_cat_spend:
            user_cat_spend[uid] = {}
        user_cat_spend[uid][cat] = user_cat_spend[uid].get(cat, 0) + val

    user_ids = list(user_cat_spend.keys())
    usuarios = db.query(models.Usuario).filter(models.Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}

    result = []
    for uid, cats in user_cat_spend.items():
        for cat, total in cats.items():
            result.append((user_map.get(uid, f"Usuario #{uid}"), cat, total))

    result.sort(key=lambda x: x[2], reverse=True)
    return result


def get_top_consumers_one_song(db: Session, limit: int = 10):
    """Usuarios que más han consumido pero que solo han cantado una canción."""
    canciones = cache.get_all_songs()
    consumos = cache.get_all_consumos()
    usuarios = db.query(models.Usuario).all()
    user_map = {u.id: u.nick for u in usuarios}

    canciones_por_user = {}
    for c in canciones:
        uid = c.get("usuario_id")
        if uid:
            canciones_por_user[uid] = canciones_por_user.get(uid, 0) + 1

    users_one_song = {uid for uid, count in canciones_por_user.items() if count == 1}

    gastos = {}
    for c in consumos:
        uid = c.get("usuario_id")
        if uid in users_one_song:
            gastos[uid] = gastos.get(uid, 0) + float(c.get("valor_total", 0))

    result = [(user_map.get(uid, f"User {uid}"), total) for uid, total in gastos.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]


def get_resumen_noche(db: Session):
    """Obtiene un resumen de la noche desde datos en cache y BD."""
    consumos = cache.get_all_consumos()
    pagos = db.query(models.Pago).all()
    usuarios_activos_db = db.query(models.Usuario).filter(
        models.Usuario.is_active == True,
        models.Usuario.mesa_id.isnot(None)
    ).all()

    total_consumido = sum(float(c.get("valor_total", 0)) for c in consumos)
    total_pagado = sum(float(p.monto) for p in pagos)
    saldo = total_consumido - total_pagado

    return {
        "total_consumido": float(total_consumido),
        "total_pagado": float(total_pagado),
        "saldo": float(saldo),
        "num_consumos": len(consumos),
        "num_pagos": len(pagos),
        "num_usuarios": len(usuarios_activos_db),
        "num_canciones": len(cache.get_all_songs()),
        "mesas_activas": len(cache.get_all_mesas()),
        "ingresos_totales": float(total_consumido),
        "canciones_cantadas": len(cache.get_all_songs()),
        "usuarios_activos": len(usuarios_activos_db)
    }


def get_categorias_mas_consumidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    """Reporte de categorías más consumidas en una mesa específica."""
    consumos = [c for c in cache.get_all_consumos() if c.get("mesa_id") == mesa_id]
    productos = db.query(models.Producto).all()
    prod_cat_map = {p.id: p.categoria for p in productos}

    cat_counts = {}
    for c in consumos:
        pid = c.get("producto_id")
        cat = prod_cat_map.get(pid, "Desconocida")
        cat_counts[cat] = cat_counts.get(cat, 0) + c.get("cantidad", 1)

    result = list(cat_counts.items())
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]
