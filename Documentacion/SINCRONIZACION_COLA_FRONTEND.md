# 🎯 GUÍA DE SINCRONIZACIÓN: Backend → Frontend (Cola Determinística)

## 📋 Resumen Ejecutivo

**Problema resuelto:** Desincronización de cola lazy cuando el admin cambia canciones en reproducción.

**Solución:** Modelo determinístico donde el backend SIEMPRE es fuente de verdad única.

---

## 🏗 Arquitectura de Sincronización

```
┌─────────────────┐
│   Admin UI      │ (Dashboard karaoke)
└────────┬────────┘
         │
         ├─ POST /admin/canciones/lazy/{id}/move-up (CAMBIO DE ESTADO)
         ├─ POST /admin/canciones/lazy/{id}/move-down
         ├─ POST /admin/canciones/lazy/approve-next
         ├─ POST /admin/canciones/{id}/revert-approve
         │
         └─ GET /admin/queue/state (FUENTE DE VERDAD) ←─────────┐
                                                                  │
         ┌──────────────────────────────────────────────────────┘
         │
    ╔════╩═════════════════════════════════════════════════════════╗
    ║                   BACKEND (FastAPI)                          ║
    ║  ┌────────────────────────────────────────────────────────┐  ║
    ║  │  QueueSynchronizer                                     │  ║
    ║  │  • get_definitive_state()  ← AUTORIDAD ÚNICA          │  ║
    ║  │  • increment_revision()    ← Invalida cache            │  ║
    ║  │  • validate_song_still_valid()                         │  ║
    ║  │  • reorder_lazy_queue_safely()                         │  ║
    ║  │  • detect_desynchronization()                          │  ║
    ║  └────────────────────────────────────────────────────────┘  ║
    ║                                                                ║
    ║  ┌────────────────────────────────────────────────────────┐  ║
    ║  │  WebSocket (broadcast_queue_update)                   │  ║
    ║  │  → Envía estado COMPLETO                              │  ║
    ║  │  → Incluye numero de revisión                         │  ║
    ║  │  → Cada CAMBIO invalidar cache                        │  ║
    ║  └────────────────────────────────────────────────────────┘  ║
    ║                                                                ║
    ║  ┌────────────────────────────────────────────────────────┐  ║
    ║  │  Database (SQLite/PostgreSQL)                         │  ║
    ║  │  • Cancion.estado = {pendiente|pendiente_lazy|...}   │  ║
    ║  │  • Cancion.orden_manual = {1,2,3...} (para congelar) │  ║
    ║  └────────────────────────────────────────────────────────┘  ║
    ╚════╦═════════════════════════════════════════════════════════╝
         │
         └─ WebSocket connection (SSE o WS)
            {
              "type": "queue_update",
              "payload": {
                "timestamp": "2024-02-13T15:30:45.123456",
                "revision": 42,
                "now_playing": { id, titulo, usuario... } | null,
                "upcoming": [ {cancion}, ... ],     ← NUNCA now_playing aquí
                "lazy_queue": [ {cancion}, ... ],   ← NUNCA reproduciendo
                "pending": [ {cancion}, ... ],
                "_integrity_checks": {...}
              }
            }
```

---

## 🔐 Contrato de Estado (INMUTABLE)

Cada respuesta de `/admin/queue/state` o WebSocket `queue_update` tiene:

```json
{
  "timestamp": "2024-02-13T15:30:45.123456Z",
  "revision": 42,
  
  "now_playing": {
    "id": 105,
    "titulo": "Bohemian Rhapsody",
    "usuario": { "nick": "Mesa_1", "mesa_id": 1 },
    "duracion_seconds": 365,
    "started_at": "2024-02-13T15:25:00Z",
    "estado": "reproduciendo"
  },
  
  "upcoming": [
    { "id": 106, "titulo": "Canción 2", "usuario": {...}, "estado": "aprobado" },
    { "id": 107, "titulo": "Canción 3", "usuario": {...}, "estado": "aprobado" }
  ],
  
  "lazy_queue": [
    { "id": 108, "titulo": "Canción Lazy 1", "usuario": {...}, "estado": "pendiente_lazy" },
    { "id": 109, "titulo": "Canción Lazy 2", "usuario": {...}, "estado": "pendiente_lazy" }
  ],
  
  "pending": [
    { "id": 110, "titulo": "Canción Pendiente", "usuario": {...}, "estado": "pendiente" }
  ],
  
  "_integrity_checks": {
    "now_playing_not_in_upcoming": true,
    "all_upcoming_states_approved": true,
    "all_lazy_states_pending_lazy": true
  }
}
```

