# ========================================================================
# ⚠️  REVERSA DE MIGRACIÓN - VOLVER A MYSQL ORIGINAL
# ========================================================================
# Ejecuta esto si algo salió mal y necesitas volver atrás

param(
    [string]$SourceDB = "mi_base_datos",
    [string]$LaragonPort = "3306",
    [string]$OriginalPort = "3306",
    [string]$MySQLUser = "root",
    [string]$MySQLPassword = ""
)

$ErrorActionPreference = "Stop"

$green = [System.ConsoleColor]::Green
$yellow = [System.ConsoleColor]::Yellow
$red = [System.ConsoleColor]::Red
$cyan = [System.ConsoleColor]::Cyan

Print-Host "`n" -ForegroundColor $cyan
Print-Host ("=" * 70) -ForegroundColor $cyan
Print-Host "⚠️  REVERSA DE MIGRACIÓN - LARAGON → MYSQL ORIGINAL" -ForegroundColor $red
Print-Host ("=" * 70) -ForegroundColor $cyan

$confirm = Read-Host "`n¿Estás seguro? Esto borrará la BD original. (s/n)"

if ($confirm -ne 's' -and $confirm -ne 'S') {
    Write-Host "Cancelado." -ForegroundColor $yellow
    exit 0
}

try {
    # Paso 1: Exportar desde Laragon
    Write-Host "`n[1/2] Exportando desde Laragon..." -ForegroundColor $green
    
    $dumpFile = "$env:TEMP\${SourceDB}_revert_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
    
    $mysqldumpArgs = @(
        "-h", "127.0.0.1",
        "-u", $MySQLUser,
        "-P", $LaragonPort,
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
    Write-Host "✓ Dump creado" -ForegroundColor $green
    
    # Paso 2: Recrear BD original
    Write-Host "`n[2/2] Reimportando en MySQL original..." -ForegroundColor $green
    
    $mysqlArgs = @(
        "-h", "localhost",
        "-u", $MySQLUser,
        "-P", $OriginalPort,
        "-e", "DROP DATABASE IF EXISTS $SourceDB; CREATE DATABASE $SourceDB;"
    )
    
    if ($MySQLPassword) {
        $mysqlArgs += "-p$MySQLPassword"
    }
    
    & mysql @mysqlArgs
    
    $importContent = Get-Content $dumpFile -Raw
    
    $mysqlArgs = @(
        "-h", "localhost",
        "-u", $MySQLUser,
        "-P", $OriginalPort,
        $SourceDB
    )
    
    if ($MySQLPassword) {
        $mysqlArgs += "-p$MySQLPassword"
    }
    
    $importContent | & mysql @mysqlArgs
    
    Write-Host "✓ BD restaurada en MySQL original" -ForegroundColor $green
    
    # Paso 3: Actualizar .env
    Write-Host "`n[3/3] Actualizando configuración..." -ForegroundColor $green
    
    $envFile = ".env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile -Raw
        $envContent = $envContent -replace 'DB_HOST=.*', 'DB_HOST=localhost'
        $envContent = $envContent -replace 'DB_PORT=.*', "DB_PORT=$OriginalPort"
        $envContent | Out-File -FilePath $envFile -Encoding UTF8
        Write-Host "✓ .env actualizado" -ForegroundColor $green
    }
    
    Write-Host "`n=== ✓ REVERSA COMPLETADA ===" -ForegroundColor $green
    Write-Host "Tu BD está nuevamente en MySQL original (localhost:$OriginalPort)" -ForegroundColor $green
    Write-Host "`nArchivo de backup guardado: $dumpFile" -ForegroundColor $yellow
}
catch {
    Write-Host "`n✗ Error: $($_.Exception.Message)" -ForegroundColor $red
    exit 1
}
