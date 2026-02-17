# HERRAMIENTAS DE DEBUG DISPONIBLES - RESUMEN RÁPIDO

## 🎯 TAREAS COMUNES Y CÓMO HACERLAS

### Tarea 1: "Una canción subida no aparece en la UI pero el player la reproduce"

**Paso 1:** Abre el panel debug en el navegador
```
Ctrl + Shift + Q (en admin dashboard)
```

**Paso 2:** Busca tu canción en "PRÓXIMAS 20 EN LA COLA"
- ✓ Si aparece → Es una canción ESCONDIDA (en BD pero no se ve en UI)
- ✗ Si no aparece → No está en BD

**Paso 3:** Abre comparación UI vs Realidad
```
Panel debug → Botón "🔎 COMPARAR"
```

**Paso 4:** Resultado
```json
"hidden_songs": [
  {"id": 108, "titulo": "Bohemian Rhapsody", "usuario": "Mesa_1"}
]
```
= La canción EXISTE en BD y VA A REPRODUCIR, pero la UI no la muestra

---

### Tarea 2: "Necesito ver EXACTAMENTE qué va a reproducir ahora mismo"

**Opción A - En el navegador:**
```
Ctrl + Shift + Q
Lee "🎵 QUÉ ESTÁ REPRODUCIENDO AHORA"
```

**Opción B - Desde terminal:**
```bash
curl http://localhost:8000/admin/queue/next-to-play | jq .
```

Respuesta:
```json
{
  "status": "something_is_playing",
  "now_playing": {
    "id": 105,
    "titulo": "Actual canción",
    "progress_percent": 45
  },
  "next_after_current": {
    "id": 106,
    "titulo": "Siguiente canción"
  }
}
```

**Opción C - Desde Python:**
```python
python queue_validator_cli.py
# Selecciona opción "2"
```

---

### Tarea 3: "Monitorear visualmente la cola cada 5 segundos"

**Opción A - Desde terminal (Python):**
```bash
python queue_validator_cli.py --auto --interval 5
```

Muestra:
- Qué está reproduciendo AHORA
- Próximas 10 canciones
- Integridad de la cola
- Se actualiza cada 5 segundos

**Opción B - Desde PowerShell (Windows):**
```powershell
$ProgressPreference = 'SilentlyContinue'
while ($true) {
    Clear-Host
    Write-Host "=== COLA QR KARAOKE - $(Get-Date -Format 'HH:mm:ss') ===" -ForegroundColor Cyan
    $response = Invoke-WebRequest -Uri "http://localhost:8000/admin/queue/debug" -UseBasicParsing
    $data = $response.Content | ConvertFrom-Json
    
    $data.what_will_play.next_20_in_queue | Select-Object -First 10 | ForEach-Object {
        Write-Host "$($_.id): $($_.titulo)" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 5
}
```

**Opción C - Panel visual en navegador:**
```
Ctrl + Shift + Q (se actualiza automáticamente cada 5 segundos)
```

---

### Tarea 4: "Encontrar TODAS las canciones escondidas"

**Desde terminal Python:**
```bash
python queue_validator_cli.py
# Selecciona opción "6"
```

Muestra lista de todas las canciones escondidas con sus details:
```
👻 CANCIONES ESCONDIDAS
11. Bohemian Rhapsody
    [ID: 108 | Usuario: Mesa_1]
12. Imagine
    [ID: 109 | Usuario: Mesa_2]
```

**Desde navegador:**
```
Ctrl + Shift + Q
Botón "🔎 COMPARAR UI vs REALIDAD"
```

---

### Tarea 5: "Ver estado COMPLETO de BD"

```bash
python queue_validator_cli.py
# Selecciona opción "4"
```

Muestra:
- Cuántas canciones reproduciendo
- Cuántas aprobadas
- Cuántas pendientes
- Cuántas rechazadas
- Detalle de cada una

---

### Tarea 6: "Validar integridad de la cola"