### ⚠️ GARANTÍAS DEL CONTRATO:
1. ✅ `now_playing` NUNCA aparecerá en `upcoming`
2. ✅ `now_playing` NUNCA tendrá `estado != "reproduciendo"`
3. ✅ Todas las canciones en `upcoming` tienen `estado == "aprobado"`
4. ✅ Todas las canciones en `lazy_queue` tienen `estado == "pendiente_lazy"`
5. ✅ El `revision` incrementa con CADA cambio
6. ✅ `timestamp` representa el momento del estado sincronizado

---

## 📡 CÓMO USAR EN FRONTEND

### 1️⃣ INICIALIZACIÓN

```javascript
// Al cargar el dashboard admin
let queueState = null;
let lastRevision = -1;

async function initQueueSync() {
  try {
    const response = await fetch('/admin/queue/state');
    queueState = await response.json();
    lastRevision = queueState.revision;
    
    console.log('🟢 Estado inicial sincronizado');
    renderQueueUI(queueState);
    
    // Conectar WebSocket DESPUÉS de obtener estado inicial
    connectQueueWebSocket();
    
  } catch (error) {
    console.error('❌ Error sincronizando estado inicial:', error);
    setTimeout(initQueueSync, 2000); // Reintentar
  }
}

function connectQueueWebSocket() {
  const ws = new WebSocket('ws://localhost:8000/ws');
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'queue_update') {
      handleQueueUpdate(msg.payload);
    }
  };
}
```

### 2️⃣ PROCESAR ACTUALIZACIÓN DESDE WEBSOCKET

```javascript
function handleQueueUpdate(newState) {
  // ✅ SIEMPRE confiar en el estado del servidor
  // ✅ NUNCA filtrar o reordenar localmente
  
  // Detectar cambios
  const revisionChanged = newState.revision !== lastRevision;
  
  if (!revisionChanged) {
    console.log('↔️ Revisión sin cambios, usando cache');
    return;
  }
  
  console.log(`🔄 Revisión cambió: ${lastRevision} → ${newState.revision}`);
  
  // Validar integridad
  if (!newState._integrity_checks.now_playing_not_in_upcoming) {
    console.error('❌ ERROR CRÍTICO: now_playing está en upcoming!');
    // Forzar re-sincronización
    location.reload();
    return;
  }
  
  // REEMPLAZAR estado local COMPLETAMENTE
  queueState = newState;
  lastRevision = newState.revision;
  
  // RE-RENDERIZAR TODO
  renderQueueUI(queueState);
}
```

### 3️⃣ RENDERIZAR LA COLA

