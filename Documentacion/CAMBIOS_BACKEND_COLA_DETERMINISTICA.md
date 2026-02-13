# 🔧 GUÍA TÉCNICA: Cambios en el Backend - Cola Determinística

## 📋 Resumen de Cambios

**Archivo nuevo:** `queue_synchronizer.py`  
**Archivos modificados:**
- `websocket_manager.py` - Mejora broadcast_queue_update
- `admin.py` - Endpoints move-up, move-down, approve-next, revert-approve
- `queue_manager.py` - Sin cambios estructurales

---

## 🎯 NUEVOS COMPONENTES

### 1. QueueSynchronizer (queue_synchronizer.py)

```python
from queue_synchronizer import QueueSynchronizer

class QueueSynchronizer:
    @staticmethod
    def get_definitive_state(db: Session) -> Dict[str, Any]
    # Retorna estado ACTUAL, sincronizado desde BD, validado
    
    @staticmethod
    def increment_revision(db: Session) -> int
    # Incrementa versión para invalidar cache frontend
    
    @staticmethod
    def validate_song_still_valid(db: Session, cancion_id: int, expected_state: str) -> bool
    # Valida que canción existe y está en estado esperado
    
    @staticmethod
    def reorder_lazy_queue_safely(db: Session, cancion_id: int, direction: str) -> Dict
    # Reordena con validaciones y retorna estado definitivo
    
    @staticmethod
    def detect_desynchronization(db: Session) -> Dict[str, Any]
    # Detecta problemas de sincronización (para debugging)
```

---

## 🔄 FLUJO DE CAMBIO (ANTES vs DESPUÉS)

### ❌ ANTES (Inseguro)

```python
@router.post("/canciones/lazy/{cancion_id}/move-up")
async def move_lazy_song_up(cancion_id: int, db: Session):
    # 1. Obtener cola (asume que sigue siendo válida)
    cola_lazy = crud.get_cola_lazy(db)
    
    # 2. Reordenar en MEMORIA
    current_index = find_index(cola_lazy, cancion_id)
    if current_index > 0:
        cola_lazy[current_index], cola_lazy[current_index-1] = swap
    
    # 3. Actualizar BD
    for idx, song in enumerate(cola_lazy):
        song.orden_manual = idx + 1
    db.commit()
    
    # ⚠️ PROBLEMAS:
    # - No valida que canción no esté reproduciéndose
    # - No valida tiempo de la transacción
    # - No incrementa versión
    # - Broadcast retorna estado CALCULADO (puede estar obsoleto)
    
    queue_manager.refresh_queue(db)
    await websocket_manager.broadcast_queue_update()
```

### ✅ DESPUÉS (Seguro)

```python
@router.post("/canciones/lazy/{cancion_id}/move-up")
async def move_lazy_song_up(cancion_id: int, db: Session):
    from queue_synchronizer import QueueSynchronizer
    
    # 1. Operación determinística y segura
    result = QueueSynchronizer.reorder_lazy_queue_safely(
        db,
        cancion_id=cancion_id,
        direction="up",
        audit_user="api_key_xyz"
    )
    
    # 2. Validar resultado
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # 3. Incrementar versión (ya hecho en QueueSynchronizer)
    # 4. Log de auditoría
    crud.create_admin_log_entry(db, action="MOVE_LAZY_UP", details=...)
    
    # 5. Broadcast DEFINITIVO (incluye integridad)
    await websocket_manager.broadcast_queue_update()
    
    # ✅ SEGURIDADES:
    # ✓ Validó que canción está en "pendiente_lazy"
    # ✓ Validó que NO está "reproduciendo"
    # ✓ Incrementó versión para invalidar cache
    # ✓ Broadcast retorna estado DEFINITIVO
    # ✓ Log de auditoría
    
    return {
        "success": True,
        "queue_state": result["queue_state"]
    }
```

---

## 🏢 REGLAS DE OPERACIÓN (NUEVAS)

### Regla 1: Autoridad única
```
ANTES: Backend calculaba al pedir, frontend asumía
DESPUÉS: Backend es autoridad SIEMPRE
         Frontend NUNCA asume, SIEMPRE confía en backend
```

