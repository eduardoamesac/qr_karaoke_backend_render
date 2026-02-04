# 🚀 Guía de Migración e Instalación - Sistema de Créditos

## 📋 Pre-Requisitos

- FastAPI en ejecución
- SQLAlchemy ORM configurado
- Base de datos actualizada

---

## 🔄 Pasos de Migración

### 1️⃣ Hacer Backup (RECOMENDADO)

```bash
# Backup de la BD
cp tu_base_datos.db tu_base_datos.db.backup.2026-02-04
```

### 2️⃣ Aplicar Cambios de Código

✅ **Ya están implementados:**
- `models.py` - Nueva tabla `SongCredits` y campos en `Usuario`
- `schemas.py` - Schemas actualizados
- `crud.py` - Funciones de créditos
- `canciones.py` - Validación de créditos
- `consumos.py` - Asignación automática de créditos
- `usuarios.py` - Endpoints de consulta
- `admin.py` - Endpoints de administración
- `main.py` - Inicia background task
- `song_credits_background.py` - Archivo nuevo

### 3️⃣ Iniciar la Aplicación

```bash
# La BD se creará/actualizará automáticamente
python -m uvicorn main:app --reload
```

**Resultado esperado:**
```
✓ Tabla 'song_credits' creada
✓ Campos agregados a 'usuarios'
✓ Background task iniciada
✓ Endpoints disponibles
```

### 4️⃣ Verificar Instalación

```bash
# Test 1: Crear usuario de prueba
curl -X POST http://localhost:8000/api/v1/mesas/1/usuarios \
  -H "Content-Type: application/json" \
  -d '{"nick": "TestUser"}'

# Deberías ver: song_credits: 1

# Test 2: Ver créditos
curl http://localhost:8000/api/v1/usuarios/1/available-credits

# Deberías ver: "credits_available": 1
```

---

## 🧪 Plan de Testing

### Test 1: Crédito Inicial

```bash
# Usuario entra, debe tener 1 crédito
POST /api/v1/mesas/1/usuarios
Body: {"nick": "Marco"}

GET /api/v1/usuarios/1/available-credits
Expected: {"credits_available": 1, "can_add_song": true}
```

### Test 2: Agregar Canción sin Comprar

```bash
# Debería funcionar con el crédito inicial
POST /api/v1/canciones/1
Body: {
  "titulo": "Bohemian Rhapsody",
  "youtube_id": "fJ9rUzIMt7o",
  "duracion_seconds": 354
}
Expected: ✅ 200 OK

# Intento 2 debería fallar
POST /api/v1/canciones/1
Expected: ❌ 402 Payment Required
Detail: "No tienes créditos disponibles"
```

### Test 3: Comprar y Obtener Créditos

```bash
# Producto: Cerveza $5,000
POST /api/v1/consumos/pedir/1
Body: {
  "producto_id": 1,  // Cerveza
  "cantidad": 1
}
Expected: ✅ 200 OK

# Verificar créditos
GET /api/v1/usuarios/1/available-credits
Expected: {"credits_available": 5000, "can_add_song": true}
```

### Test 4: Decaimiento de Créditos

```bash
# Inmediatamente después de la compra
GET /api/v1/usuarios/1/song-credits
Expected: "available_credits": 5000

# Esperar 1 minuto

# Después de 1 minuto
GET /api/v1/usuarios/1/song-credits
Expected: "available_credits": 4900  (aprox.)

# Después de 50 minutos
GET /api/v1/usuarios/1/song-credits
Expected: "available_credits": 0 (o cercano a 0)

# Intento de agregar canción
POST /api/v1/canciones/1
Expected: ❌ 402 Payment Required
```

### Test 5: Compra Multiple

```bash
# Compra 2 productos
POST /api/v1/consumos/pedir/1
Body: {
  "items": [
    {"producto_id": 1, "cantidad": 1},  // $5,000
    {"producto_id": 2, "cantidad": 2}   // $6,000 (2x$3,000)
  ]
}
Expected: ✅ 200 OK, consumos creados

# Verificar créditos
GET /api/v1/usuarios/1/available-credits
Expected: "credits_available": 11000
```

### Test 6: Detalle de Créditos

```bash
GET /api/v1/usuarios/1/song-credits
Expected Response:
{
  "available_credits": 4900,
  "credits_detail": [
    {
      "credit_id": 1,
      "original_value": 5000,
      "current_value": 4900,
      "minutes_remaining": 49
    },
    {
      "credit_id": 2,
      "original_value": 6000,
      "current_value": 5900,
      "minutes_remaining": 59
    }
  ],
  "needs_purchase": false,
  "minutes_to_zero": 49
}
```

### Test 7: Admin Ver Créditos

```bash
# Admin puede ver créditos de cualquier usuario
GET /api/v1/admin/usuarios/1/song-credits
Header: "Authorization: Bearer YOUR_API_KEY"
Expected: Mismo response que test 6
```

---

## 🔧 Configuración Avanzada

### Cambiar Decaimiento (100 puntos/minuto)

