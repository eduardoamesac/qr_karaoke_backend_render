# ========================================================================
# ðŸŽµ MIGRACION COMPLETA: MYSQL â†’ LARAGON (SCRIPT MAESTRO)
# ========================================================================
# Ejecuta este script una sola vez para completar toda la migraciÃ³n

param(
    [string]$SourceDB = "mi_base_datos",
    [string]$TargetPort = "3306",
    [string]$MySQLUser = "root",
    [string]$MySQLPassword = "",
    [switch]$SkipDump = $false,
    [switch]$SkipSetup = $false
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = $MyInvocation.MyCommand.Path

# Colores
$green = [System.ConsoleColor]::Green
$yellow = [System.ConsoleColor]::Yellow
$red = [System.ConsoleColor]::Red
$cyan = [System.ConsoleColor]::Cyan

# ========================================================================
# FUNCIONES AUXILIARES
# ========================================================================

function Print-Header {
    param([string]$title)
    Write-Host "`n" -ForegroundColor $cyan
    Write-Host ("=" * 70) -ForegroundColor $cyan
    Write-Host $title -ForegroundColor $cyan
    Write-Host ("=" * 70) -ForegroundColor $cyan
}

function Print-Step {
    param([string]$step, [string]$description)
    Write-Host "`n[$step] $description" -ForegroundColor $green
}

function Print-Success {
    param([string]$message)
    Write-Host "âœ“ $message" -ForegroundColor $green
}

function Print-Error {
    param([string]$message)
    Write-Host "âœ— $message" -ForegroundColor $red
}

function Print-Warning {
    param([string]$message)
    Write-Host "âš  $message" -ForegroundColor $yellow
}

# ========================================================================
# VALIDACIONES INICIALES
# ========================================================================

Print-Header "ðŸŽµ MIGRACIÃ“N MYSQL â†’ LARAGON - QR KARAOKE"

Write-Host "Validando requisitos..." -ForegroundColor $cyan

# Validar que mysqldump estÃ© disponible
try {
    $null = & mysqldump --version 2>$null
    Print-Success "mysqldump disponible"
} catch {
    Print-Error "mysqldump no encontrado. Agrega MySQL al PATH de Windows"
    Write-Host "`nAlternativa: Descarga MySQL Community Server o usa Laragon para MySQL" -ForegroundColor $yellow
    exit 1
}

# Validar que mysql estÃ© disponible
try {
    $null = & mysql --version 2>$null
    Print-Success "mysql CLI disponible"
} catch {
    Print-Error "mysql CLI no encontrado. Agrega MySQL al PATH"
    exit 1
}

# ========================================================================
# FASE 1: EXPORTAR BASE DE DATOS
# ========================================================================

if (-not $SkipDump) {
    Print-Step "1/3" "Exportando base de datos desde MySQL actual..."
    
    $dumpFile = "$env:TEMP\${SourceDB}_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
    
    try {
        Write-Host "Exportando a: $dumpFile" -ForegroundColor $cyan
        
        $mysqldumpArgs = @(
            "-h", "localhost",
            "-u", $MySQLUser,
            "-P", "3306",
            "--routines",
            "--triggers",
            "--column-statistics=0",
            "--result-file=$dumpFile",
            $SourceDB
        )
        
        if ($MySQLPassword) {
            $mysqldumpArgs += "-p$MySQLPassword"
        }
        
        & mysqldump @mysqldumpArgs
        
        if (-not (Test-Path $dumpFile)) {
            throw "El archivo dump no se creÃ³"
        }
        
        $fileSize = [math]::Round((Get-Item $dumpFile).Length / 1MB, 2)
        Print-Success "Dump exportado ($fileSize MB)"
        
        # Guardar ruta del dump
        $Script:DumpFile = $dumpFile
    }
    catch {
        Print-Error "Error al exportar: $($_.Exception.Message)"
        Write-Host "`nVerifica:" -ForegroundColor $yellow
        Write-Host "â€¢ Usuario MySQL correcto: $MySQLUser" -ForegroundColor $yellow
        Write-Host "â€¢ Base de datos existe: $SourceDB" -ForegroundColor $yellow
        Write-Host "â€¢ MySQL estÃ¡ corriendo en localhost:3306" -ForegroundColor $yellow
        exit 1
    }
} else {
    Print-Warning "Saltando exportaciÃ³n (--SkipDump)"
    $Script:DumpFile = Get-ChildItem "$env:TEMP\${SourceDB}_backup_*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
}

# ========================================================================
# FASE 2: CREAR BASE DE DATOS EN LARAGON
# ========================================================================

Print-Step "2/3" "Preparando base de datos en Laragon..."

try {
    Write-Host "Puerto Laragon: $TargetPort" -ForegroundColor $cyan
    
    # Crear BD
    $mysqlArgs = @(
        "-h", "127.0.0.1",
        "-u", $MySQLUser,
        "-P", $TargetPort,
        "-e", "DROP DATABASE IF EXISTS $SourceDB; CREATE DATABASE $SourceDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )
    
    if ($MySQLPassword) {
        $mysqlArgs += "-p$MySQLPassword"
    }
    
    & mysql @mysqlArgs
    Print-Success "Base de datos creada en Laragon"
    
    # Importar dump
    Write-Host "`nImportando datos..." -ForegroundColor $cyan
    
    $importContent = Get-Content $Script:DumpFile -Raw
    
    $mysqlArgs = @(
        "-h", "127.0.0.1",
        "-u", $MySQLUser,
        "-P", $TargetPort,
        $SourceDB
    )
    
    if ($MySQLPassword) {
        $mysqlArgs += "-p$MySQLPassword"
    }
    
    $importContent | & mysql @mysqlArgs
    Print-Success "Datos importados a Laragon"
}
catch {
    Print-Error "Error al importar: $($_.Exception.Message)"
    Write-Host "`nVerifica:" -ForegroundColor $yellow
    Write-Host "â€¢ Laragon MySQL estÃ¡ corriendo" -ForegroundColor $yellow
    Write-Host "â€¢ Puerto es correcto: $TargetPort" -ForegroundColor $yellow
    Write-Host "â€¢ Credenciales MySQL: $MySQLUser" -ForegroundColor $yellow
    exit 1
}

# ========================================================================
# FASE 3: CONFIGURAR APLICACIÃ“N
# ========================================================================

if (-not $SkipSetup) {
    Print-Step "3/3" "Configurando aplicaciÃ³n para Laragon..."
    
    # Crear .env si no existe
    $envFile = "$projectRoot\.env"
    
    if (Test-Path $envFile) {
        Print-Warning ".env ya existe, actualizando..."
        
        # Actualizar valores clave
        $envContent = Get-Content $envFile -Raw
        $envContent = $envContent -replace 'DB_HOST=.*', 'DB_HOST=127.0.0.1'
        $envContent = $envContent -replace 'DB_PORT=.*', "DB_PORT=$TargetPort"
        $envContent = $envContent -replace 'DB_USER=.*', "DB_USER=$MySQLUser"
        
        if ($MySQLPassword) {
            $envContent = $envContent -replace 'DB_PASSWORD=.*', "DB_PASSWORD=$MySQLPassword"
        }
        
        $envContent | Out-File -FilePath $envFile -Encoding UTF8
        Print-Success ".env actualizado"
    } else {
        Write-Host "Creando .env..." -ForegroundColor $cyan
        
        $envContent = @"
# ðŸŽµ CONFIGURACIÃ“N LARAGON - QR KARAOKE

# BASE DE DATOS - LARAGON HS
DB_HOST=127.0.0.1
DB_USER=$MySQLUser
DB_PASSWORD=$MySQLPassword
DB_NAME=$SourceDB
DB_PORT=$TargetPort

# AMBIENTE
ENVIRONMENT=development

# POOL DE CONEXIONES
POOL_SIZE=10
MAX_OVERFLOW=20

# KARAOKE SETTINGS
KARAOKE_CIERRE=02:00
"@

        $envContent | Out-File -FilePath $envFile -Encoding UTF8
        Print-Success ".env creado"
    }
}

# ========================================================================
# VERIFICACIÃ“N FINAL
# ========================================================================

Print-Step "VerificaciÃ³n" "Probando conexiÃ³n a Laragon..."

try {
    $testScript = @"
import sys
sys.path.insert(0, '$projectRoot')
from dotenv import load_dotenv
load_dotenv()
from database_config import engine

try:
    with engine.connect() as conn:
        result = conn.execute("SELECT COUNT(*) as table_count FROM information_schema.TABLES WHERE TABLE_SCHEMA='$SourceDB';")
        count = result.scalar()
        print(f'âœ“ ConexiÃ³n exitosa. {count} tablas encontradas.')
        sys.exit(0)
except Exception as e:
    print(f'âœ— Error: {str(e)}')
    sys.exit(1)
"@

    $testScript | python
    
    if ($LASTEXITCODE -eq 0) {
        Print-Success "Base de datos verificada y accesible"
    } else {
        Print-Error "No se pudo verificar la conexiÃ³n"
        exit 1
    }
}
catch {
    Print-Warning "No se pudo ejecutar verificaciÃ³n: $($_.Exception.Message)"
}

# ========================================================================
# RESUMEN FINAL
# ========================================================================

Print-Header "âœ“ MIGRACIÃ“N COMPLETADA EXITOSAMENTE"

Write-Host "`nðŸ“Š RESUMEN:" -ForegroundColor $green
Write-Host "  â€¢ Base de datos: $SourceDB" -ForegroundColor $cyan
Write-Host "  â€¢ UbicaciÃ³n: Laragon (127.0.0.1:$TargetPort)" -ForegroundColor $cyan
Write-Host "  â€¢ Archivo .env: Configurado" -ForegroundColor $cyan
Write-Host "`nðŸ“ PRÃ“XIMOS PASOS:" -ForegroundColor $green
Write-Host "  1. Abre terminal PowerShell" -ForegroundColor $cyan
Write-Host "  2. Navega a: $projectRoot" -ForegroundColor $cyan
Write-Host "  3. Ejecuta tu venv: .\.venv\Scripts\Activate.ps1" -ForegroundColor $cyan
Write-Host "  4. Inicia la app: python main.py" -ForegroundColor $cyan

Write-Host "`nðŸŽµ Â¡Tu aplicaciÃ³n ya estÃ¡ usando Laragon!`n" -ForegroundColor $green
