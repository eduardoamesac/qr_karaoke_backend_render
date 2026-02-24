# ================================================================
# 🎵 CONFIGURAR LARAGON EN TU APLICACIÓN
# ================================================================
# Este script configura automáticamente tu app para usar Laragon

param(
    [switch]$CreateEnvFile,
    [string]$LaragonPort = "3306",
    [string]$MySQLUser = "root",
    [string]$MySQLPassword = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n=== CONFIGURAR LARAGON EN QR KARAOKE ===" -ForegroundColor Green

# Paso 1: Crear .env para Laragon
if ($CreateEnvFile) {
    Write-Host "`n[1/2] Creando archivo .env para Laragon..." -ForegroundColor Green
    
    $envContent = @"
# 🎵 CONFIGURACIÓN LARAGON - QR KARAOKE

# BASE DE DATOS - LARAGON HS
DB_HOST=127.0.0.1
DB_USER=$MySQLUser
DB_PASSWORD=$MySQLPassword
DB_NAME=mi_base_datos
DB_PORT=$LaragonPort

# AMBIENTE
ENVIRONMENT=development

# POOL DE CONEXIONES
POOL_SIZE=10
MAX_OVERFLOW=20

# KARAOKE SETTINGS
KARAOKE_CIERRE=02:00

# ========================================
# ✓ CONFIGURADO PARA LARAGON
# ========================================
"@

    $envContent | Out-File -FilePath "$projectRoot\.env" -Encoding UTF8
    Write-Host "✓ Archivo .env creado exitosamente" -ForegroundColor Green
}

# Paso 2: Verificar conexión
Write-Host "`n[2/2] Verificando conexión a Laragon..." -ForegroundColor Green

try {
    # Importar configuración
    $pythonScript = @"
import sys
sys.path.insert(0, '$projectRoot')
from database_config import engine

try:
    conn = engine.connect()
    result = conn.execute("SELECT @@version AS version;")
    row = result.fetchone()
    print(f"✓ Conectado a Laragon MySQL (versión {row[0]})")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"✗ Error: {str(e)}")
    sys.exit(1)
"@

    $pythonScript | python
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=== ✓ LARAGON CONFIGURADO EXITOSAMENTE ===" -ForegroundColor Green
        Write-Host "Tu aplicación está lista para usar Laragon" -ForegroundColor Green
    } else {
        Write-Host "`n✗ No se pudo conectar a Laragon" -ForegroundColor Red
        Write-Host "Verifica que Laragon esté corriendo" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "`n✗ Error de verificación:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

Write-Host ""
