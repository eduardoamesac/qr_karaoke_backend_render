# Sistema de Créditos de Canciones - Implementación Completa

## 📋 Descripción General

Se ha implementado un nuevo sistema de cola de canciones basado en **créditos matemáticos por compra de productos**. En lugar de una cola inteligente que acomoda las canciones, ahora funciona así:

### Flujo del Sistema:

1. **Al ingresar a la app**: El usuario obtiene **1 crédito** para agregar una canción
2. **Al comprar productos**: Se asignan créditos según el valor en pesos
   - Cerveza $5,000 = 5,000 créditos
   - Energética $3,000 = 3,000 créditos
   - Etc.
3. **Decaimiento de créditos**: Los créditos decaen 100 puntos **cada minuto**
4. **Cuando llega a 0**: El usuario ya no puede agregar canciones y ve un mensaje indicando que debe hacer un pedido
5. **Estado en tiempo real**: Se muestra cuánto tiempo le queda antes de que expire el crédito

---

## 🔧 Cambios Implementados

### 1. **Modelos de Base de Datos (models.py)**

#### Nuevos campos en `Usuario`:
```python
song_credits = Column(Integer, default=1)  # Créditos disponibles
credits_added_at = Column(DateTime, default=now_bogota())  # Última vez que se agregaron
last_song_added_at = Column(DateTime, nullable=True)  # Última canción agregada
```

#### Nueva tabla `SongCredits`:
```python
class SongCredits(Base):
    """Tracking de créditos de canciones por usuario"""
    id: Integer (PK)
    usuario_id: Integer (FK)
    credits_value: Integer  # Valor original (ej: 5000)
    created_at: DateTime  # Cuándo se creó el crédito
    expires_at: DateTime  # Cuándo expiró (llegó a 0)
    consumed_at: DateTime  # Cuándo fue consumido
    consumed_by_song_id: Integer  # Canción que lo consumió
```

---

### 2. **Funciones CRUD (crud.py)**

#### `add_song_credits(db, usuario_id, credit_value)`
- Agrega nuevos créditos a un usuario
- Se llama automáticamente cuando se crea un consumo

#### `get_available_song_credits(db, usuario_id)`
- Retorna los créditos disponibles considerando el decaimiento
- Calcula minutos transcurridos × 100 puntos/minuto
- Marca como expirados los que llegaron a 0

#### `get_user_credits_detail(db, usuario_id)`
- Retorna información detallada de créditos
- Incluye: créditos disponibles, detalle por grupo, minutos restantes

#### `consume_song_credit(db, usuario_id, cancion_id)`
- Consume un crédito cuando el usuario agrega una canción
- Retorna `True` si hay crédito, `False` si no

---

### 3. **Modificación de Endpoints**

#### `POST /api/v1/canciones/{usuario_id}` (canciones.py)
- **Antes**: Validaba solo duración y duplicados
- **Ahora**: Además valida créditos disponibles
- Retorna error `402 (Payment Required)` si no hay créditos
- Muestra minutos hasta que expire el crédito en el mensaje de error

#### `POST /api/v1/consumos/{usuario_id}` (consumos.py)
- **Cambio**: Automáticamente agrega créditos al usuario cuando compra

#### `POST /api/v1/consumos/pedir/{usuario_id}` (consumos.py)
- **Cambio**: También agrega créditos automáticamente

#### `POST /api/v1/consumos/pedir/carrito/{usuario_id}` (consumos.py)
- **Cambio**: Suma todos los créditos del carrito y los asigna

---

### 4. **Nuevos Endpoints**

#### `GET /api/v1/usuarios/{usuario_id}/song-credits`
- Obtiene créditos detallados
- Retorna: disponibles, detalle por grupo, minutos restantes

#### `GET /api/v1/usuarios/{usuario_id}/cuenta-regresiva`
- Endpoint simplificado para la UI
- Muestra si puede agregar canción o necesita comprar

#### `GET /api/v1/usuarios/{usuario_id}/available-credits` (público)
- Endpoint público para verificar créditos
- Mensaje simple: "Puedes agregar" vs "Debes hacer un pedido"

#### `GET /api/v1/admin/usuarios/{usuario_id}/song-credits` (admin)
- Admin puede ver el detalle de créditos de cualquier usuario

---

### 5. **Tarea de Background (song_credits_background.py)**

Nueva tarea asincrónica que se ejecuta **cada 60 segundos**:
- Verifica créditos que llegaron a 0
- Marca como expirados
- Registra en logs

Se inicia automáticamente en el `lifespan` de FastAPI

---

## 📊 Schemas Actualizados (schemas.py)

- `Usuario`: Agregado campo `song_credits`
- `UsuarioConectado`: Agregado campo `song_credits`
- `UsuarioPublico`: Agregado campo `song_credits`

---

## 🚀 Cómo Funciona

### Ejemplo Práctico:

1. **Marco entra a la app en la Mesa 1**
   - Sistema: "Marco, tienes 1 crédito para agregar una canción"
   - Marco agrega "Bohemian Rhapsody"

2. **Marco quiere agregar otra canción**
   - Sistema: "No tienes créditos. Haz un pedido para agregar más"

3. **Marco pide una cerveza ($5,000)**
   - Sistema: "✅ Consumo registrado. Se te asignaron 5,000 créditos"
   - Marco ahora tiene 5,000 créditos

4. **Pasa 1 minuto**
   - Créditos: 5,000 - 100 = 4,900

5. **Pasan 50 minutos**
   - Créditos: 5,000 - 5,000 = 0
   - Sistema: "Tus créditos expiraron. Debes hacer un pedido para agregar más canciones"

