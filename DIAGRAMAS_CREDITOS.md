# 📊 Diagramas del Sistema de Créditos

## 1️⃣ Flujo General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    USUARIO ENTRA A LA APP                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ✅ Se crea con 1 crédito
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │   ¿Quiere agregar una canción?      │
        └──────────────────────────────────────┘
                 │                     │
              SÍ │                     │ NO
                 │                     │
                 ▼                     ▼
        ┌──────────────────┐    ┌────────────────┐
        │¿Tiene créditos?  │    │Usa otro app    │
        └──────────────────┘    └────────────────┘
             │        │
          SÍ │        │ NO
             │        │
             ▼        ▼
        ┌─────────┐ ┌──────────────────────────┐
        │ ✅ Agrega│ │ ❌ Error 402:            │
        │canción  │ │ Debes hacer un pedido    │
        └─────────┘ └──────────────────────────┘
                           │
                    ¿Hace un pedido?
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │   Compra producto ($X pesos)        │
        └──────────────────────────────────────┘
                           │
                   ✅ Se asignan X créditos
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │  Créditos empiezan a decrecer       │
        │  -100 puntos cada minuto            │
        └──────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        Antes de 0              Llega a 0
              │                         │
              ▼                         ▼
    ✅ Puede agregar      ❌ Debe comprar
       más canciones         de nuevo
```

---

## 2️⃣ Máquina de Estados - Usuario

```
                        ┌─────────────────┐
                        │   USUARIO NUEVO │
                        └────────┬────────┘
                                 │
                        (song_credits = 1)
                                 │
                    ┌────────────▼────────────┐
                    │                         │
                    ▼                         ▼
            ┌───────────────┐        ┌──────────────┐
            │ CON CRÉDITOS  │        │ SIN CRÉDITOS │
            │ (>0)          │        │ (=0)         │
            └───────────────┘        └──────────────┘
                    │                        │
                    │ + 1 min                │
                    │ (decaimiento)          │ [está esperando]
                    │                        │
                    ▼                        ▼
            ┌───────────────┐        ┌──────────────┐
            │ CON MENOS     │───────▶│ SIN CRÉDITOS │
            │ CRÉDITOS      │        │ (expirado)   │
            └───────────────┘        └──────────────┘
                    │                        │
                    │                        │ [compra]
                    │                        │
            AGREGA CANCIÓN       ┌───────────▼────────┐
                    │            │    CON CRÉDITOS    │
                    │            │    (nuevo paquete) │
                    │            └────────────────────┘
                    │
                    ▼
            [CANCIÓN EN COLA]
```

---

## 3️⃣ Ciclo de Vida de un Crédito

```
CREACIÓN        DECAIMIENTO        CONSUMO         EXPIRACIÓN
    │               │                │                │
    ▼               ▼                ▼                ▼

┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────┐
│ Compra  │   │ Cada min │   │ Usuario      │   │ Crédito  │
│ $5,000  │──▶│ -100     │   │ agrega       │   │ = 0      │
│ pesos   │   │ puntos   │──▶│ canción      │──▶│ Expirado │
└─────────┘   └──────────┘   └──────────────┘   └──────────┘