### Regla 2: Cambios atómicos
```
ANTES: Cambio en BD + Broadcast separados = ventana de inconsistencia
DESPUÉS: 
  1. Validar estado actual
  2. Cambiar en BD (transacción)
  3. Incrementar revisión
  4. Broadcast estado definitivo
  TODO EN UNA SECUENCIA ATÓMICA
```

### Regla 3: Invalidar cache
```
ANTES: Frontend seguía usando datos viejos si los tenía
DESPUÉS: Cada cambio incrementa revision
         Frontend detecta cambio y descarta cache
```

### Regla 4: Validación de integridad
```
ANTES: Sin validaciones, state corruption silencioso
DESPUÉS: Cada estado incluye _integrity_checks
         Frontend valida antes de renderizar
         Backend detecta corrupción y alerta
```

---

## 📊 ENDPOINTS MEJORADOS

### 1. GET /admin/queue/state (NUEVO)

Retorna el estado DEFINITIVO en este instante.

**Response:**
```json
{
  "timestamp": "2024-02-13T15:30:45.123456Z",
  "revision": 42,
  "now_playing": {...},
  "upcoming": [...],
  "lazy_queue": [...],
  "pending": [...],
  "_integrity_checks": {
    "now_playing_not_in_upcoming": true,
    "all_upcoming_states_approved": true,
    "all_lazy_states_pending_lazy": true
  }
}
```

---

### 2. POST /admin/canciones/lazy/{id}/move-up (MEJORADO)

**Cambios:**
- Usa `QueueSynchronizer.reorder_lazy_queue_safely()`
- Retorna estado definitivo con revisión
- Valida que canción NO esté reproduciendo

**Response:**
```json
{
  "mensaje": "Canción movida hacia arriba",
  "queue_state": {
    "timestamp": "...",
    "revision": 43,
    ...completo...
  }
}
```

---

### 3. POST /admin/canciones/lazy/approve-next (MEJORADO)

**Cambios:**
- Incrementa versión explícitamente
- Retorna estado definitivo
- Log de auditoría con revisión

**Response:**
```json
{
  "mensaje": "Canción 'Bohemian Rhapsody' aprobada",
  "cancion_aprobada": {...},
  "queue_state": {...}
}
```

---

## 🔍 DEBUGGING

### Detectar desincronización

```python
from queue_synchronizer import QueueSynchronizer

# Desde Python shell
db = SessionLocal()
issues = QueueSynchronizer.detect_desynchronization(db)
print(f"Clean: {issues['clean']}")
for issue in issues['issues']:
    print(f" - {issue}")
```

### Forzar sincronización

```python
from queue_manager import queue_manager
db = SessionLocal()
queue_manager.refresh_all(db)
print("✓ Cache sincronizado")
```

### Ver logs de cambios

```bash
# Grep de los últimos cambios de cola
grep "REORDER_LAZY\|APPROVE_LAZY\|MOVE_LAZY" app.log | tail -20
```

---

## 📋 VALIDACIONES IMPLEMENTADAS

### En `reorder_lazy_queue_safely()`

```python
# 1. Canción existe
if not cancion:
    return {"success": False, "error": "Canción no encontrada"}

# 2. Canción está en estado correcto
if cancion.estado != "pendiente_lazy":
    return {"success": False, "error": f"Canción está en {cancion.estado}"}

# 3. Canción NO está reproduciéndose
if cancion.estado == "reproduciendo":
    return {"success": False, "error": "No se puede reordenar: canción está reproduciendo"}

# 4. Canción está en cola_lazy actual
if cancion_id not in cola_ids:
    return {"success": False, "error": "Canción no está en lazy (inconsistencia)"}

# 5. No está en el límite
if direction == "up" and current_idx == 0:
    return {"success": False, "error": "Canción ya está en el principio"}

# ... después de cambio ...

# 6. Validar integridad del estado final
if not new_state["_integrity_checks"]["now_playing_not_in_upcoming"]:
    logger.error("CRITICAL: now_playing en upcoming after reorder!")
```

---

## 🚨 MANEJO DE ERRORES

### Caso: Canción desapareció de lazy entre request y cambio

```python
# QueueSynchronizer detecta:
# "Canción no está en cola lazy (inconsistencia detectada)"

# Frontend recibe 400:
{
  "error": "Canción no está en cola lazy (inconsistencia detectada)",
  "cancion_id": 105
}

# Frontend debe:
# 1. Mostrar error al admin
# 2. Hacer GET /admin/queue/state para sincronizar
# 3. Renderizar estado actual
```