6. **Marco pide otra cerveza ($5,000)**
   - Sistema: "✅ Se te asignaron 5,000 créditos nuevos"

---

## 💾 Base de Datos

### Tabla Creada: `song_credits`

```sql
CREATE TABLE song_credits (
  id INTEGER PRIMARY KEY,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
  credits_value INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT NOW,
  expires_at DATETIME NULL,
  consumed_at DATETIME NULL,
  consumed_by_song_id INTEGER NULL REFERENCES canciones(id)
);
```

### Cambios en tabla `usuarios`:
- Nuevas columnas: `song_credits`, `credits_added_at`, `last_song_added_at`

---

## 🔔 Validaciones

### Al intentar agregar una canción:
```
✅ Si tiene créditos > 0:
   - Se consume 1 "crédito lógico"
   - Se crea la canción
   - Se marca en consumed_at la cual canción consumió

❌ Si tiene créditos <= 0:
   - Error 402 (Payment Required)
   - Mensaje: "No tienes créditos... Minutos hasta 0: 45.3"
```

### Decaimiento automático:
```
Cada minuto:
  créditos_actuales = créditos_originales - (minutos_transcurridos × 100)
  
Ejemplo:
  - Crédito original: 5,000
  - Después de 10 min: 5,000 - 1,000 = 4,000
  - Después de 50 min: 5,000 - 5,000 = 0 (expirado)
```

---

## 📱 Frontend - Cambios Recomendados

### En la UI del usuario:
```javascript
// Antes de mostrar botón para agregar canción:
GET /api/v1/usuarios/{usuario_id}/available-credits

if (response.can_add_song) {
  // Mostrar: "Puedes agregar una canción"
  // Botón: "Agregar canción"
} else {
  // Mostrar: "Debes hacer un pedido para agregar más canciones"
  // Botón: "Ver menú de productos"
  // Info: "Tiempo hasta que expire crédito: X minutos"
}
```

### Mostrar contador en tiempo real:
```javascript
// Para el usuario que compró y tiene créditos que decaen:
GET /api/v1/usuarios/{usuario_id}/song-credits

Mostrar:
- "Tienes 4,500 créditos disponibles"
- "⏱️ Vencen en 44 minutos"
- Progreso visual del decaimiento
```

---

## 🐛 Casos Especiales Manejados

1. **Usuario intenta agregar 2 canciones sin comprar nada**
   - Primera: ✅ Se usa el crédito inicial (1)
   - Segunda: ❌ Error 402, sin créditos

2. **Créditos expiran mientras el usuario está en la app**
   - Background task marca como `expires_at`
   - En siguiente intento, detecta crédito = 0

3. **Usuario compra mientras está agregando canción**
   - Los nuevos créditos se suman inmediatamente
   - Puede reintentar agregar canción

4. **Múltiples compras en poco tiempo**
   - Se crean múltiples registros en `SongCredits`
   - Se suman todos los créditos válidos (no expirados)

---

## ⚙️ Configuración

### Variables de entorno: *(ninguna nueva requerida)*

### Constantes en el código:
```python
CREDITS_DECAY_PER_MINUTE = 100  # Puntos que pierde por minuto
INITIAL_CREDITS = 1  # Créditos al ingresar
```

---

## 🔄 Flujo de Integración

1. ✅ **models.py** - Agregar campos a `Usuario` y tabla `SongCredits`
2. ✅ **schemas.py** - Actualizar schemas de usuario
3. ✅ **crud.py** - Agregar funciones de créditos
4. ✅ **canciones.py** - Validar créditos antes de agregar
5. ✅ **consumos.py** - Agregar créditos automáticamente
6. ✅ **usuarios.py** - Endpoints para ver créditos
7. ✅ **admin.py** - Admin puede ver créditos de usuarios
8. ✅ **song_credits_background.py** - Tarea de decaimiento
9. ✅ **main.py** - Iniciar tarea de background

---

## 📈 Ventajas del Sistema

✅ **Justo**: Todos empiezan con 1 crédito
✅ **Incentiva compras**: Más créditos con más gasto
✅ **Matemático**: Decaimiento constante (100/min)
✅ **Automático**: No requiere intervención manual
✅ **Escalable**: Funciona con cualquier precio de producto
✅ **Transparente**: Usuario ve exactamente cuándo expira
✅ **Simple**: Una canción = 1 crédito consumido

---

## 🚨 Notas Importantes

1. La migración de base de datos se ejecutará automáticamente al iniciar la app
2. Los usuarios existentes tendrán `song_credits = 1` (valor por defecto)
3. No hay "deuda" - los créditos no pueden ser negativos
4. Una vez que expire un crédito, no se recupera (solo comprando más)
5. El decaimiento se calcula en tiempo real (no almacenado)

---

## 🧪 Testing

Para probar el sistema:

```bash
# 1. Crear usuario
POST /api/v1/mesas/{mesa_id}/usuarios
Body: {"nick": "TestUser"}

# 2. Intentar agregar canción (debe funcionar con 1 crédito)
POST /api/v1/canciones/{usuario_id}

# 3. Ver créditos
GET /api/v1/usuarios/{usuario_id}/available-credits

# 4. Intentar agregar otra (debe fallar)
POST /api/v1/canciones/{usuario_id}  -> Error 402

# 5. Hacer pedido
POST /api/v1/consumos/pedir/{usuario_id}

# 6. Ver créditos nuevos
GET /api/v1/usuarios/{usuario_id}/available-credits

# 7. Esperar 60 segundos (background task decrementa)
# Esperar otro minuto...
```

---

**Implementación completada el 04/02/2026**
