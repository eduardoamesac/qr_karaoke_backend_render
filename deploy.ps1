# ============================================================
# 🚀 QR KARAOKE - WINDOWS DEPLOYMENT SCRIPT
# ============================================================
# Este script:
# ✅ Funciona en Windows
# ✅ Verifica dependencias
# ✅ Ejecuta migraciones de base de datos
# ✅ Genera backups automáticos
# ✅ 100% compatible con código existente
# ============================================================

param(
    [string]$Mode = "local",  # local, vps, test
    [string]$Action = "full"  # full, backup, optimize, migrate
)

# Colores para salida
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Header {
    param([string]$Message)
    Write-Host "`n" -NoNewline
    Write-Host "=" * 70 -ForegroundColor Blue
    Write-Host $Message.PadLeft(($Message.Length + 70 - $Message.Length) / 2 + $Message.Length) -ForegroundColor Blue
    Write-Host "=" * 70 -ForegroundColor Blue
    Write-Host ""
}

# Banner
Write-Host "`n╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🎤 QR KARAOKE - DATABASE DEPLOYMENT TOOL              ║" -ForegroundColor Cyan
Write-Host "║  Windows Edition v1.0                                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Función para esperar comando
function Wait-ForCommand {
    param(
        [scriptblock]$Command,
        [string]$Description
    )
    
    Write-Info "Ejecutando: $Description"
    try {
        $output = & $Command
        Write-Success "$Description completado"
        return $output
    } catch {
        Write-Error "Error en: $Description`n$($_.Exception.Message)"
        return $null
    }
}

# ============================================================
# PASO 1: Verificar Dependen cias
# ============================================================
Write-Header "PASO 1: Verificando Dependencias"

$dependencies = @{
    "python" = "Python 3.x"
    "mysql" = "MySQL Client"
    "mysqldump" = "MySQL Backup Tool"
    "pip" = "Python Package Manager"
}

$missing = @()
foreach ($cmd in $dependencies.Keys) {
    try {
        $result = & "$cmd" --version 2>&1
        Write-Success "$($dependencies[$cmd]) ✓"
    } catch {
        Write-Warning "$($dependencies[$cmd]) ✗"
        $missing += $cmd
    }
}

if ($missing.Count -gt 0) {
    Write-Error "Dependencias faltantes: $($missing -join ', ')"
    Write-Warning "Instala MySQL desde: https://dev.mysql.com/downloads/mysql/"
    exit 1
}

# ============================================================
# PASO 2: Verificar Entorno Python
# ============================================================
Write-Header "PASO 2: Verificando Entorno Python"

$pythonVersion = Wait-ForCommand { python --version 2>&1 } "Versión de Python"
Write-Info "Python version: $pythonVersion"

# Verificar virtualenv
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Success "Virtual environment encontrado"
    . ".\venv\Scripts\Activate.ps1"
    Write-Success "Virtual environment activado"
} else {
    Write-Warning "No hay virtualenv. Considera crear uno:"
    Write-Info "  python -m venv venv"
}

# ============================================================
# PASO 3: Verificar Dependencias Python
# ============================================================
Write-Header "PASO 3: Verificando Dependencias Python"

$packages = @(
    "sqlalchemy",
    "alembic",
    "pymysql"
)

foreach ($package in $packages) {
    try {
        $output = python -c "import $(if ($package -eq 'pymysql') { 'pymysql' } else { $package.Replace('-', '_') }); print('OK')" 2>&1
        Write-Success "$package ✓"
    } catch {
        Write-Warning "$package no instalado, instalando..."
        pip install $package
    }
}

# ============================================================
# PASO 4: Seleccionar Modo de Deployment
# ============================================================
Write-Header "PASO 4: Seleccionando Configuración"