Ejemplo Timeline:
┌────────────────────────────────────────────────────────────┐
│ Tiempo    │ Crédito │ Estado          │ Acción              │
├────────────────────────────────────────────────────────────┤
│ 9:00 AM   │ 5,000   │ ACTIVO          │ Se crean los crd    │
│ 9:01 AM   │ 4,900   │ ACTIVO          │ -100/min            │
│ 9:05 AM   │ 4,500   │ ACTIVO          │ Usuario agrega song │
│ 9:06 AM   │ 4,400   │ CONSUMIDO       │ marked consumed_at  │
│ 9:30 AM   │ 4,400   │ CONSUMIDO       │ (no decae si usados)│
│           │         │                 │                      │
│ 10:00 AM  │ 0       │ EXPIRADO        │ Llegó a cero         │
│ 10:01 AM  │ 0       │ EXPIRADO        │ marked expires_at    │
└────────────────────────────────────────────────────────────┘
```

---

## 4️⃣ Base de Datos - Relaciones

```
┌────────────────────┐
│   USUARIOS         │
├────────────────────┤
│ id (PK)            │
│ nick               │
│ mesa_id (FK)       │
│ puntos             │
│ nivel              │
│ song_credits ◄──┐  │◄─────────────┐
│ is_silenced      │  │               │
└────────────────────┘  │               │
       ▲                │               │
       │                │               │
       │        ┌────────────────────┐  │
       │        │ SONG_CREDITS (N)   │  │
       │        ├────────────────────┤  │
       │        │ id (PK)            │  │
       └────────┤ usuario_id (FK)◄──┘  │
                │ credits_value      │  │
                │ created_at         │  │
                │ expires_at         │  │
                │ consumed_at        │  │
                │ consumed_by_song_id├──┘
                └────────────────────┘
                         │
                         │ (FK)
                         │
                ┌────────▼──────────┐
                │   CANCIONES       │
                ├───────────────────┤
                │ id (PK)           │
                │ usuario_id (FK)   │
                │ youtube_id        │
                │ titulo            │
                │ estado            │
                │ duracion_seconds  │
                └───────────────────┘
```

---

## 5️⃣ Algoritmo de Cálculo de Créditos

```
FUNCIÓN: get_available_song_credits(usuario_id)

┌──────────────────────────────────────────────────────────────┐
│ 1. Obtener todos los créditos NO CONSUMIDOS del usuario     │
│    SELECT * FROM song_credits                               │
│    WHERE usuario_id = X                                     │
│    AND consumed_at IS NULL                                  │
│    AND consumed_by_song_id IS NULL                          │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Para CADA crédito:                                       │
│                                                              │
│    minutes_elapsed = (ahora - created_at) / 60              │
│    remaining = credits_value - (minutes_elapsed * 100)      │
│    remaining = MAX(0, remaining)                            │
│                                                              │
│ Ejemplo:                                                    │
│   - Crédito creado hace 5 minutos                           │
│   - Valor original: 5,000                                   │
│   - Decaimiento: 5 * 100 = 500                              │
│   - Valor actual: 5,000 - 500 = 4,500 ✓                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. SUMAR todos los créditos restantes                       │
│                                                              │
│    total = 0                                                │
│    FOR cada crédito:                                        │
│        IF remaining > 0:                                    │
│            total += remaining                               │
│        ELSE:                                                │
│            marcar como expirado                             │
│                                                              │
│ Resultado: total_credits                                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        [RETORNAR total]
```

**Ejemplo Visual:**

```
Usuario tiene 2 grupos de créditos:

Grupo 1: Compra hace 5 minutos ($5,000)
  Original: 5,000
  Decaimiento: 5 * 100 = 500
  Actual: 4,500 ✓

Grupo 2: Compra hace 50 minutos ($5,000)  
  Original: 5,000
  Decaimiento: 50 * 100 = 5,000
  Actual: 0 ❌ (EXPIRADO)

TOTAL DISPONIBLE: 4,500 + 0 = 4,500
```

---

## 6️⃣ Background Task - Ciclo de Trabajo

```
┌─────────────────────────────────────────────────┐
│  BACKGROUND TASK INICIADA (al startup)         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
         ┌──────────────────┐
         │ BUCLE INFINITO   │
         │ while True:      │
         └──────────┬───────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ Obtener TODOS los        │
         │ créditos no consumidos   │
         │ (cada 60 segundos)       │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ PARA CADA crédito:       │
         │                          │
         │ IF remaining == 0:       │
         │   SET expires_at = ahora │
         │   LOG: expirado          │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ COMMIT cambios a BD      │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ LOG: Task executed at X  │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │ await asyncio.sleep(60)  │
         │ (Esperar 60 segundos)    │
         └──────────┬───────────────┘
                    │
         [VOLVER AL INICIO]
         │
         └────────────────────┐
                              ▼
                        ┌──────────────┐
                        │ SIGUIENTE    │
                        │ ITERACIÓN    │
                        └──────────────┘
