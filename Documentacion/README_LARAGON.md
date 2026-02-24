# 🎵 MIGRACIÓN DE BASE DE DATOS A LARAGON

## 📋 RESUMEN RÁPIDO

Tu base de datos `mi_base_datos` que está en **MySQL local** será migrada a **Laragon HS**.

```
❌ ANTES:          ✅ DESPUÉS:
localhost:3306 → 127.0.0.1:3306 (Laragon)
```

---

## ⚡ OPCIÓN 1: MIGRACIÓN AUTOMÁTICA (Recomendado)

### Paso 1: Preparativos
1. Abre **Laragon Dashboard**
2. Asegúrate que **HS (MySQL)** esté corriendo (verde ✓)
3. Abre **PowerShell como Administrador**
4. Navega a tu proyecto:
```powershell
cd C:\Users\MARCO_MESA\Documents\qr_karaoke_backend_render
```

### Paso 2: Ejecutar migración
```powershell
.\migrate_complete.ps1
```

**Eso es todo.** El script hará:
- ✓ Exportar tu BD actual
- ✓ Crearla en Laragon
- ✓ Importar todos los datos
- ✓ Configurar tu `.env`
- ✓ Verificar que todo funcione

### Paso 3: ¡Listo!
Tu aplicación ahora usa Laragon. Inicia normalmente:
```powershell
python main.py
```

---

## 🔧 OPCIÓN 2: MIGRACIÓN MANUAL (Si tienes problemas)

### Paso 1: Exportar base de datos actual
```powershell
.\migrate_to_laragon.ps1
```

### Paso 2: Configurar .env
Copia o edita `.env` en tu proyecto:
```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=mi_base_datos
DB_PORT=3306
ENVIRONMENT=development
```

### Paso 3: Verificar conexión
```powershell
python -c "from database_config import engine; print('✓ Conectado')"
```

---

## 🚨 TROUBLESHOOTING

### ❌ "mysqldump no reconocido"
**Solución:** Agrega MySQL al PATH de Windows
1. Abre `System Properties` → `Environment Variables`
2. Busca `PATH` en System variables
3. Agrega: `C:\Program Files\MySQL\MySQL Server 8.0\bin`
4. Reinicia PowerShell

### ❌ "Acceso denegado"
**Verifica:**
- ¿Usuario MySQL es `root`? → Usa `-MySQLUser "root"`
- ¿Tiene contraseña? → Usa `-MySQLPassword "tu_password"`
- ¿Puerto es 3306? → Verifica en Laragon Dashboard

### ❌ "Puerto 3306 en uso"
**Solución:** Laragon está usando otro puerto
1. Abre Laragon Dashboard
2. Haz clic en MySQL → Settings
3. Mira el puerto alojado
4. Corre: `.\migrate_complete.ps1 -TargetPort "3307"`

### ❌ Laragon MySQL no inicia
**Solución:**
1. Cierra Laragon completamente
2. Abre Laragon nuevamente
3. Si sigue sin funcionar: `Laragon` → `Tools` → `MySQL` → `Reinstall MySQL`

---

## ⏮️  REVERTIR A MYSQL ORIGINAL (Si cambias de idea)

```powershell
.\migrate_revert.ps1
```

Esto restaurará tu BD al MySQL original (localhost:3306).

---

## 📊 ARCHIVOS GENERADOS

```
migrate_complete.ps1       ← Script principal de migración
migrate_to_laragon.ps1     ← Solo exportar/importar
migrate_revert.ps1         ← Volver atrás si algo sale mal
setup_laragon.ps1          ← Solo configurar app para Laragon
.env                       ← Configuración (creado automáticamente)
MIGRACION_LARAGON.txt      ← Instrucciones detalladas
```

---

## ✅ VERIFICACIÓN FINAL

Si todo está bien, verás:
```
✓ Conectado a Laragon MySQL (versión 8.0.xx)
```

En tu terminal:
```powershell
# Activar venv
.\venv\Scripts\Activate.ps1

# Iniciar app
python main.py

# Verás: INFO:     Uvicorn running on http://localhost:8000
```

---

## 📞 SOPORTE

Si algo falla:
1. Lee el archivo `MIGRACION_LARAGON.txt` (más detallado)
2. Verifica que Laragon MySQL esté corriendo
3. Prueba revertir: `.\migrate_revert.ps1`
4. Ejecuta nuevamente: `.\migrate_complete.ps1`

---

**¡Listo! Tu app ahora usa Laragon. 🚀**