### Caso: Revision number no incrementa

```python
# Backend loguea warning:
# "REORDER_LAZY_SUCCESS: Song 105 moved up. Revision: 42"

# Si revision NO incrementó (sigue siendo 42):
# PROBLEMA CRÍTICO - revisar que increment_revision() fue llamado
```

---

## 📈 PERFORMANCE

### Impacto de `get_definitive_state()`

```
Antiguo: crud.get_cola_completa_con_lazy() = 1 query al cache
Nuevo:  QueueSynchronizer.get_definitive_state() = 
        - refresh_all() → 4 queries (now_playing, approved, lazy, pending)
        - Validaciones de integridad
        - Serialización

Tiempo: ~50-100ms por estado (aceptable para admin dashboard)
```

### Optimización posible

Si el admin hace muchos cambios rápidamente:
```python
# Cache corto término (5 segundos) si no hay cambios
# Útil para GET /admin/queue/state repetidas rápidamente
cache = {}
cache_time = 0

@staticmethod
def get_definitive_state_cached(db, max_age_seconds=5):
    import time
    now = time.time()
    if cache and (now - cache_time) < max_age_seconds:
        return cache
    
    state = QueueSynchronizer.get_definitive_state(db)
    cache = state
    cache_time = now
    return state
```

---

## 🔄 MIGRACIÓN DE CÓDIGO EXISTENTE

### Paso 1: Importar QueueSynchronizer

```python
from queue_synchronizer import QueueSynchronizer
```

### Paso 2: Reemplazar endpoints

Para cada endpoint que cambia cola:

```python
# ❌ VIEJO
queue_manager.refresh_queue(db)
await websocket_manager.broadcast_queue_update()

# ✅ NUEVO
new_revision = QueueSynchronizer.increment_revision(db)
await websocket_manager.broadcast_queue_update()
# WebSocket ahora usa get_definitive_state internamente
```

### Paso 3: Retornar estado definitivo

```python
# ❌ VIEJO
return {"mensaje": "Hecho"}

# ✅ NUEVO
state = QueueSynchronizer.get_definitive_state(db)
return {
    "mensaje": "Hecho",
    "queue_state": state
}
```

---

## 🧪 TESTING

### Test: Mover canción no cambia now_playing

```python
def test_move_lazy_preserves_now_playing():
    # Arrange
    now_playing = create_song(estado="reproduciendo")
    lazy_song = create_song(estado="pendiente_lazy")
    
    # Act
    result = QueueSynchronizer.reorder_lazy_queue_safely(
        db, lazy_song.id, "up"
    )
    
    # Assert
    assert result["success"] == True
    state = result["queue_state"]
    assert state["now_playing"]["id"] == now_playing.id
    assert lazy_song.id not in [s["id"] for s in state["upcoming"]]
```

### Test: Revision incrementa cada cambio

```python
def test_revision_increments():
    db_session = SessionLocal()
    
    state1 = QueueSynchronizer.get_definitive_state(db_session)
    rev1 = state1["revision"]
    
    # Hacer cambio
    QueueSynchronizer.reorder_lazy_queue_safely(...)
    
    state2 = QueueSynchronizer.get_definitive_state(db_session)
    rev2 = state2["revision"]
    
    assert rev2 == rev1 + 1
```

---

## 📞 SOPORTE TÉCNICO

**Error:** `INTEGRITY ERROR: now_playing también está en upcoming`

**Causa:** Bug en lógica de reorder o corruption de datos  
**Solución:**
```bash
# 1. Log del error
tail -f app.log | grep "INTEGRITY ERROR"

# 2. Debuggear
python
>>> from queue_synchronizer import QueueSynchronizer
>>> from database import SessionLocal
>>> db = SessionLocal()
>>> issues = QueueSynchronizer.detect_desynchronization(db)
>>> print(issues)

# 3. Si persiste, ejecutar script de reparación
python repair_queue.py
```

---

## 📚 REFERENCIAS

- `queue_synchronizer.py` - Clase principal
- `websocket_manager.py` line XY - broadcast_queue_update mejorado
- `admin.py` - endpoints move-up, move-down, approve-next
- `SINCRONIZACION_COLA_FRONTEND.md` - Guía para frontend