```javascript
function renderQueueUI(state) {
  // SECCIÓN 1: Now Playing
  const nowPlayingDiv = document.getElementById('now-playing');
  if (state.now_playing) {
    nowPlayingDiv.innerHTML = `
      <div class="now-playing-card">
        <h3>🎤 Reproduciendo</h3>
        <p><strong>${state.now_playing.titulo}</strong></p>
        <p>Usuario: ${state.now_playing.usuario.nick}</p>
        <p class="debug-info">ID: ${state.now_playing.id} | Revisión: ${state.revision}</p>
      </div>
    `;
  } else {
    nowPlayingDiv.innerHTML = '<p>Nada reproduciéndose</p>';
  }
  
  // SECCIÓN 2: Cola Aprobada (Upcoming)
  const upcomingList = document.getElementById('upcoming-queue');
  upcomingList.innerHTML = state.upcoming.map((song, idx) => `
    <div class="queue-item upcoming">
      <span>#${idx + 1}</span>
      <span>${song.titulo}</span>
      <span>${song.usuario.nick}</span>
      <button onclick="moveSongInUpcoming(${song.id}, 'down')">↓</button>
    </div>
  `).join('');
  
  // SECCIÓN 3: Cola Lazy (Pendiente_lazy)
  const lazyList = document.getElementById('lazy-queue');
  lazyList.innerHTML = state.lazy_queue.map((song, idx) => `
    <div class="queue-item lazy">
      <span>#${idx + 1}</span>
      <span>${song.titulo}</span>
      <span>${song.usuario.nick}</span>
      <button onclick="moveLazySongUp(${song.id})">↑</button>
      <button onclick="moveLazySongDown(${song.id})">↓</button>
      <button onclick="approveLazySong(${song.id})">✓ Aprobar</button>
    </div>
  `).join('');
  
  console.log(`✅ UI actualizado | Rev: ${state.revision}`);
}
```

### 4️⃣ ENVIAR CAMBIOS AL BACKEND

```javascript
async function moveLazySongUp(songId) {
  try {
    const response = await fetch(
      `/admin/canciones/lazy/${songId}/move-up`,
      { method: 'POST' }
    );
    
    if (!response.ok) throw new Error(response.statusText);
    
    const result = await response.json();
    
    // ⚠️ NO confies en result.queue_state del response
    // ESPERA a que el WebSocket te envíe la actualización REAL
    console.log('✓ Comando enviado, esperando confirmación por WS...');
    
    // El WebSocket enviará queue_update con la nueva revelación
    
  } catch (error) {
    console.error('❌ Error moviendo canción:', error);
  }
}

async function approveLazySong(songId) {
  try {
    const response = await fetch(
      `/admin/canciones/lazy/approve-next`,
      { method: 'POST' }
    );
    
    const result = await response.json();
    console.log('✓ Canción aprobada:', result.cancion_aprobada.titulo);
    
  } catch (error) {
    console.error('❌ Error aprobando:', error);
  }
}
```

---

## 🎯 REGLAS DE ORO PARA EL FRONTEND

| ❌ INCORRECTO | ✅ CORRECTO |
|---|---|
| Asumir que el orden se mantiene | Siempre confiar en `revision` |
| Filtrar canción localmente | Esperar broadcast del backend |
| Renderizar datos cacheados | Forzar re-render cuando revision cambia |
| Reordenar lista sin confirmación | Reordenar SOLO en respuesta del servidor |
| Mostrar canción que desapareció | Validar que ID siga en estado actual |

---

## 🔍 DEBUGGING

### Ver logs de desincronización

```javascript
function checkQueueIntegrity(state) {
  const checks = state._integrity_checks;
  
  console.table({
    'now_playing_not_in_upcoming': checks.now_playing_not_in_upcoming,
    'all_upcoming_approved': checks.all_upcoming_states_approved,
    'all_lazy_pending_lazy': checks.all_lazy_states_pending_lazy
  });
  
  if (Object.values(checks).some(v => !v)) {
    console.error('⚠️ INTEGRITY CHECK FAILED!');
    return false;
  }
  return true;
}

// Llamar periódicamente
setInterval(() => {
  fetch('/admin/queue/state')
    .then(r => r.json())
    .then(state => {
      if (!checkQueueIntegrity(state)) {
        console.error('SYNC PROBLEM DETECTED:', state);
      }
    });
}, 30000); // Cada 30 segundos
```

### Forzar re-sincronización completa

```javascript
async function forceSyncQueue() {
  console.warn('🔄 Forzando re-sincronización completa...');
  lastRevision = -1;
  const response = await fetch('/admin/queue/state');
  const newState = await response.json();
  handleQueueUpdate(newState);
}
```

---

