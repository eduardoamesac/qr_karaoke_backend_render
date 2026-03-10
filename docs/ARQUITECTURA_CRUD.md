# Arquitectura CRUD — QR Karaoke Backend

## 1. Por qué se reorganizó el código

El archivo `crud.py` original creció de forma orgánica hasta convertirse en un monolito de más de 1 400 líneas con responsabilidades mezcladas: mesas, usuarios, canciones, productos, consumos y administración, todo en un único archivo. Esto dificultaba:

- **Lectura y navegación**: encontrar una función requería desplazarse por cientos de líneas.
- **Mantenimiento**: un cambio en lógica de pagos podía afectar accidentalmente código de canciones.
- **Colaboración**: múltiples desarrolladores editando el mismo archivo generaba conflictos.
- **Testing**: imposible probar un dominio de forma aislada.
- **Funciones duplicadas**: el archivo contenía definiciones duplicadas que Python resolvía implícitamente usando solo la última, generando confusión.

La reorganización separa cada dominio de negocio en su propio módulo, manteniendo el `crud.py` raíz **intacto** para garantizar compatibilidad con Render.com.

---

## 2. Nueva estructura de carpetas

```
qr_karaoke_backend_render/
├── main.py                        # Entry point FastAPI (sin modificar)
├── crud.py                        # INTACTO — compatibilidad con Render
├── models.py                      # Modelos SQLAlchemy (sin modificar)
├── schemas.py                     # Schemas Pydantic (sin modificar)
├── database.py                    # Conexión a BD (sin modificar)
├── timezone_utils.py              # Utilidad de zona horaria (sin modificar)
├── cache_manager.py               # Cache JSON en memoria (sin modificar)
├── queue_manager.py               # Gestor de cola de reproducción (sin modificar)
├── app/
│   ├── __init__.py                # Paquete app
│   └── crud/
│       ├── __init__.py            # Re-exporta todo para compatibilidad
│       ├── crud_mesas.py          # Mesas + Pagos
│       ├── crud_usuarios.py       # Usuarios + Ranking + Estadísticas
│       ├── crud_canciones.py      # Cola karaoke + algoritmo de cola
│       ├── crud_productos.py      # Inventario / catálogo
│       ├── crud_consumos.py       # Pedidos + Reportes financieros
│       └── crud_admin.py          # API Keys + Reset de noche
└── docs/
    └── ARQUITECTURA_CRUD.md       # Este documento
```

---

## 3. Tabla completa de funciones por módulo

### `app/crud/crud_mesas.py` — Mesas y Pagos

| Función | Descripción |
|---|---|
| `get_mesa_by_qr` | Busca una mesa por su código QR (CACHE) |
| `get_mesa_by_id` | Obtiene una mesa por ID (CACHE) |
| `get_mesas` | Devuelve todas las mesas (CACHE) |
| `create_mesa` | Crea una nueva mesa en el CACHE |
| `set_mesa_active_status` | Activa/desactiva una mesa (CACHE) |
| `delete_mesa` | Elimina una mesa del CACHE |
| `get_mesas_vacias` | Mesas sin usuarios conectados |
| `get_table_payment_status` | Estado de cuenta detallado de una mesa |
| `get_all_tables_payment_status` | Estado de cuenta de todas las mesas activas |
| `create_pago` | Registra un pago en BD |
| `get_pagos` | Obtiene todos los pagos en BD |
| `get_pagos_mesa` | Pagos de una mesa específica |

### `app/crud/crud_usuarios.py` — Usuarios y Ranking

| Función | Descripción |
|---|---|
| `get_usuario_by_id` | Busca un usuario por ID |
| `get_usuario_by_nick` | Busca un usuario por nick (case-insensitive) |
| `create_usuario` | Crea un usuario en BD |
| `create_usuario_en_mesa` | Crea un usuario asociado a una mesa |
| `get_o_crear_usuario_admin_para_mesa` | Obtiene/crea el usuario admin de una mesa |
| `get_all_usuarios` | Obtiene todos los usuarios |
| `update_usuario` | Actualiza campos de un usuario |
| `delete_usuario` | Elimina un usuario de BD |
| `get_or_create_dj_user` | Obtiene/crea el usuario DJ global |
| `get_total_consumido_por_usuario` | Total consumido por un usuario (CACHE) |
| `get_ranking_usuarios` | Ranking global por puntos |
| `get_usuarios_sin_consumo` | Usuarios sin ningún consumo |
| `get_usuarios_una_cancion` | Usuarios que cantaron exactamente una canción |
| `get_usuarios_inactivos_consumo` | Usuarios sin consumo en las últimas N horas |
| `get_usuarios_consumen_pero_no_cantan` | Usuarios que consumen pero no cantan |
| `get_usuarios_mas_rechazados` | Usuarios con más canciones rechazadas |

