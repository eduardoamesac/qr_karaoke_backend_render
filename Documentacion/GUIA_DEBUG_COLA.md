# 🔍 GUÍA DE DEBUG: Encontrar canciones escondidas y validar cola

## 📋 PROBLEMA A RESOLVER

- ✅ Subes una canción para que sea la siguiente
- ❌ Desaparece de la UI
- ❌ El player no la reproduce después
- ❌ Hay canciones "escondidas" en BD que no muestra la UI

**Esto ocurre porque:**
1. La UI no muestra todas las canciones que hay en BD
2. Hay desincronización visual entre lo que ves vs lo que reproducirá el player

---

## 🎯 HERRAMIENTAS DE DEBUG DISPONIBLES

### 1. PANEL DEBUG VISUAL (Frontend)

**Atajo de teclado:**
```
Ctrl + Shift + Q
```

Abre un panel en la esquina inferior derecha que muestra:
- ✓ Qué está reproduciendo AHORA
- ✓ Qué va a reproducir DESPUÉS (próximas 20)
- ✓ Integridad de la cola
- ✓ Problemas detectados

**Botones:**
- 🔄 REFRESCAR - Actualiza el reporte
- 🔎 COMPARAR UI vs REALIDAD - Encuentra canciones escondidas
- 📋 VER JSON - Ve los datos crudos

---

### 2. ENDPOINT: GET /admin/queue/debug

Muestra un reporte completo JSON con:
- `what_will_play` - Las próximas 20 canciones REALES que sonarán
- `database_state` - Todas las canciones en BD
- `integrity_checks` - Validaciones
- `issues` - Problemas detectados
- `recent_queue_operations` - Historial de cambios

**Llamar desde terminal:**
```bash
curl http://localhost:8000/admin/queue/debug | jq .
```

**Secciones importantes:**
```json
{
  "what_will_play": {
    "next_20_in_queue": [
      {
        "position": 1,
        "id": 106,
        "titulo": "Bohemian Rhapsody",
        "usuario": "Mesa_1"
      },
      ...
    ]
  },
  "database_state": {
    "aprobado_count": 15,
    "aprobado_list": [...]  // TODAS las canciones aprobadas
  },
  "integrity_checks": {
    "now_playing_not_in_approved": true,
    "no_duplicates": true,
    "all_approved_have_correct_status": true,
    "issues_detected": false
  }
}
```

---

### 3. ENDPOINT: GET /admin/queue/next-to-play

Muestra claramente cuál es LA PRÓXIMA canción que va a sonar.

**Respuesta cuando algo está reproduciéndose:**
```json
{
  "status": "something_is_playing",
  "now_playing": {
    "id": 105,
    "titulo": "Actual reproduciendo",
    "duration": 180,
    "progress_percent": 45
  },
  "next_after_current": {
    "id": 106,
    "titulo": "Siguiente canción",
    "usuario": "Mesa_1"
  }
}
```

**Respuesta cuando cola estàvacía:**
```json
{
  "status": "empty",
  "message": "NO HAY CANCIONES EN LA COLA"
}
```

---

### 4. ENDPOINT: POST /admin/queue/compare-ui-vs-reality

**Qué hace:**
Compara lo que la UI muestra vs la realidad en BD. Detecta:
- 🔴 Canciones ESCONDIDAS (en BD pero no en UI)
- 👻 Canciones FANTASMA (en UI pero no en BD)
- 🔄 Orden DIFERENTE
- ⚠ now_playing INCORRECTO

**Llamar desde programa:**
```python
import requests

ui_state = {
  "now_playing": {"id": 105},
  "upcoming": [
    {"id": 106, "titulo": "Canción 2"},
    {"id": 107, "titulo": "Canción 3"}
  ]
}

response = requests.post(
  "http://localhost:8000/admin/queue/compare-ui-vs-reality",
  json=ui_state
)
comparison = response.json()
```

