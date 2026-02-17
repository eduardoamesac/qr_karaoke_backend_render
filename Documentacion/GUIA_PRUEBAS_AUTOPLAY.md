# Guía de Pruebas - Autoplay Automático

## Verificación Rápida ✅

### 1. Verifica que los cambios estén en place

```bash
# En PowerShell
cd c:\Users\MARCO_MESA\Documents\qr_karaoke_backend_render

# Busca que broadcast_play_song reciba duración
Select-String -Path "websocket_manager.py" -Pattern "duration_seconds"
# Debe encontrar: async def broadcast_play_song(self, youtube_id: str, duration_seconds: int = 0):

# Busca que se envíe duración en crud.py  
Select-String -Path "crud.py" -Pattern "broadcast_play_song" | Select-Object -First 5
# Debe encontrar calls con: broadcast_play_song(..., siguiente_cancion.duracion_seconds or 0)
```

### 2. Reinicia el servidor
```bash
# En terminal de PowerShell
cd c:\Users\MARCO_MESA\Documents\qr_karaoke_backend_render
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Abre el Player
- URL: http://localhost:8000/static/player.html
- Abre la Consola del Navegador: **F12** → **Console**

## Prueba Completa del Autoplay 🎵

### Paso 1: Agregar canción de prueba
1. Ve a http://localhost:8000/admin/
2. Busca una canción (ej: "Happy birthday karaoke")
3. Verifica que veas la DURACIÓN bajo cada resultado
4. Añade la canción con el botón "➕ Añadir"

**Esperado:**
- ✅ La canción aparece en la cola
- ✅ Se muestra la duración (ej: "⏱️ 3:30")

### Paso 2: Verifica logs en la Consola del Player
1. Con el player abierto (http://localhost:8000/static/player.html)
2. F12 → Console
3. **Busca estos logs en este orden:**

```
✅ Reproductor de YouTube creado con API para video: [VIDEO_ID]
✅ Reproductor listo, iniciando reproducción
▶️ Video reproduciéndose
⏱️ Temporizador de fallback establecido para [NUMERO] segundos

[...espera a que termine el video...]

🎬 Video terminado, iniciando transición de 5 segundos...
```

**Si ves esto = ✅ AUTOPLAY FUNCIONANDO**

### Paso 3: Verifica el Temporizador de Fallback
1. En la cola, agrega otra canción
2. Espera a que TERMINE la primera
3. Mira la pantalla - debería:
   - Mostrar "Próxima canción: [TITULO]"
   - Esperar 5 segundos
   - Comenzar A REPRODUCIR AUTOMÁTICAMENTE sin que hagas nada

**Si eso sucede = ✅ TODO PERFECTO**

## Debugging - Si NO Funciona ⚠️

### Síntoma: "No hay temporizador de fallback"
**Causa:** La duración no se está enviando
**Solución:**
1. En admin, busca la canción nuevamente
2. ¿Ves la duración bajo el resultado? Si NO:
   ```bash
   # Revisa los logs del servidor
   # Busca errores al obtener metadata de YouTube
   ```
3. Si SÍ ves duración en admin, pero no en player:
   - F12 → Network
   - Filtra por "siguiente"
   - Haz que termine la canción
   - Revisa la Respuesta JSON en Network
   - ¿Contiene "duracion_seconds"? Si NO, problema en backend

### Síntoma: "El video nunca termina"
**Causa:** El evento ENDED no se dispara
**Solución:**
- Eso está bien, el FALLBACK TIMER se activa automáticamente
- Verás: `⚠️ FALLBACK TIMER ACTIVADO`
- El video avanza de todas formas (es el backup)

### Síntoma: "Ha habido un error conectándose a la API"
**Causa:** Problema de CORS o servidor caído
**Solución:**
```bash
# Revisa que el server esté corriendo
curl http://localhost:8000/api/v1/canciones/cola/extended

# Si da error, reinicia imaginating
uvicorn main:app --reload
```

### Síntoma: "WebSocket desconectado"
**Causa:** Conexión perdida
**Solución:**
- Recarga la página (F5)
- El WebSocket debe reconectar automáticamente en 3 segundos
- Verás: `WebSocket conectado exitosamente`

## Verificación de Componentes 🔧

### A. Verifica que la Duración se Guarda
```python
# Desde Python REPL o script
from database import SessionLocal
from models import Cancion

db = SessionLocal()
canciones = db.query(Cancion).all()
for c in canciones[:3]:
    print(f"{c.titulo}: {c.duracion_seconds} segundos")

# Esperado: Todas deben tener duracion_seconds > 0
```

### B. Verifica que WebSocket envía duración
```javascript
// En la Consola del Player (F12console)
// Espera a que termine una canción
// Busca en los logs: "Recibida orden de reproducir:"
// Debería decir: 
// "Recibida orden de reproducir: [VIDEO_ID]"
// "duration: X segundos"
```

### C. Verifica el Endpoint de Búsqueda
```bash
# Abre en navegador
http://localhost:8000/api/v1/youtube/public-search?q=happy%20birthday%20karaoke

# Esperado: Array de canciones, cada una con:
{
  "video_id": "...",
  "title": "...",
  "thumbnail": "...",
  "duration_seconds": 215    // <-- IMPORTANTE
}
```

## Tests Manuales 📝

| Test | Pasos | Esperado |
|------|-------|----------|
| **Autoplay Básico** | 1. Agrega canción<br>2. Espera a que termine<br>3. Sin hacer nada | Siguiente está reproduciendo |
| **Múltiples Canciones** | 1. Agrega 3 canciones<br>2. Inicia | Todas se reproducen automáticamente en orden |
| **Cola Vacía** | 1. Termina última canción | Muestra "Esperando siguiente..." y carrusel |
| **Admin Manual + Auto** | 1. Player reproduciendo<br>2. Admin presiona "Play"<br>3. Espera a que termine | Sigue al siguiente automáticamente |
| **WebSocket Interrumpido** | 1. Abre DevTools<br>2. Network Throttling: Offline<br>3. Cuando vuelve online | Se recupera y usa fallback HTTP |

## Logs Importantes para Copiar-Pegar 📋

Si reportas un problema, cople estos logs de la consola (F12):

```javascript
// Ej: Problema con duración
// En Console, paste:
console.log('Video ID:', currentVideoId);
console.log('Duración enviada:', currentVideoDuration);
console.log('Timer establecido:', autoplayTimer !== null);
```

## Performance Expectations ⚡

| Métrica | Esperado |
|---------|----------|
| Tiempo para transición | ~5 segundos (fijo) |
| Tiempo para HTTP error recovery | ~2 segundos |
| Tiempo para siguiente canción aparezca | <1 segundo (WebSocket) |
| WebSocket reconnect | ~3 segundos |
| Fallback timer accuracy | ±1 segundo |

---

## Si Todo Está Bien ✨

Deberías ver este flujo:
```
[Admin agrega canción]
        ↓
[Player obtiene cola via WebSocket]
        ↓
[Video comienza a reproducir]
        ↓ 
[Timer de fallback establecido]
        ↓
[5 minutos después... video termina]
        ↓
[ENDED event O fallback timer dispara]
        ↓
[Pantalla de transición 5 segundos]
        ↓
[POST /api/v1/canciones/siguiente]
        ↓
[Siguiente canción comienza AUTOMÁTICAMENTE]
```

**¡SIN HACER NADA MANUALMENTE! 🎉**
