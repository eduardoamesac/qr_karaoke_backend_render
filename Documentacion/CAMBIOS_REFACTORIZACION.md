# Refactorización de Arquitectura: BD → Cache JSON

## 📋 Resumen de Cambios

Se ha refactorizado la aplicación para optimizar la base de datos, manteniendo solo las tablas críticas en BD y moviendo todo lo demás a JSON (cache).

## 🗄️ Tablas que se Mantienen en BD

1. **usuarios** - Datos de usuarios (nick, puntos, nivel, etc.)
2. **productos** - Catálogo de productos (nombre, precio, stock)
3. **pagos** - Registros de pagos (monto, método, fecha)
4. **admin_api_keys** - Claves API para admin

## 📦 Datos Movidos a Cache JSON (en carpeta `/cache`)

1. **mesas.json**
   - Información de mesas (id, nombre, qr_code, is_active)
   - Archivo centralizado con todas las mesas

2. **mesa_cuenta_*.json** (por cada mesa)
   - Información de cuentas de mesas
   - Consumos y pagos de cada mesa
   - Totales y saldos

3. **consumos.json**
   - Todos los consumos (cantidad, valor, producto_id, mesa_id, usuario_id)
   - Archivo centralizado

4. **song_credits_*.json** (por usuario)
   - Créditos de canciones por usuario
   - Historial de consumo de créditos

5. **canciones_global.json** + **user_songs_*.json** (preexistente)
   - Canciones por usuario
   - Ya estaba en cache

## 🔄 Cambios en cache_manager.py

Se han agregado nuevos métodos:

### Métodos de Mesas
- `create_mesa_in_cache()` - Crear mesa
- `get_mesa_by_id()` - Obtener mesa por ID
- `get_mesa_by_qr()` - Obtener mesa por QR
- `get_all_mesas()` - Obtener todas las mesas
- `update_mesa_in_cache()` - Actualizar mesa
- `delete_mesa_from_cache()` - Eliminar mesa

### Métodos de Consumos
- `create_consumo_in_cache()` - Crear consumo
- `get_consumo_by_id()` - Obtener consumo
- `get_consumos_by_mesa()` - Consumos por mesa
- `get_consumos_by_usuario()` - Consumos por usuario
- `get_all_consumos()` - Todos los consumos

### Métodos de Song Credits
- `add_song_credits()` - Agregar créditos
- `get_song_credits()` - Obtener créditos
- `get_active_song_credits()` - Créditos activos
- `consume_song_credits()` - Marcar crédito consumido

## 🔧 Cambios en models.py

Se eliminaron las siguientes clases:
- ❌ `Mesa`
- ❌ `Cuenta`
- ❌ `Cancion`
- ❌ `Consumo`
- ❌ `SongCredits`

Se mantuvieron:
- ✅ `Usuario`
- ✅ `Producto`
- ✅ `AdminApiKey`
- ✅ `Pago` (modificado - mesa_id sin FK)

## 📝 Cambios Necesarios en crud.py

Reemplazar las funciones que acceden a BD por versiones que usan cache_manager:

```python
# ANTES (usando BD)
def get_mesa_by_qr(db: Session, qr_code: str):
    return db.query(models.Mesa).filter(models.Mesa.qr_code == qr_code).first()

# DESPUÉS (usando Cache)
def get_mesa_by_qr(db: Session, qr_code: str):
    return cache_manager.get_mesa_by_qr(qr_code)
```

Ver el archivo `crud_cache_updated.py` para todas las funciones actualizadas.

## 🎯 Funciones a Actualizar en crud.py

### Mesas (15+ funciones)
- `get_mesa_by_qr()` 
- `get_mesas()`
- `create_mesa()`
- `get_mesa_by_id()`
- `delete_mesa()`
- `get_mesas_vacias()`
- `set_mesa_active_status()`
- Otras funciones de análisis por mesa

### Consumos (8+ funciones)
- `create_consumo_para_usuario()`
- `get_consumos_por_usuario()`
- `get_consumos_por_mesa()`
- `get_consumo_por_mesa()`
- `get_recent_consumos()`
- Funciones de reportes

### Song Credits (4+ funciones)
- `add_song_credits_to_usuario()`
- `get_song_credits()`
- `consume_song_credit()`

## 🚀 Pasos para Implementar

1. **Aplicar migración de Alembic**
   ```bash
   alembic upgrade cleanup_cache_optimization
   ```

2. **Actualizar crud.py**
   - Copiar funciones de `crud_cache_updated.py`
   - Reemplazar funciones antiguas en `crud.py`
   - Asegurar que all imports incluyan `cache_manager`

3. **Verificar routers**
   - Revisar archivos que importan models eliminados
   - Reemplazar referencias a funciones de crud

4. **Restaurar datos existentes (opcional)**
   - Si hay datos en BD, migrar a JSON antes de eliminar tablas

## ⚡ Beneficios

✅ Base de datos más pequeña (solo datos críticos)
✅ Mejor rendimiento para transacciones rápidas
✅ Más flexibilidad para estructura de datos
✅ Fácil backup/restore con archivos JSON
✅ Menos consultas a BD

## ⚠️ Consideraciones

- Los datos en cache JSON se persisten en disco
- Asegurar que la carpeta `/cache` tenga permisos de lectura/escritura
- El cache se carga en memoria al iniciar la aplicación
- Para producción, considerar sincronización entre instancias

## 📊 Arquitetura Final

```
DB (MySQL)
├── usuarios
├── productos
├── pagos
└── admin_api_keys

Cache (JSON en /cache/)
├── mesas.json
├── consumos.json
├── mesa_cuenta_1.json
├── mesa_cuenta_2.json
├── song_credits_1.json
├── song_credits_2.json
├── canciones_global.json
└── user_songs_*.json
```
