# 🛠️ Scripts de Utilidad — QR Karaoke Backend

Esta carpeta contiene scripts de utilidad y mantenimiento para el sistema QR Karaoke.

> **Nota**: Estos scripts NO son parte de la aplicación principal. Son herramientas de mantenimiento y configuración inicial que se ejecutan manualmente.

> ⚠️ **Importante**: Todos los scripts deben ejecutarse **desde la raíz del proyecto**, no desde dentro de la carpeta `scripts/`. Ejemplo:
> ```bash
> # ✅ Correcto (desde la raíz del proyecto)
> python scripts/tail_log.py
> 
> # ❌ Incorrecto (desde dentro de scripts/)
> cd scripts && python tail_log.py
> ```

---

## Scripts de Configuración Inicial

### `crear_mesas.py`

**Propósito**: Crea las mesas iniciales en la base de datos.

**Cuándo ejecutar**: Una sola vez, al configurar el local por primera vez.

```bash
python scripts/crear_mesas.py
```

---

### `create_db.py`

**Propósito**: Crea el esquema inicial de la base de datos SQLite para desarrollo local.

**Cuándo ejecutar**: Al configurar el entorno de desarrollo local.

```bash
python scripts/create_db.py
```

---

### `create_mysql_schema.py`

**Propósito**: Crea el esquema de base de datos compatible con MySQL/MariaDB.

**Cuándo ejecutar**: Al migrar a una base de datos MySQL.

```bash
python scripts/create_mysql_schema.py
```

---

## Scripts de Generación de QR

### `generate_qr_admin.py`

**Propósito**: Genera el código QR para el acceso al panel de administración.

**Cuándo ejecutar**: Al cambiar la URL del panel de administración o para regenerar el QR.

```bash
python scripts/generate_qr_admin.py
```

---

### `generate_qr_mesas.py`

**Propósito**: Genera los códigos QR para todas las mesas del local. Los archivos se guardan en `qrcodes_mesas/`.

**Cuándo ejecutar**: Al agregar nuevas mesas o regenerar los QR existentes.

```bash
python scripts/generate_qr_mesas.py
```

---

## Scripts de Verificación

### `verify_account_restriction.py`

**Propósito**: Verifica que las restricciones de cuenta por mesa funcionen correctamente.

**Cuándo ejecutar**: Después de cambios en el módulo de cuentas.

```bash
python scripts/verify_account_restriction.py
```

---

### `verify_lazy_implementation.py`

**Propósito**: Verifica que la implementación del reordenamiento lazy de la cola funcione correctamente.

**Cuándo ejecutar**: Después de cambios en el sistema de cola de canciones.

```bash
python scripts/verify_lazy_implementation.py
```

---

### `verify_simple.py`

**Propósito**: Verificación básica del estado general del sistema.

**Cuándo ejecutar**: Como diagnóstico rápido del sistema.

```bash
python scripts/verify_simple.py
```

---

## Scripts de Corrección (Fix)

### `fix_admin.py`

**Propósito**: Corrige problemas en el panel de administración (rutas, permisos, etc.).

**Cuándo ejecutar**: Al detectar problemas específicos en el panel admin.

```bash
python scripts/fix_admin.py
```

---

### `fix_crud.py`

**Propósito**: Corrige inconsistencias en las operaciones CRUD de la base de datos.

**Cuándo ejecutar**: Al detectar datos corruptos o inconsistentes.

```bash
python scripts/fix_crud.py
```

---

### `fix_ganancias.py`

**Propósito**: Corrige cálculos de ganancias en la base de datos.

**Cuándo ejecutar**: Al detectar inconsistencias en los reportes de ganancias.

```bash
python scripts/fix_ganancias.py
```

---

## Scripts de Diagnóstico

### `tail_log.py`

**Propósito**: Muestra las últimas líneas del log de la aplicación en tiempo real (similar a `tail -f`).

**Cuándo ejecutar**: Para monitorear la actividad de la aplicación en tiempo real.

```bash
python scripts/tail_log.py
```

---

### `random_scorer.py`

**Propósito**: Genera puntuaciones aleatorias para testing del sistema de scoring de canciones.

**Cuándo ejecutar**: Al probar el sistema de puntuación.

```bash
python scripts/random_scorer.py
```

---

## Scripts Adicionales en la carpeta `scripts/`

La carpeta `scripts/` también contiene scripts de soporte para testing y diagnóstico de conexiones:

- `check_all_mesas.py` — Verifica el estado de todas las mesas
- `check_openapi.py` — Verifica que el schema OpenAPI sea válido
- `clear_mesas.py` — Limpia datos temporales de mesas
- `create_mesa_temp.py` — Crea una mesa temporal para testing
- `list_mesas_temp.py` — Lista mesas temporales creadas
- `list_routes.py` — Lista todas las rutas registradas en FastAPI
- `simulate_broken_ws_and_post.py` — Simula una conexión WebSocket rota para pruebas