**Respuesta con problemas:**
```json
{
  "discrepancies": [
    {
      "type": "hidden_songs",
      "severity": "CRITICAL",
      "count": 3,
      "hidden_song_ids": [108, 109, 110],
      "hidden_songs_details": [
        {
          "id": 108,
          "titulo": "Hidden Song 1",
          "usuario": "Mesa_2"
        }
      ],
      "message": "3 CANCIONES ESTÁN EN BD PERO NO MUESTRA LA UI"
    }
  ],
  "summary": {
    "is_synchronized": false,
    "issues_found": 1,
    "critical_issues": 1,
    "warnings": 0
  }
}
```

---

## 🔧 FLUJO DE DEBUG PASO A PASO

### Situación: "Subí una canción pero no aparece en la cola"

#### PASO 1: Abre el panel de debug
```
Presiona: Ctrl + Shift + Q
```

#### PASO 2: Obtén el reporte
El panel muestra automáticamente:
```
🎵 QUÉ VA A REPRODUCIR:
▶ Reproduciendo: Canción Actual
↓ Siguiente: Canción 1
   Canción 2
   Canción 3
   ...
```

#### PASO 3: Busca tu canción en "PRÓXIMAS 20 EN LA COLA"
Si **TU CANCIÓN APARECE** en esa lista:
- ✅ Está en BD
- ✅ Se Va a reproducir
- ❌ Problema: UI no la muestra (bug visual)

Si **TU CANCIÓN NO APARECE**:
- ❌ NO está en BD
- ❌ Posible: fue rechazada, no aprobada, o eliminada
- Revisa que esté en estado "aprobado"

#### PASO 4: Compara UI vs Realidad
Botón en el panel: "🔎 COMPARAR UI vs REALIDAD"

Muestra:
```
⚠ PROBLEMAS CRÍTICOS:
❌ [hidden_songs] 2 CANCIONES ESTÁN EN BD PERO NO MUESTRA LA UI
   - ID 108: Bohemian Rhapsody (Mesa_1)
   - ID 109: Imagine (Mesa_2)
```

**Esto significa:**
- Las canciones EXISTEN en BD
- El PLAYER las VA a reproducir
- Pero la UI NO las está mostrando (bug en renderizado)

---

## 💡 CASOS COMUNES Y SOLUCIONES

### Caso 1: Canción aparece en debug pero NO en UI

**Síntoma:**
- Panel debug muestra la canción en top 20
- UI no la muestra

**Causa:**
- Límite de UI en cantidad mostrada
- CSS oculta elementos
- JavaScript no renderiza correctamente

**Solución:**
```javascript
// En console del navegador:
document.querySelectorAll('[data-cancion-id]').length
// Muestra cuántas canciones renderiza la UI

// Si show < 10 pero debug show > 10 → problema de UI rendering
```

### Caso 2: Canción en UI pero NO en debug

**Síntoma:**
- UI muestra canción
- Debug says: "CANCIÓN FANTASMA - EN UI PERO NO EN BD"

**Causa:**
- Canción fue eliminada después de renderizar
- UI no actualizó

**Solución:**
- Refresca la página
- O espera a que WebSocket envíe actualización

### Caso 3: now_playing diferente entre UI y debug

**Síntoma:**
- UI muestra: "Reproduciendo: Canción A"
- Debug muestra: "Reproduciendo: Canción B"

**Causa:**
- DESINCRONIZACIÓN CRÍTICA
- El player está reproduciendo algo diferente a lo que ve el admin

**Solución:**
```
1. Presiona REFRESCAR en panel debug
2. Si persiste → hay bug en synchronizer
3. Contacta a desarrollador con:
   - Salida de /admin/queue/debug
   - Salida de /admin/queue/state
```

---

## 🎬 FLUJO COMPLETO: VERIFICAR QUE TODO FUNCIONA

### 1. Verifica qué va a reproducir AHORA

```
GET /admin/queue/next-to-play
```

Si muestra ahora playing correctamente → ✓

### 2. Sube una canción nueva

Desde cliente usuario, pide una canción.

### 3. Verifica que aparezca en la cola

```
Ctrl + Shift + Q
Ver en "PRÓXIMAS 20 EN LA COLA"
```

### 4. Compara UI vs Realidad

Click en "🔎 COMPARAR UI vs REALIDAD"

Debe mostrar:
```
✓ SINCRONIZADO
✓ UI MUESTRA: 10 canciones
✓ REALIDAD EN BD: 10 canciones
✓ Sin discrepancias
```