### `app/crud/crud_canciones.py` — Cola de Karaoke

| Función | Descripción |
|---|---|
| `create_cancion_para_usuario` | Añade una canción al CACHE para un usuario |
| `get_cancion_by_id` | Obtiene una canción por ID (CACHE) |
| `get_canciones_por_usuario` | Canciones de un usuario (CACHE) |
| `get_cancion_reproduciendo` | Canción actualmente reproduciéndose |
| `get_all_canciones` | Todas las canciones en CACHE |
| `get_canciones_pendientes` | Canciones pendientes de aprobación |
| `update_cancion_estado` | Actualiza el estado de una canción |
| `check_if_song_in_user_list` | Verifica si una canción ya fue añadida |
| `get_available_song_credits` | Créditos disponibles de un usuario |
| `get_user_credits_detail` | Detalle de créditos del usuario |
| `consume_song_credit` | Consume un crédito de canción |
| `get_duracion_total_cola_aprobada` | Duración total de la cola aprobada |
| `start_next_song_if_autoplay_and_idle` | Inicia siguiente canción si autoplay activo |
| `check_and_approve_next_lazy_song` | Aprueba la siguiente canción lazy si aplica |
| `avanzar_cola_automaticamente` | Avanza la cola (async, marca cantada + inicia siguiente) |
| `get_cola_lazy` | Cola pendiente_lazy ordenada |
| `aprobar_siguiente_cancion_lazy` | Aprueba la primera canción en cola lazy |
| `get_cola_completa_con_lazy` | Cola completa agrupada por estado |
| `move_lazy_song_up` | Sube una canción lazy (verifica pertenencia) |
| `move_lazy_song_down` | Baja una canción lazy (verifica pertenencia) |
| `enriquecer_cancion` | Añade datos del usuario a una canción del CACHE |
| `get_cola_completa` | Cola básica (now_playing + upcoming) |
| `get_canciones_mas_cantadas` | Top canciones más cantadas |
| `get_canciones_mas_rechazadas` | Top canciones más rechazadas |
| `get_canciones_cantadas_por_usuario` | Canciones cantadas por usuario |
| `get_canciones_cantadas_por_mesa` | Canciones cantadas por mesa |
| `get_actividad_por_hora` | Actividad por hora del día |
| `get_tiempo_promedio_espera` | Tiempo promedio de espera en cola |
| `get_canciones_mas_pedidas_por_mesa` | Canciones más pedidas en una mesa |

### `app/crud/crud_productos.py` — Inventario

| Función | Descripción |
|---|---|
| `get_producto_by_id` | Obtiene un producto por ID |
| `get_producto_by_nombre` | Obtiene un producto por nombre |
| `get_all_productos` | Todos los productos activos |
| `get_productos` | Productos con paginación (sin filtro is_active) |
| `create_producto` | Crea un nuevo producto |
| `update_producto` | Actualiza un producto |
| `delete_producto` | Elimina o desactiva un producto |
| `update_producto_valor` | Actualiza el precio de un producto |
| `update_producto_active_status` | Activa/desactiva un producto |
| `get_productos_mas_consumidos` | Top productos más consumidos |
| `get_productos_menos_consumidos` | Productos menos consumidos |
| `get_productos_no_consumidos` | Productos sin ningún consumo |
| `get_productos_mas_consumidos_por_mesa` | Productos más consumidos en una mesa |

### `app/crud/crud_consumos.py` — Pedidos y Reportes