```bash
# Opción 1: Terminal
python queue_validator_cli.py
# Selecciona opción "5"

# Opción 2: API
curl http://localhost:8000/admin/queue/debug | jq '.integrity_checks'

# Respuesta:
{
  "now_playing_not_in_approved": true,        ✓ OK
  "no_duplicates": true,                      ✓ OK
  "all_approved_have_correct_status": true,   ✓ OK
  "issues_detected": false                    ✓ OK
}
```

Si alguno es `false` → PROBLEMA CRÍTICO

---

### Tarea 7: "Comparar lo que UI muestra vs lo que realmente reproducirá"

```bash
# Desde navegador (automático):
Ctrl + Shift + Q → Botón "🔎 COMPARAR"

# Desde Python (manual):
python -c "
import requests
import json

ui_state = {
    'now_playing': {'id': 105},
    'upcoming': [
        {'id': 106, 'titulo': 'Canción 2'},
        {'id': 107, 'titulo': 'Canción 3'}
    ]
}

r = requests.post(
    'http://localhost:8000/admin/queue/compare-ui-vs-reality',
    json=ui_state
)
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
"
```

Resultado:
```json
{
  "discrepancies": [
    {
      "type": "hidden_songs",
      "count": 3,
      "message": "3 canciones están en BD pero no en UI",
      "hidden_song_ids": [108, 109, 110]
    }
  ],
  "summary": {
    "is_synchronized": false,
    "critical_issues": 1
  }
}
```

---

## 🔧 ENDPOINTS DISPONIBLES

| Endpoint | Método | Propósito | Respuesta |
|----------|--------|----------|----------|
| `/admin/queue/next-to-play` | GET | Qué reproduce AHORA | status, now_playing, next |
| `/admin/queue/debug` | GET | Reporte completo | what_will_play, db_state, checks, issues |
| `/admin/queue/compare-ui-vs-reality` | POST | Encontrar discrepancias | discrepancies, summary |

---

## 🎮 PANEL VISUAL (Navegador)

**Atajo:** `Ctrl + Shift + Q` en admin dashboard

**Muestra:**
- ✓ Qué está reproduciendo AHORA
- ✓ Próximas 20 canciones en orden
- ✓ Validaciones de integridad
- ✓ Problemas detectados

**Botones:**
- 🔄 REFRESCAR - Actualiza el reporte
- 🔎 COMPARAR UI vs REALIDAD - Encuentra canciones escondidas
- 📋 VER JSON - Ve datos crudos

**Monitoreo automático:**
- Se actualiza cada 5 segundos
- F12 → Console: Ve logs de validación

---

## 🖥 VALIDADOR CLI (Terminal Python)

```bash
# Modo menú interactivo (por defecto)
python queue_validator_cli.py

# Modo monitoreo (se actualiza cada 5s)
python queue_validator_cli.py --auto --interval 5

# Ver reporte una solo vez
python queue_validator_cli.py --once
```

**Colores:**
- 🟢 Verde = OK
- 🟡 Amarillo = Warning
- 🔴 Rojo = Error
- 🔵 Azul = Info

**Menú interactivo:**
1. Ver reporte completo
2. Ver qué está reproduciendo
3. Ver próximas 20 canciones
4. Ver estado de BD
5. Ver validaciones
6. Ver canciones escondidas
7. Ver operaciones recientes
8. Ver JSON completo
9. Comparar UI vs Realidad (custom)

---

## 📋 FLUJO RECOMENDADO DE DEBUG

### Si subes una canción y NO aparece en la UI:

```
1. Panel debug (Ctrl+Shift+Q)
   ├─ ¿Aparece en "PRÓXIMAS 20"?
   │  ├─ SÍ → Es ESCONDIDA (problema UI)
   │  └─ NO → No está en BD (problema anterior)
   │
2. Si es ESCONDIDA → Botón "COMPARAR"
   ├─ Verás: "hidden_songs: [ID: 108]"
   └─ Significa: Está en BD, sonará, pero UI no la muestra
   
3. Toma screenshot del debug panel
4. Reporta: "Ver screenshot - canción escondida ID 108"
```