### 5. Toma una acción (move-up, approve, etc)

Desde admin, reordena la canción.

### 6. Verifica que actualizó

```
Ctrl + Shift + Q
🔄 REFRESCAR
```

El panel debe actualizar y mostrar nuevo orden.

---

## 🚨 SEÑALES DE ALERTA

Si ves estos mensajes → Hay PROBLEMAS:

```
❌ COLA VACÍA - NADA VA A REPRODUCIR
❌ now_playing está TAMBIÉN en approved queue
❌ Sin duplicados (FALSO) → hay IDs duplicados
❌ CANCIONES ESCONDIDAS detectadas
⚠ Desorden en cola
⚠ Integridad comprometida
```

**ACCIÓN INMEDIATA:**
```bash
1. Copia el JSON del reporte (📋 VER JSON)
2. Toma screenshot
3. Reinicia el backend:
   python main.py
4. Prueba de nuevo
```

---

## 📊 TABLA DE DIAGNÓSTICO

| Problema | Debug muestra | UI muestra | Solución |
|---|---|---|---|
| Canción escondida | ✓ En BD | ✗ No aparece | Refrescar página |
| Canción fantasma | ✗ No en BD | ✓ Aparece | Esperar WS update |
| now_playing diferente | X | Y | Refresar ambos |
| Orden diferente | 1,2,3,4 | 1,3,2,4 | BUG CRÍTICO |
| Cola vacía | ✗ | ✗ | Cargar canciones |
| Duplicados | 2x ID 105 | Confuso | Contactar soporte |

---

## 💻 EJEMPLOS: LLAMAR DESDE PYTHON/CURL

### Ver qué va a reproducir:
```bash
curl -s http://localhost:8000/admin/queue/next-to-play | jq '.next_to_play.titulo'
```

### Ver integridad:
```bash
curl -s http://localhost:8000/admin/queue/debug | jq '.integrity_checks'
```

### Ver issues:
```bash
curl -s http://localhost:8000/admin/queue/debug | jq '.issues'
```

### Encontrar canciones escondidas:
```bash
curl -s http://localhost:8000/admin/queue/debug | jq '.database_state.aprobado_list | length'
# Compara con cantidad que muestra UI
```

---

## 🔄 MONITOREO AUTOMÁTICO

El panel de debug **monitorea automáticamente** cada 5 segundos:
- ✓ now_playing en approved (error crítico)
- ✓ Duplicados
- ✓ Canciones escondidas

Ve a la console del navegador (F12) → Console:
```javascript
// Debería Ver:
// "🟢 Queue Validator Monitoring Started"
// "⚠ Issues detectadas: 0" (o el número)
```

---

## 📞 TROUBLESHOOTING

### P: El panel no abre con Ctrl+Shift+Q
**R:** 
- Verifica que queue_validator.js esté cargado (F12 → Sources)
- Recarga la página (Ctrl+R)
- Prueba botón azul "🔍 DEBUG COLA" en esquina inferior derecha

### P: El endpoint /admin/queue/debug retorna 500
**R:**
- Revisa logs del backend
- Probablemente hay un error en queue_debugger.py
- Reinicia backend: `python main.py`

### P: No veo mis canciones en "PRÓXIMAS 20"
**R:**
- ¿Estado es "aprobado"? (no pendiente o pendiente_lazy)
- ¿Son más de 20? Scroll en el panel
- Llama al endpoint compare-ui-vs-reality para encontrarlas

### P: Dice "SINCRONIZADO" pero veo desorden
**R:**
- Refresca el panel (🔄 REFRESCAR)
- La canción puede estar movindose (transición incompleta)
- Espera a que WS la actualice

---

## ✅ CONCLUSIÓN

Con estas herramientas puedes:
1. ✓ Ver EXACTAMENTE qué va a reproducir
2. ✓ Encontrar canciones escondidas
3. ✓ Detectar desincronizaciones
4. ✓ Validar integridad de la cola
5. ✓ Debuggear problemas visualmente

**Recordar:** 
- El backend ES la verdad
- Si está en BD pero no en UI → problema visual
- Si no está en BD → nunca sonará
