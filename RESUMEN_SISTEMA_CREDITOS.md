# 🎵 Nuevo Sistema de Cola de Canciones - Resumen de Cambios

## ✅ Implementación Completada

He reemplazado completamente la lógica de la cola de canciones por un **sistema matemático basado en créditos**.

---

## 🎯 Cómo Funciona Ahora

### El Flujo:

```
Usuario entra a la app
       ↓
Recibe 1 crédito (derecho a agregar 1 canción)
       ↓
¿Quiere agregar más canciones?
       ↓
   SÍ → Debe hacer un pedido de productos
       ↓
Compra una cerveza ($5,000) = Recibe 5,000 créditos
       ↓
Los créditos disminuyen 100 puntos cada minuto
       ↓
Después de 50 minutos → Créditos = 0
       ↓
Debe hacer otro pedido para agregar más canciones
```

---

## 📊 Ejemplo en Números

### Escenario: Marco en la Mesa 1

| Hora | Evento | Créditos | Acción |
|------|--------|----------|--------|
| 9:00 | Marco entra | 1 | ✅ Agrega "Bohemian Rhapsody" |
| 9:00 | Intenta agregar otra | 0 | ❌ **Rechazado**: "Debes hacer pedido" |
| 9:05 | Pide Cerveza ($5,000) | 5,000 | ✅ Se asignan 5,000 créditos |
| 9:06 | Pasa 1 minuto | 4,900 | - Créditos decaen 100/min |
| 9:15 | Pasan 10 min totales | 4,000 | ✅ Puede agregar canción |
| 9:55 | Pasan 50 min totales | 0 | ❌ Créditos expirados |
| 9:55 | Pide otra Cerveza | 5,000 | ✅ Se asignan 5,000 créditos nuevos |

---

## 💻 Cambios Técnicos

### 1️⃣ Base de Datos

**Nueva tabla `song_credits`:**
- Almacena cada compra de créditos
- Tracks de cuándo se crean, consumen y expiran
- Vinculada a la canción que consumió el crédito

**Nuevos campos en `usuarios`:**
- `song_credits` - Créditos disponibles (cálculo en tiempo real)
- `credits_added_at` - Cuándo se asignaron
- `last_song_added_at` - Cuándo agregó última canción

### 2️⃣ Validaciones

**Al agregar canción:**
```
✅ Si tiene créditos > 0:
   POST /api/v1/canciones/{usuario_id}
   → Canción agregada ✓
   
❌ Si tiene créditos = 0:
   POST /api/v1/canciones/{usuario_id}
   → Error 402: "No tienes créditos. Minutos hasta 0: 45"
```

### 3️⃣ Automático al Comprar

Cada consumo suma créditos:
```python
# Cuando compra:
compra_valor = 5000  # Cerveza
créditos_asignados = 5000  # 1 peso = 1 crédito

# Cuando pasan minutos:
créditos_actuales = créditos_asignados - (minutos × 100)
```

### 4️⃣ Tarea de Background

Cada 60 segundos:
- Verifica qué créditos llegaron a 0
- Los marca como expirados
- Registra en logs

---

## 🔌 Endpoints Nuevos/Modificados

### Agregar Canción (MODIFICADO)
```
POST /api/v1/canciones/{usuario_id}
Nuevo: Valida créditos antes de crear canción
Error: 402 si no hay créditos
```

### Ver Créditos Disponibles (NUEVO)
```
GET /api/v1/usuarios/{usuario_id}/available-credits
Respuesta: {
  "usuario_id": 5,
  "nick": "Marco",
  "credits_available": 4500,
  "can_add_song": true,
  "needs_purchase": false,
  "message": "Puedes agregar una canción"
}
```

### Detalle de Créditos (NUEVO)
```
GET /api/v1/usuarios/{usuario_id}/song-credits
Respuesta: {
  "available_credits": 4500,
  "credits_detail": [
    {
      "credit_id": 1,
      "original_value": 5000,
      "current_value": 4500,
      "minutes_remaining": 45
    }
  ],
  "needs_purchase": false,
  "minutes_to_zero": 45
}
```

### Admin - Ver Créditos de Usuario (NUEVO)
```
GET /api/v1/admin/usuarios/{usuario_id}/song-credits
(Solo admin)
```

---

## 🎨 Para la UI del Usuario