## 📊 FLUJO COMPLETO DE UN CAMBIO

### Escenario: Admin mueve canción lazy hacia arriba

```
T1: Admin click "↑" en canción ID 105
    └─→ Frontend: POST /admin/canciones/lazy/105/move-up

T2: Backend recibe cambio
    ├─ QueueSynchronizer.reorder_lazy_queue_safely()
    ├─ Valida que ID 105 esté en "pendiente_lazy"
    ├─ Valida que NO esté "reproduciendo"
    ├─ Reordena EN BD con orden_manual
    ├─ Incrementa revisión: 41 → 42
    └─ Retorna response con queue_state

T3: Frontend recibe response 200
    └─ Log: "✓ Comando enviado, esperando confirmación..."
    └─ ⚠️ NO RENDERIZA AÚN (podría cambiar de nuevo)

T4: Backend hace broadcast_queue_update()
    ├─ QueueSynchronizer.get_definitive_state()
    ├─ Fuerza refresh_all() desde BD
    ├─ Valida integridad
    ├─ Envía WebSocket con revision=42
    └─ Incluye cola ACTUALIZADA

T5: Frontend recibe WebSocket con revision cambió (41→42)
    ├─ handleQueueUpdate() detects cambio
    ├─ Valida integridad ✓
    ├─ REEMPLAZA queueState completo
    ├─ RENDERIZA UI nuevamente
    └─ Muestra canción en nueva posición ✓

RESULTADO:
Frontend NUNCA asumió orden ✓
Backend fue fuente de verdad única ✓
Cambios fueron atómicos ✓
```

---

## 🚀 MIGRACIÓN DESDE CÓDIGO VIEJO

Si ya tienes código que cachea la cola:

```javascript
// ❌ VIEJO (inseguro)
let cachedQueue = state.upcoming;
function renderOldWay() {
  // Renderizar desde cache
  // PROBLEMA: queue puede cambiar en BD simultáneamente
}

// ✅ NUEVO (seguro)
let queueState = null;
function renderNewWay() {
  // Siempre renderizar desde queueState actual
  // SEGURO: Espera a que backend confirme cambios
}
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

- [ ] Frontend hace `GET /admin/queue/state` al inicializar
- [ ] Frontend conecta WebSocket y escucha `queue_update`
- [ ] Frontend valida `revision` antes de renderizar
- [ ] Frontend valida `_integrity_checks`
- [ ] Frontend REEMPLAZA estado completo (no merge parcial)
- [ ] Frontend renderiza desde `queueState` actual
- [ ] Frontend hace POST al botón pero no renderiza hasta WS
- [ ] Frontend muestra indicador "sincronizando..." mientras espera
- [ ] Frontend tiene timeout de 5s para detectar desconexión
- [ ] Frontend loguea todos los cambios de revisión

---

## 🆘 CASOS PROBLEMÁTICOS RESUELTOS

### Caso 1: Admin mueve canción mientras se reproduce
**Viejo problema:** Canción desaparece de cola pero sigue sonando  
**Solución:** QueueSynchronizer valida que canción NO esté "reproduciendo" antes de reordenar

### Caso 2: Dos admins cambian cola simultáneamente
**Viejo problema:** Estado inconsistente, conflictos  
**Solución:** Cada cambio incrementa revision, frontend descarta comandos viejos

### Caso 3: Frontend cacheó cola, canción fue aprobada por otro admin
**Viejo problema:** Usuario ve canción vieja  
**Solución:** WebSocket envía nueva revision, frontend descarta cache

---

## 📞 SOPORTE

Si ves cualquiera de estos:
- ❌ now_playing aparece en upcoming
- ❌ Canción desaparece pero sigue sonando
- ❌ Revision no incrementa con cambios
- ❌ _integrity_checks falla

**ACCIÓN INMEDIATA:**
```bash
# Desde backend: force full resync
curl http://localhost:8000/admin/queue/state | jq '._integrity_checks'

# Si falla: Error grave, reiniciar backend
python main.py --restart
```