### Si UI y BD no se sincronizan:

```
1. Terminal: python queue_validator_cli.py --auto --interval 5
2. Realiza acción en UI (move-up, approve, etc)
3. Observa si monitoreo muestra cambios inmediatos
4. Si NO → hay lag en WebSocket
5. Si SÍ pero UI no actualiza → problema en JavaScript
```

### Si todo parece roto:

```
1. Ver integridad: python queue_validator_cli.py → opción 5
2. Si algún check es FALSE → contactar soporte
3. Si todos OK pero igual no funciona:
   - Reinicia backend: python main.py
   - Recarga frontend: Ctrl+R
   - Intenta de nuevo
```

---

## 🔴 PROBLEMAS COMUNES

| Síntoma | Diagnosis | Solución |
|---------|-----------|----------|
| Canción en UI, no suena | Hidden song (en BD) | Refrescar UI |
| Canción en BD, no en UI | Issue rendering | Refrescar página |
| now_playing diferente en UI vs debug | Desync crítica | Reiniciar backend |
| Cola dice vacía en debug | Sin canciones aprobadas | Cargar canciones |
| Duplicados en debug | Corrupción BD | Contactar soporte |
| Panel debug no abre | queue_validator.js no cargó | F12, refrescar, reiniciar |

---

## 📞 INFORMACIÓN PARA REPORTAR BUGS

Cuando reportes un problema, incluye:

```bash
# 1. Reporte de debug
python queue_validator_cli.py --once > debug_report.txt

# 2. Screenshot del panel visual
# Ctrl+Shift+Q → print screen

# 3. Logs del backend (última línea)
tail -n 50 main.log

# 4. Qué hiciste exactamente
# "Subí canción X, moví a posición Y, presioné botón Z"
```

**Enviar:**
- debug_report.txt
- screenshot (panel debug)
- descripción de pasos

---

## ✅ CHECKLIST: CONFIRMAR QUE TODO FUNCIONA

- [ ] Panel abre con Ctrl+Shift+Q
- [ ] Muestra "QUÉ ESTÁ REPRODUCIENDO AHORA" correctamente
- [ ] Botón "COMPARAR" funciona
- [ ] Validaciones muestran status OK
- [ ] CLI funciona: `python queue_validator_cli.py`
- [ ] Endpoint /admin/queue/debug funciona
- [ ] WebSocket se actualiza sin refrescar página

Si TODO está ✓ → Sistema de debug operacional

---

## 🎬 VIDEO TUTORIAL (Escrito)

### Scenario: "Subo canción y no la veo pero suena"

```
[ADMIN DASHBOARD]
├─ Presiono Ctrl+Shift+Q
├─ Se abre panel azul en esquina abajo-derecha
├─ Leo: "PRÓXIMAS 20 EN LA COLA"
├─ Busco mi canción (ej: Bohemian Rhapsody)
├─ ¡La encuentro en posición 15!
├─ Pero en la UI solo veo 10 canciones
├─ Presiono botón "🔎 COMPARAR"
├─ Muestra: "3 CANCIONES ESCONDIDAS"
└─ Causa identificada: UI limita a 10, BD tiene 20

[CONCLUSIÓN]
La canción VA a reproducir (está en BD)
Pero UI no la muestra (problema visual)
Solución: Actualizar número máximo de canciones mostradas en UI
```

---

## 🚀 PRÓXIMOS PASOS

Una vez que tengas estas herramientas funcionando:

1. ✓ Usa panel debug (Ctrl+Shift+Q) regularmente
2. ✓ Monitoreoautomático con CLI para acciones
3. ✓ Toma screenshots cuando algo mal
4. ✓ Reporta ID de canciones problemáticas
5. ✓ Verifica que WebSocket actualiza en tiempo real

Esto nos permitirá identificar EXACTAMENTE dónde falla la sincronización.
