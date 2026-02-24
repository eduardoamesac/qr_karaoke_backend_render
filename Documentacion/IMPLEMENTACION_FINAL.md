# 🔄 GUÍA FINAL: REFACTORIZACIÓN BD → CACHE JSON

## ✅ Tareas Completadas

### 1. ✅ **cache_manager.py Expandido**
- Agregados métodos para mesas (create, get, update, delete)
- Agregados métodos para consumos (create, get, update, delete)
- Agregados métodos para song_credits (add, get, consume)
- Sistema de persistencia en JSON para todos los datos

### 2. ✅ **models.py Simplificado**
- Eliminadas clases: Mesa, Cuenta, Cancion, Consumo, SongCredits
- Mantenidas clases: Usuario, Producto, AdminApiKey, Pago
- Pago.mesa_id es ahora un Integer sin FK (controlado vía cache)

### 3. ✅ **Migración Alembic Creada**
- Archivo: `alembic/versions/cleanup_cache_optimization.py`
- Elimina las tablas de BD
- Mantiene las 4 tablas principales

### 4. ✅ **Documentación Creada**
- `CAMBIOS_REFACTORIZACION.md` - Explicación completa
- `crud_cache_updated.py` - Funciones ejemplo
- `update_crud_manual_guide.py` - Guía de actualización

## 🔧 TAREAS PENDIENTES (MANUAL)

### PASO 1: Aplicar Migración

```bash
alembic upgrade cleanup_cache_optimization
```

### PASO 2: Actualizar crud.py

Reemplaza estas funciones usando la referencia en `crud_cache_updated.py`:

#### MESAS (15 funciones)
```python
# Reemplazar TODAS estas funciones:
- get_mesa_by_qr()
- get_mesas()
- create_mesa()
- create_usuario_en_mesa()  # Actualizar para no usar mesa_id FK
- get_mesa_by_id()
- delete_mesa()
- update_usuario_mesa()
- get_mesas_vacias()
- set_mesa_active_status()
- get_ingresos_por_mesa()
- get_estado_mesas()
- get_resumen_mesa()
- get_productos_mas_consumidos_por_mesa()
- get_canciones_cantadas_por_mesa()
- get_ingresos_promedio_por_usuario_por_mesa()
```

#### CONSUMOS (10 funciones)
```python
# Reemplazar TODAS estas funciones:
- create_consumo_para_usuario()
- get_consumos_por_usuario()
- get_consumo_por_mesa()
- get_recent_consumos()
- get_productos_mas_consumidos_por_mesa()
- get_categorias_mas_consumidas_por_mesa()
- get_canciones_mas_pedidas_por_mesa()
- get_usuarios_sin_consumo()
- get_usuarios_consumen_pero_no_cantan()
- get_total_consumido_por_usuario()
```

#### SONG CREDITS (4 funciones)
```python
# Reemplazar TODAS estas funciones:
- add_song_credits()
- get_song_credits()
- get_active_song_credits()
- consume_song_credit()
```

### PASO 3: Actualizar Imports en crud.py

Al inicio de crud.py, añade:
```python
from cache_manager import cache_manager
```

### PASO 4: Revisar y Actualizar Routers

Archivos que probablemente necesitan cambios:
- `mesas.py` - Manejo de mesas
- `consumos.py` - Manejo de consumos  
- `usuarios.py` - Referencias a mesa_id
- `admin.py` - Reportes basados en mesas
- `productos.py` - Referencias a consumos

### PASO 5: Verificar Imports de Modelos

Busca y elimina cualquier referencia a:
- `models.Mesa`
- `models.Cuenta`
- `models.Cancion`
- `models.Consumo`
- `models.SongCredits`

En los archivos:
- `schemas.py`
- Routers
- Otros módulos

## 📋 Checklist de Verificación

```
□ Migración Alembic aplicada exitosamente
□ crud.py actualizado con funciones de cache
□ Todos los imports de cache_manager agregados
□ models.py eliminado de schema definitions
□ Routers verificados y actualizados
□ No hay referencias a models.Mesa etc.
□ Aplicación inicia sin errores
□ Datos de mesas se guardan en /cache/mesas.json
□ Datos de consumos se guardan en /cache/consumos.json
```

## 🧪 Testing Recomendado

```python
# Verificar que cache_manager funciona
from cache_manager import cache_manager

# Crear mesa
mesa_id = cache_manager.create_mesa_in_cache("Mesa 1", "QR123")
print(f"Mesa creada: {mesa_id}")

# Crear consumo
consumo_id = cache_manager.create_consumo_in_cache({
    "cantidad": 1,
    "valor_total": 5000,
    "producto_id": 1,
    "mesa_id": mesa_id,
    "usuario_id": 1
})
print(f"Consumo creado: {consumo_id}")

# Obtener mesas
mesas = cache_manager.get_all_mesas()
print(f"Mesas en cache: {len(mesas)}")
```

## ⚠️ Notas Importantes

1. **Migración es DESTRUCTIVA**: Elimina todas las tablas viejas de BD
   - Hacer backup antes de ejecutar migración
   
2. **Cache es PERSISTENTE**: Datos se guardan en archivos JSON en `/cache/`
   - Hacer backup de carpeta cache regularmente
   
3. **Sin Sincronización Multi-Instancia**: Si ejecutas 2+ instancias de app
   - Todas leen/escriben al mismo cache
   - Usar un sistema de archivos compartido en producción
   
4. **Mesa_id y Cuenta eliminadas**: Cambio estructural importante
   - Usuario ya no tiene mesa_id en BD
   - Mesas se manejan vía cache
   - Cuentas están integradas en el cache de mesas

5. **Relaciones Eliminadas**: No hay más FK entre tablas eliminadas
   - Pago.mesa_id es solo un integer
   - Control manual de integridad

## 📞 Soporte

Si tienes dudas sobre las funciones nuevas, consulta:
- `crud_cache_updated.py` - Implementaciones ejemplo
- `cache_manager.py` - Métodos disponibles
- `CAMBIOS_REFACTORIZACION.md` - Documentación general

---
**Última actualización:** 2026-02-23
**Version:** 1.0
