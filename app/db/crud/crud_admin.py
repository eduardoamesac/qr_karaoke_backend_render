"""CRUD operations for Admin reporting and night-reset operations."""

import datetime
from collections import Counter
from sqlalchemy.orm import Session

from app.db.models import Usuario, Producto, Pago
from app.utils.cache_manager import cache_manager as cache


def get_resumen_noche(db: Session):
    """Obtiene un resumen de la noche desde datos en cache y BD."""
    consumos = cache.get_all_consumos()
    pagos = db.query(Pago).all()
    usuarios_activos_db = db.query(Usuario).filter(
        Usuario.is_active == True,
        Usuario.mesa_id.isnot(None)
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


def reset_database_for_new_night(db: Session):
    """
    Reinicia el sistema para una nueva noche.
    1. Limpia todo el caché JSON (canciones, consumos, balances, mesas).
    2. Elimina todos los pagos de la BD (son datos de la noche anterior).
    3. Resetea créditos y puntos de usuarios en la DB.
    4. Desconecta a todos los usuarios de sus mesas.
    """
    cache.clear_all()

    db.query(Pago).delete()

    db.query(Usuario).update({
        "song_credits": 0,
        "puntos": 0,
        "nivel": "bronce",
        "mesa_id": None,
        "is_active": False
    })

    db.commit()
    return True


def get_ganancias_totales(db: Session):
    """Obtiene las ganancias reales (ventas - costo de productos vendidos)."""
    consumos = cache.get_all_consumos()
    productos = db.query(Producto).all()

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


def limpiar_datos_prueba(db: Session):
    """Limpia todos los datos (solo para desarrollo/pruebas)."""
    db.query(Pago).delete()
    db.query(Usuario).delete()
    db.query(Producto).delete()
    db.commit()
    cache.clear_all()


# ================================================================================
# REPORTES Y ESTADÍSTICAS
# ================================================================================

def get_canciones_mas_cantadas(db: Session, limit: int = 10):
    """Reporte de canciones más cantadas."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    counts = Counter((s.get("titulo"), s.get("youtube_id")) for s in cantadas)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [(titulo, y_id, count) for (titulo, y_id), count in items]


def get_productos_mas_consumidos(db: Session, limit: int = 10):
    """Reporte de productos más consumidos."""
    consumos = cache.get_all_consumos()
    product_counts = Counter()
    for c in consumos:
        product_counts[c.get("producto_id")] += c.get("cantidad", 0)

    product_ids = [p_id for p_id, _ in product_counts.most_common(limit)]
    productos = db.query(Producto).filter(Producto.id.in_(product_ids)).all()
    prod_map = {p.id: p.nombre for p in productos}

    return [
        (prod_map.get(p_id, f"Producto #{p_id}"), count)
        for p_id, count in product_counts.most_common(limit)
    ]


def get_usuarios_sin_consumo(db: Session):
    """Usuarios que no han realizado consumos."""
    consumos = cache.get_all_consumos()
    usuarios_con_consumo = {c.get("usuario_id") for c in consumos}
    return db.query(Usuario).filter(~Usuario.id.in_(usuarios_con_consumo)).all()


def get_canciones_cantadas_por_usuario(db: Session):
    """Reporte de canciones cantadas por cada usuario."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    user_counts = Counter(s.get("usuario_id") for s in cantadas)
    user_ids = list(user_counts.keys())
    usuarios = db.query(Usuario).filter(Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}
    results = [
        (user_map.get(u_id, f"Usuario #{u_id}"), count)
        for u_id, count in user_counts.items()
    ]
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_ingresos_promedio_por_usuario(db: Session):
    """Ingresos promedio por cada usuario que ha consumido."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return 0
    total_ingresos = sum(float(c.get("valor_total", 0)) for c in consumos)
    num_usuarios = len({c.get("usuario_id") for c in consumos})
    return total_ingresos / num_usuarios if num_usuarios > 0 else 0


def get_usuarios_una_cancion(db: Session):
    """Usuarios que han cantado exactamente una canción."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]
    user_counts = Counter(s.get("usuario_id") for s in cantadas)
    one_hit_ids = [u_id for u_id, count in user_counts.items() if count == 1]
    return db.query(Usuario).filter(Usuario.id.in_(one_hit_ids)).all()


def get_mesas_vacias(db: Session):
    """Mesas sin usuarios conectados."""
    mesas = cache.get_all_mesas()
    usuarios = db.query(Usuario).all()
    mesas_con_usuarios = {u.mesa_id for u in usuarios if u.mesa_id}
    return [m for m in mesas if m.get("id") not in mesas_con_usuarios]


def get_ingresos_promedio_por_usuario_por_mesa(db: Session):
    """Reporte de ingresos promedio por usuario en cada mesa."""
    mesas = cache.get_all_mesas()
    consumos = cache.get_all_consumos()
    usuarios = db.query(Usuario).all()
    user_to_mesa = {u.id: u.mesa_id for u in usuarios if u.mesa_id}

    mesa_income = Counter()
    mesa_users = {m.get("id"): set() for m in mesas}

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


def get_tiempo_promedio_espera(db: Session):
    """Tiempo promedio de espera (created_at hasta finished_at)."""
    all_songs = cache.get_all_songs()
    cantadas = [
        s for s in all_songs
        if s.get("estado") == "cantada" and s.get("finished_at") and s.get("created_at")
    ]
    if not cantadas:
        return 0

    total_seconds = 0
    for s in cantadas:
        try:
            start = datetime.datetime.fromisoformat(s.get("created_at"))
            end = datetime.datetime.fromisoformat(s.get("finished_at"))
            total_seconds += (end - start).total_seconds()
        except Exception:
            continue

    return total_seconds / len(cantadas)


def get_actividad_por_hora(db: Session):
    """Reporte de canciones cantadas por hora."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada" and s.get("started_at")]

    hora_counts = Counter()
    for s in cantadas:
        try:
            dt = datetime.datetime.fromisoformat(s.get("started_at"))
            hora_counts[dt.hour] += 1
        except Exception:
            continue

    return sorted(hora_counts.items(), key=lambda x: x[1], reverse=True)


def get_canciones_cantadas_por_mesa(db: Session):
    """Cantidad de canciones cantadas por mesa."""
    all_songs = cache.get_all_songs()
    cantadas = [s for s in all_songs if s.get("estado") == "cantada"]

    usuarios = db.query(Usuario).all()
    user_to_mesa = {u.id: u.mesa_id for u in usuarios if u.mesa_id}

    mesa_counts = Counter()
    for s in cantadas:
        m_id = user_to_mesa.get(s.get("usuario_id"))
        if m_id:
            mesa_counts[m_id] += 1

    mesas = {m.get("id"): m.get("nombre") for m in cache.get_all_mesas()}
    results = [
        (mesas.get(m_id, f"Mesa #{m_id}"), count)
        for m_id, count in mesa_counts.items()
    ]
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_canciones_mas_rechazadas(db: Session, limit: int = 10):
    """Reporte de canciones más rechazadas."""
    all_songs = cache.get_all_songs()
    rechazadas = [s for s in all_songs if s.get("estado") == "rechazada"]
    counts = Counter((s.get("titulo"), s.get("youtube_id")) for s in rechazadas)
    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [(titulo, y_id, count) for (titulo, y_id), count in items]


def get_usuarios_mas_rechazados(db: Session, limit: int = 10):
    """Usuarios con más canciones rechazadas."""
    all_songs = cache.get_all_songs()
    rechazadas = [s for s in all_songs if s.get("estado") == "rechazada"]
    user_counts = Counter(s.get("usuario_id") for s in rechazadas)
    user_ids = [u_id for u_id, _ in user_counts.most_common(limit)]
    usuarios = db.query(Usuario).filter(Usuario.id.in_(user_ids)).all()
    user_map = {u.id: u.nick for u in usuarios}
    return [
        (user_map.get(u_id, f"Usuario #{u_id}"), count)
        for u_id, count in user_counts.most_common(limit)
    ]


def get_ingresos_por_categoria(db: Session):
    """Ingresos por categoría de producto."""
    consumos = cache.get_all_consumos()
    if not consumos:
        return []
    product_ids = {c.get("producto_id") for c in consumos}
    productos = db.query(Producto).filter(Producto.id.in_(product_ids)).all()
    prod_cat_map = {p.id: p.categoria for p in productos}
    cat_income = Counter()
    for c in consumos:
        cat = prod_cat_map.get(c.get("producto_id"), "Sin Categoría")
        cat_income[cat] += float(c.get("valor_total", 0))
    return sorted(cat_income.items(), key=lambda x: x[1], reverse=True)


def get_total_ingresos(db: Session):
    consumos = cache.get_all_consumos()
    return sum(float(c.get("valor_total", 0)) for c in consumos)


def get_ingresos_por_mesa(db: Session):
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
    result = [(mesas[mid], total) for mid, total in ingresos.items() if mid in mesas]
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def get_productos_menos_consumidos(db: Session, limit: int = 5):
    consumos = cache.get_all_consumos()
    productos = db.query(Producto).all()
    cantidades = {p.id: 0 for p in productos}
    for c in consumos:
        pid = c.get("producto_id")
        if pid in cantidades:
            cantidades[pid] += c.get("cantidad", 1)
    prod_map = {p.id: p.nombre for p in productos}
    result = [(prod_map[pid], cant) for pid, cant in cantidades.items()]
    result.sort(key=lambda x: x[1])
    return result[:limit]


def get_top_consumers_one_song(db: Session, limit: int = 10):
    canciones = cache.get_all_songs()
    consumos = cache.get_all_consumos()
    usuarios = db.query(Usuario).all()
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


def get_categorias_mas_consumidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    consumos = [c for c in cache.get_all_consumos() if c.get("mesa_id") == mesa_id]
    productos = db.query(Producto).all()
    prod_cat_map = {p.id: p.categoria for p in productos}
    cat_counts = {}
    for c in consumos:
        pid = c.get("producto_id")
        cat = prod_cat_map.get(pid, "Desconocida")
        cat_counts[cat] = cat_counts.get(cat, 0) + c.get("cantidad", 1)
    result = list(cat_counts.items())
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]


def get_canciones_mas_pedidas_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    usuarios_mesa = [u.id for u in db.query(Usuario).filter(Usuario.mesa_id == mesa_id).all()]
    canciones = [c for c in cache.get_all_songs() if c.get("usuario_id") in usuarios_mesa]
    counts = {}
    for c in canciones:
        key = (c.get("titulo", "Desconocido"), c.get("youtube_id", ""))
        counts[key] = counts.get(key, 0) + 1
    result = [(titulo, yid, count) for (titulo, yid), count in counts.items()]
    result.sort(key=lambda x: x[2], reverse=True)
    return result[:limit]


def get_productos_mas_consumidos_por_mesa(db: Session, mesa_id: int, limit: int = 5):
    consumos = [c for c in cache.get_all_consumos() if c.get("mesa_id") == mesa_id]
    productos = db.query(Producto).all()
    prod_map = {p.id: p.nombre for p in productos}
    counts = {}
    for c in consumos:
        pid = c.get("producto_id")
        counts[pid] = counts.get(pid, 0) + c.get("cantidad", 1)
    result = [(prod_map.get(pid, "Desconocido"), count) for pid, count in counts.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result[:limit]


def get_productos_no_consumidos(db: Session):
    consumos = cache.get_all_consumos()
    productos = db.query(Producto).all()
    consumidos_ids = {c.get("producto_id") for c in consumos}
    return [p for p in productos if p.id not in consumidos_ids]


def get_usuarios_inactivos_consumo(db: Session, horas: int = 2):
    consumos = cache.get_all_consumos()
    usuarios = db.query(Usuario).all()
    last_consumo = {}

    from datetime import datetime as dt, timedelta
    for c in consumos:
        uid = c.get("usuario_id")
        created = c.get("created_at")
        if uid and created:
            try:
                created = created.replace("Z", "+00:00")
                d = dt.fromisoformat(created)
                if uid not in last_consumo or d > last_consumo[uid]:
                    last_consumo[uid] = d
            except ValueError:
                pass

    from app.utils.timezone_utils import now_bogota
    now = now_bogota()

    for uid in last_consumo:
        if last_consumo[uid].tzinfo is None:
            last_consumo[uid] = last_consumo[uid].replace(tzinfo=now.tzinfo)

    inactivos = []
    for u in usuarios:
        if u.id not in last_consumo:
            inactivos.append(u)
        else:
            diff = now - last_consumo[u.id]
            if diff > timedelta(hours=horas):
                inactivos.append(u)
    return inactivos


def get_usuarios_consumen_pero_no_cantan(db: Session, umbral_consumo: float = 100.0):
    canciones = cache.get_all_songs()
    consumos = cache.get_all_consumos()
    usuarios = db.query(Usuario).all()
    cantores = {c.get("usuario_id") for c in canciones if c.get("usuario_id")}
    gastos = {}
    for c in consumos:
        uid = c.get("usuario_id")
        if uid:
            gastos[uid] = gastos.get(uid, 0) + float(c.get("valor_total", 0))
    return [
        u for u in usuarios
        if u.id not in cantores and gastos.get(u.id, 0) > umbral_consumo
    ]