```

---

## 7️⃣ Validación de Agregar Canción

```
POST /api/v1/canciones/{usuario_id}

                    ┌─────────────────────┐
                    │ USUARIO SOLICITA    │
                    │ AGREGAR CANCIÓN     │
                    └────────────┬────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
    VALIDAR:            VALIDAR:               VALIDAR:
    Existe             No silenciado          ✨ CRÉDITOS
    usuario?           ?                      ✨ > 0 ?
         │                   │                       │
    SI  │                SI  │                   SI  │
         │                   │                       │
         ▼                   ▼                       ▼
    CONTINUAR    ────▶   CONTINUAR    ────▶   CONTINUAR
         │                   │                       │
    NO  │                NO  │                   NO  │
         │                   │                       │
         ▼                   ▼                       ▼
    ❌ 404           ❌ 403              ❌ 402 ◄──── NUEVO
    Usuario no        Silenciado        Sin créditos
    encontrado        (prohibido)        (Payment Required)
                                         Mensaje:
                                         "Debes hacer un
                                          pedido para..."
```

---

## 8️⃣ Diagrama de Estados de Créditos

```
                    [ANTES DE CREAR]
                          │
                          ▼
                    ┌──────────────┐
                    │ CREAR CRÉDITO│
                    │ created_at=now
                    │ credits_value=X
                    └──────────────┘
                          │
                          ▼
                    ┌──────────────────┐
        ┌──────────▶│ ACTIVO           │◀──────────┐
        │           │ remaining > 0    │           │
        │           └──────────────────┘           │
        │                   │                      │
        │                   │ Usuario agrega       │
        │                   │ canción              │
        │                   │                      │
        │                   ▼                      │
        │           ┌──────────────────┐           │
        └───────────┤ CONSUMIDO        │           │
                    │ consumed_at=now  │           │
                    │ consumed_by...=id│           │
                    └──────────────────┘   MÚLTIPLES
                                           CRÉDITOS
        ┌─────────────────────────┐       EM USO
        │                         │
        ▼                         ▼
    ┌──────────────┐      ┌──────────────────┐
    │ EXPIRADO     │      │ CONSUMIDO        │
    │ expires_at=  │      │ (sin expirarse)  │
    │ now          │      └──────────────────┘
    │ remaining=0  │
    └──────────────┘
```

---

## 9️⃣ Ejemplo Completo: Flujo de Marco

```
HORA    EVENTO                CRÉDITOS    BD CHANGES
────────────────────────────────────────────────────────────────

9:00    Marco entra             1        song_credits created:
        a la app                         id=1, value=1,
                                        created_at=9:00

9:00    Agrega canción #1       0        song_credits:
        "Bohemian Rhapsody"              id=1, consumed_at=9:00,
                                        consumed_by_song_id=1

9:00    Intenta agregar #2      0        ❌ Error 402
        "Another One"                    "Sin créditos"

9:05    Pide Cerveza            5000     song_credits created:
        ($5,000)                        id=2, value=5000,
                                        created_at=9:05

9:06    [Background task        4900     song_credits id=2:
         decrementa -100]                remaining=4900

9:15    Agrega canción #2       4000     song_credits:
        "Another One"                    id=2, consumed_at=9:15,
                                        consumed_by_song_id=2

9:55    [50 minutos después]    0        song_credits id=2:
        Créditos expiran                 expires_at=9:55

9:56    Intenta agregar #3      0        ❌ Error 402
        "Imagine"                        "Debes hacer pedido"

9:56    Pide otra Cerveza       5000     song_credits created:
        ($5,000)                        id=3, value=5000,
                                        created_at=9:56
```

---

**Diagramas actualizados: 04/02/2026** ✅