| Función | Descripción |
|---|---|
| `get_consumos_mesa` | Consumos de una mesa (CACHE) |
| `create_consumo_para_usuario` | Crea un consumo, descuenta stock y otorga créditos |
| `create_pedido_from_carrito` | Crea múltiples consumos desde un carrito |
| `get_recent_consumos` | Consumos recientes enriquecidos con nombres |
| `delete_consumo` | Elimina consumo, restaura stock y créditos |
| `update_consumo_cantidad` | Cambia la cantidad de un consumo |
| `get_total_ingresos` | Total de ingresos de la noche |
| `get_ganancias_totales` | Ganancias reales (ventas - costos) |
| `get_ingresos_por_mesa` | Ingresos agrupados por mesa |
| `get_ingresos_por_categoria` | Ingresos por categoría de producto |
| `get_ingresos_promedio_por_usuario` | Promedio de ingresos por usuario |
| `get_ingresos_promedio_por_usuario_por_mesa` | Promedio de ingresos por usuario por mesa |
| `get_usuarios_mayor_gasto_por_categoria` | Usuarios con mayor gasto por categoría |
| `get_top_consumers_one_song` | Mayores consumidores con solo una canción |
| `get_resumen_noche` | Resumen completo de la noche |
| `get_categorias_mas_consumidas_por_mesa` | Categorías más consumidas en una mesa |

### `app/crud/crud_admin.py` — Administración

| Función | Descripción |
|---|---|
| `create_admin_api_key` | Genera y almacena una nueva API key |
| `get_admin_api_key` | Verifica si una API key es válida |
| `get_all_admin_api_keys` | Lista todas las API keys |
| `deactivate_admin_api_key` | Desactiva una API key (sin eliminar) |
| `delete_admin_api_key` | Elimina una API key permanentemente |
| `reset_database_for_new_night` | Reset completo para nueva noche |
| `limpiar_datos_prueba` | Limpia datos (solo desarrollo) |

---

## 4. Cómo importar

### Desde los módulos nuevos (recomendado para código futuro)

```python
# Importar solo lo necesario del módulo específico
from app.crud.crud_mesas import get_mesa_by_qr, create_mesa
from app.crud.crud_usuarios import get_usuario_by_id, get_ranking_usuarios
from app.crud.crud_canciones import avanzar_cola_automaticamente, get_cola_completa_con_lazy
from app.crud.crud_productos import get_productos, create_producto
from app.crud.crud_consumos import create_consumo_para_usuario, get_resumen_noche
from app.crud.crud_admin import create_admin_api_key, reset_database_for_new_night
```

### Desde `app.crud` (re-exporta todo el dominio)

```python
from app.crud import get_mesa_by_qr, avanzar_cola_automaticamente
# o importar el módulo completo
import app.crud as crud
crud.get_mesa_by_qr(db, qr_code)
```

### Desde el `crud.py` raíz (compatibilidad — código existente no cambia)

```python
import crud
crud.get_mesa_by_qr(db, qr_code)
crud.avanzar_cola_automaticamente(db)
```

---

## 5. Notas sobre compatibilidad hacia atrás

- El archivo `crud.py` en la **raíz del proyecto permanece intacto**. Render.com y todo el código existente (`main.py`, routers, etc.) continúan funcionando sin cambios.
- Los módulos en `app/crud/` son una **copia organizada** del código existente, no un reemplazo.
- El `app/crud/__init__.py` re-exporta todo con `from app.crud.crud_X import *`, de forma que `from app.crud import función` es equivalente a `from crud import función`.
- Las funciones con **definiciones duplicadas** en el `crud.py` original fueron incluidas en los módulos nuevos con una sola definición (la versión más reciente y completa):
  - `get_cola_lazy`: se usa la segunda definición (con mejor ordenamiento).

---

## 6. Próximos pasos (Fase 3)

Una vez que los módulos estén validados en producción:

1. **Mover `models.py`** a `app/models/models.py` y actualizar imports con `from app.models import models`.
2. **Mover `schemas.py`** a `app/schemas/schemas.py`.
3. **Mover routers** (`mesas.py`, `canciones.py`, etc.) a `app/api/`.
4. **Actualizar `main.py`** para usar los nuevos paths de import.
5. **Retirar `crud.py` raíz** (solo cuando todos los imports hayan migrado).
6. **Añadir tests unitarios por módulo** aprovechando la separación de responsabilidades.