En `crud.py`, función `get_available_song_credits()`:

```python
# Cambiar esto:
remaining_credit = max(0, credit.credits_value - int(minutes_elapsed * 100))

# Ejemplos:
# Por minuto = 50:   int(minutes_elapsed * 50)
# Por minuto = 200:  int(minutes_elapsed * 200)
# Por hora = 100:    int(hours_elapsed * 100)
```

### Cambiar Crédito Inicial

En `models.py`:

```python
# Cambiar esto:
song_credits = Column(Integer, default=1)

# Ejemplos:
song_credits = Column(Integer, default=0)   # Sin créditos iniciales
song_credits = Column(Integer, default=5)   # 5 créditos iniciales
```

### Cambiar Intervalo de Background Task

En `song_credits_background.py`:

```python
# Cambiar esto:
await asyncio.sleep(60)  # Ejecuta cada 60 segundos

# Ejemplos:
await asyncio.sleep(30)   # Cada 30 segundos
await asyncio.sleep(300)  # Cada 5 minutos
```

---

## 📊 Monitoreo

### Ver Logs de Créditos

```bash
# Ver en karaoke_debug.log
tail -f karaoke_debug.log | grep Credits

# O buscar específicamente
grep "song_credits_background\|Crédito.*expirado" karaoke_debug.log
```

### Consultar BD Directamente

```sql
-- Ver todos los créditos de un usuario
SELECT * FROM song_credits WHERE usuario_id = 1;

-- Ver créditos activos (no consumidos)
SELECT * FROM song_credits 
WHERE consumed_at IS NULL 
AND consumed_by_song_id IS NULL;

-- Ver créditos expirados
SELECT * FROM song_credits WHERE expires_at IS NOT NULL;

-- Ver cuántos créditos tiene cada usuario
SELECT 
  u.id, u.nick, COUNT(sc.id) as num_credits
FROM usuarios u
LEFT JOIN song_credits sc ON u.id = sc.usuario_id
  AND sc.consumed_at IS NULL
  AND sc.consumed_by_song_id IS NULL
GROUP BY u.id;
```

---

## 🐛 Troubleshooting

### Error: "Tabla 'song_credits' no existe"

**Solución:**
```python
# Reiniciar la app, se creará automáticamente:
python -m uvicorn main:app --reload
```

### Error 402 aunque compró hace poco

**Verificar:**
```bash
GET /api/v1/usuarios/{user_id}/song-credits
# Ver: "minutes_remaining" y si es muy bajo, créditos están por expirar
```

### Background task no decrementa

**Verificar logs:**
```bash
# Debe haber líneas como:
grep "Credits decay worker" karaoke_debug.log
```

### Usuario no ve nuevo crédito después de comprar

**Verificar:**
```bash
# 1. Consumo se creó
SELECT * FROM consumos WHERE usuario_id = X;

# 2. Créditos se asignaron
SELECT * FROM song_credits WHERE usuario_id = X;

# 3. Endpoint no hace cache
GET /api/v1/usuarios/{user_id}/available-credits
```

---

## ✅ Checklist de Rollout

- [ ] Backup de BD realizado
- [ ] Código actualizado en todos los archivos
- [ ] App reiniciada con cambios
- [ ] Verificar creación de tabla `song_credits`
- [ ] Test 1: Crédito inicial (PASS)
- [ ] Test 2: Agregar canción (PASS)
- [ ] Test 3: Comprar y obtener créditos (PASS)
- [ ] Test 4: Decaimiento después de 1+ minuto (PASS)
- [ ] Test 5: Múltiples compras (PASS)
- [ ] Test 6: Ver detalle de créditos (PASS)
- [ ] Test 7: Admin puede ver créditos (PASS)
- [ ] Usuarios existentes pueden agregar canciones
- [ ] Background task en logs
- [ ] Notificar a frontend sobre nuevos endpoints

---

## 📱 Integración con Frontend

### Endpoints que el frontend necesita conocer:

```javascript
// Para usuario común:
GET  /api/v1/usuarios/{id}/available-credits
GET  /api/v1/usuarios/{id}/song-credits
POST /api/v1/canciones/{id}        // Con error 402 si sin créditos
POST /api/v1/consumos/pedir/{id}   // Asigna créditos automáticamente

// Para admin:
GET  /api/v1/admin/usuarios/{id}/song-credits
```

### Manejo de error 402:

```javascript
async function addSong(userId, songData) {
  try {
    const response = await fetch(`/api/v1/canciones/${userId}`, {
      method: 'POST',
      body: JSON.stringify(songData)
    });
    
    if (response.status === 402) {
      // Error de créditos
      const data = await response.json();
      showMessage("❌ " + data.detail);
      // Sugerir: "Haz un pedido en el menú de productos"
      redirectToMenu();
    }
  } catch (error) {
    console.error(error);
  }
}
```

---

## 🎓 Documentación Completa

Ver archivo: `SISTEMA_CREDITOS_CANCIONES.md`

---

**Última actualización: 04/02/2026**
