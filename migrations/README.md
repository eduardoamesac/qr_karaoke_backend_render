# 🗄️ Scripts de Migración — QR Karaoke Backend

Esta carpeta contiene scripts de migración **ad-hoc** que se ejecutan manualmente para aplicar cambios de esquema a la base de datos de producción.

> **Nota**: Las migraciones automáticas de Alembic están en la carpeta [`alembic/`](../alembic/). Estos scripts son complementarios para cambios que requieren lógica adicional.

---

## ⚠️ Instrucciones Generales

1. **Siempre hacer un backup** de la base de datos antes de ejecutar cualquier migración
2. Ejecutar los scripts con la variable `DATABASE_URL` configurada correctamente
3. Verificar el resultado revisando la base de datos después de cada migración
4. Los scripts son idempotentes en la medida de lo posible (se pueden ejecutar múltiples veces sin daño)

---

## Scripts Disponibles

### `migrate_db.py`

**Propósito**: Migración general de la base de datos para actualizar el esquema inicial.

**Cuándo ejecutar**: Al hacer el primer despliegue o cuando se necesite inicializar la base de datos desde cero.

```bash
python migrations/migrate_db.py
```

---

### `apply_migration.py`

**Propósito**: Aplica una migración base al esquema de la base de datos.

**Cuándo ejecutar**: Cuando hay cambios de esquema que no están cubiertos por Alembic.

```bash
python migrations/apply_migration.py
```

---

### `apply_migration_cuentas.py`

**Propósito**: Migración específica para el módulo de cuentas y facturación por mesa.

**Cuándo ejecutar**: Al habilitar la funcionalidad de cuentas por mesa.

```bash
python migrations/apply_migration_cuentas.py
```

---

### `apply_approved_at_migration.py`

**Propósito**: Agrega el campo `approved_at` a la tabla de canciones en cola para rastrear cuándo fue aprobada cada canción.

**Cuándo ejecutar**: Una sola vez, después de implementar el sistema de aprobación con timestamp.

```bash
python migrations/apply_approved_at_migration.py
```

---

### `apply_costo_migration.py`

**Propósito**: Agrega el campo `costo` a la tabla de productos para registrar el costo de adquisición.

**Cuándo ejecutar**: Una sola vez, al implementar el módulo de ganancias.

```bash
python migrations/apply_costo_migration.py
```

---

### `apply_despachado_migration.py`

**Propósito**: Agrega el campo `despachado` a la tabla de consumos para indicar si el pedido fue entregado.

**Cuándo ejecutar**: Una sola vez, al implementar el seguimiento de despacho de pedidos.

```bash
python migrations/apply_despachado_migration.py
```

---

### `add_ganancias_functions.py`

**Propósito**: Agrega funciones y columnas necesarias para el módulo de cálculo de ganancias.

**Cuándo ejecutar**: Una sola vez, al activar el módulo de reportes de ganancias.

```bash
python migrations/add_ganancias_functions.py
```

---

### `add_is_karaoke_migration.py`

**Propósito**: Agrega el campo `is_karaoke` a la tabla de mesas para distinguir entre mesas de karaoke y mesas regulares.

**Cuándo ejecutar**: Una sola vez, al implementar el soporte de mesas mixtas.

```bash
python migrations/add_is_karaoke_migration.py
```

---

### `agregar_updatequeue.py`

**Propósito**: Agrega el evento `update_queue` al sistema de WebSockets para notificaciones en tiempo real de cambios en la cola.

**Cuándo ejecutar**: Una sola vez, al implementar las notificaciones en tiempo real.

```bash
python migrations/agregar_updatequeue.py
```

---

## Orden de Ejecución Recomendado (instalación nueva)

```
1. alembic upgrade head           # Migraciones automáticas
2. migrate_db.py                  # Migración base
3. apply_migration.py             # Esquema general
4. apply_migration_cuentas.py     # Módulo de cuentas
5. apply_approved_at_migration.py # Campo approved_at
6. apply_costo_migration.py       # Campo costo en productos
7. apply_despachado_migration.py  # Campo despachado en consumos
8. add_ganancias_functions.py     # Módulo de ganancias
9. add_is_karaoke_migration.py    # Campo is_karaoke en mesas
10. agregar_updatequeue.py        # WebSocket update_queue
```