### Mostrar Estado de Créditos:

```javascript
// Antes de mostrar botón "Agregar Canción":
async function checkCanAddSong(usuarioId) {
  const res = await fetch(`/api/v1/usuarios/${usuarioId}/available-credits`);
  const data = await res.json();
  
  if (data.can_add_song) {
    // Mostrar botón activo: "Agregar Canción" ✅
  } else {
    // Mostrar desactivado con mensaje:
    // "Debes hacer un pedido para agregar más" + link a menú
  }
}
```

### Mostrar Contador Regresivo:

```javascript
// Si tiene créditos, mostrar cuánto tiempo le queda:
async function updateCreditsTimer(usuarioId) {
  const res = await fetch(`/api/v1/usuarios/${usuarioId}/song-credits`);
  const data = await res.json();
  
  const creditsLeft = data.available_credits;
  const minutesLeft = Math.ceil(creditsLeft / 100);
  
  // Mostrar: "Tienes 4,500 créditos (44 minutos)"
  // Actualizar cada 10 segundos
}
```

---

## 🧪 Casos de Uso

### ✅ Marco quiere agregar 3 canciones

1. **Entra a la app** → Tiene 1 crédito
2. **Agrega canción 1** → Usa el crédito inicial
3. **Intenta agregar canción 2** → ❌ Rechazado, sin créditos
4. **Pide cerveza $5,000** → ✅ Obtiene 5,000 créditos
5. **Agrega canciones 2-5** → Usa créditos disponibles
6. **Espera 50 minutos** → Créditos expiran
7. **Intenta agregar canción 6** → ❌ Sin créditos
8. **Pide cerveza otra vez** → ✅ 5,000 créditos nuevos

### ✅ Sara gasta más

1. **Entra** → 1 crédito
2. **Agrega canción 1** → Usa crédito
3. **Pide surtido de 4 productos** → 15,000 créditos
4. **Agrega 10 canciones seguidas** → Todas exitosas
5. **Espera 2 horas** → Créditos expiran
6. **No pide nada** → Sin permiso para más canciones

---

## 🚀 Ventajas

| Ventaja | Beneficio |
|---------|-----------|
| **Justo** | Todos empiezan igual (1 crédito) |
| **Transparente** | Usuario ve exactamente cuándo expira |
| **Automático** | Sin intervención manual |
| **Matemático** | Decaimiento constante (100/min) |
| **Escalable** | Funciona con cualquier precio |
| **Incentiva compras** | Más créditos = más gasto de usuario |

---

## 📁 Archivos Modificados

```
✅ models.py              → Nuevos campos y tabla SongCredits
✅ schemas.py            → Campos actualizados en Usuario
✅ crud.py               → Funciones de créditos + lógica
✅ canciones.py          → Validación de créditos al agregar
✅ consumos.py           → Automático asignar créditos
✅ usuarios.py           → Endpoints para ver créditos
✅ admin.py              → Endpoints admin de créditos
✅ main.py               → Inicia tarea de background
✅ song_credits_background.py  → Archivo nuevo (decaimiento)
```

---

## ⚠️ Notas Importantes

1. **Migración automática** - Al iniciar, la BD se actualiza automáticamente
2. **Usuarios existentes** - Tendrán `song_credits = 1` por defecto
3. **Sin deuda** - Los créditos no pueden ser negativos
4. **No hay recuperación** - Solo se recuperan comprando
5. **Cálculo en tiempo real** - No almacenado, se calcula al solicitar

---

## 🔍 Validaciones

### Antes de agregar canción:
1. ✅ Usuario existe
2. ✅ Usuario no está silenciado
3. ✅ **Tiene créditos > 0** ← NUEVO
4. ✅ Hay tiempo hasta cierre
5. ✅ No es duplicado en la mesa
6. ✅ Cola no sobrepasa horario

---

## 📞 Soporte

Si necesitas:
- **Ajustar decaimiento** → Cambiar `100` en `crud.py` función `get_available_song_credits()`
- **Créditos iniciales** → Cambiar `default=1` en `models.py` Usuario
- **Ver todos los créditos de usuarios** → Ver documento `SISTEMA_CREDITOS_CANCIONES.md`

---

**Sistema implementado y testeado ✅**  
**Fecha: 04/02/2026**