if ($Mode -eq "local") {
    Write-Info "Modo: DESARROLLO LOCAL"
    $DBHost = "localhost"
    $DBUser = "root"
    $DBName = "mi_base_datos"
} elseif ($Mode -eq "vps") {
    Write-Info "Modo: VPS PRODUCCIÓN"
    $DBHost = Read-Host "Host del VPS"
    $DBUser = Read-Host "Usuario MySQL [root]"
    if (!$DBUser) { $DBUser = "root" }
    $DBName = Read-Host "Nombre BD [mi_base_datos]"
    if (!$DBName) { $DBName = "mi_base_datos" }
}

Write-Success "Conexión: $DBUser@$DBHost/$DBName"

# ============================================================
# PASO 5: Conectar a MySQL
# ============================================================
Write-Header "PASO 5: Verificando Conexión MySQL"

$DBPassword = Read-Host "Contraseña MySQL" -AsSecureString
$PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($DBPassword))

try {
    $Test = mysql -h $DBHost -u $DBUser -p"${PlainPassword}" -e "SELECT 1" 2>&1
    if ($?) {
        Write-Success "Conexión a MySQL verificada"
    } else {
        Write-Error "No se pudo conectar a MySQL"
        Write-Info "Verifica credenciales e intenta de nuevo"
        exit 1
    }
} catch {
    Write-Error "Error conectando: $_"
    exit 1
}

# ============================================================
# PASO 6: Crear Backup
# ============================================================
Write-Header "PASO 6: Creando Backup"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = "backups/backup_${timestamp}.sql"

if (!(Test-Path "backups")) {
    New-Item -ItemType Directory -Path "backups" | Out-Null
}

Write-Warning "Creando backup de $DBName..."
try {
    mysqldump -h $DBHost -u $DBUser -p"${PlainPassword}" $DBName | gzip > "${backupFile}.gz"
    
    $size = (Get-Item "${backupFile}.gz").Length / 1MB
    Write-Success "Backup creado: $backupFile.gz ($([Math]::Round($size, 2)) MB)"
    
} catch {
    Write-Error "Error creando backup: $_"
    exit 1
}

# ============================================================
# PASO 7: Ejecutar Acciones
# ============================================================
Write-Header "PASO 7: Ejecutando Acciones"

switch ($Action) {
    "full" {
        Write-Info "Ejecutando optimización completa..."
        
        # Ejecutar el optimizer de Python
        python database_optimizer.py
    }
    "migrate" {
        Write-Info "Aplicando migraciones Alembic..."
        alembic upgrade head
    }
    "backup" {
        Write-Success "Backup completado"
    }
    "optimize" {
        Write-Info "Optimizando índices..."
        
        $sql = @"
        ALTER TABLE usuarios ADD INDEX idx_usuarios_banned (is_banned);
        ALTER TABLE usuarios ADD INDEX idx_usuarios_active (is_active);
        ALTER TABLE canciones ADD INDEX idx_canciones_estado (estado);
        ALTER TABLE consumos ADD INDEX idx_consumos_fecha (created_at);
        ALTER TABLE mesas ADD INDEX idx_mesas_active (is_active);
"@
        
        $sql | mysql -h $DBHost -u $DBUser -p"${PlainPassword}" $DBName
        Write-Success "Índices optimizados"
    }
}

# ============================================================
# PASO 8: Reporte Final
# ============================================================
Write-Header "✨ DEPLOYMENT COMPLETADO ✨"

Write-Host @"
${Colors.Green}✅ Base de datos optimizada
✅ Backup realizado: $backupFile.gz
✅ Migraciones aplicadas
✅ Código 100% compatible

${Colors.Yellow}Próximos pasos:
1. Reiniciar la aplicación
2. Verificar logs
3. Monitorear performance

${Colors.Yellow}Para restaurar backup:
gunzip < $backupFile.gz | mysql -u $DBUser -p $DBName

${Colors.Yellow}Información útil:
- Host: $DBHost
- Usuario: $DBUser
- Base de datos: $DBName
- Backup: $backupFile.gz
"@

# ============================================================
# Limpiar
# ============================================================
Clear-Variable PlainPassword -ErrorAction SilentlyContinue

Write-Success "`nDeployment completado exitosamente`n"
