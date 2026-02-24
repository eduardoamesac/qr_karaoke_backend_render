# ========================================================================
# SCRIPT MIGRACION DE BASE DE DATOS A LARAGON
# ========================================================================
# Este script exporta mi_base_datos y la importa en Laragon
# Requiere: mysqldump y mysql disponibles en PATH

param(
    [string]$SourceHost = "localhost",
    [string]$SourceUser = "root",
    [string]$SourcePassword = "",
    [string]$SourceDB = "mi_base_datos",
    [string]$SourcePort = "3306",
    [string]$TargetHost = "127.0.0.1",
    [string]$TargetUser = "root",
    [string]$TargetPassword = "",
    [string]$TargetPort = "3306"
)

$ErrorActionPreference = "Stop"

# Colores para output
$green = [System.ConsoleColor]::Green
$yellow = [System.ConsoleColor]::Yellow
$red = [System.ConsoleColor]::Red

Write-Host "`n=== MIGRACION DE BASE DE DATOS A LARAGON ===" -ForegroundColor $green
Write-Host "Origen: $SourceHost`:$SourcePort/$SourceDB" -ForegroundColor $yellow
Write-Host "Destino: $TargetHost`:$TargetPort/$SourceDB" -ForegroundColor $yellow

# Archivo dump temporal
$dumpFile = "$env:TEMP\mi_base_datos_dump.sql"

try {
    Write-Host "`n[1/3] Exportando base de datos desde $SourceHost..." -ForegroundColor $green
    
    $mysqldump = "mysqldump"
    $mysqldumpArgs = @(
        "-h", $SourceHost,
        "-u", $SourceUser,
        "-P", $SourcePort,
        "--routines",
        "--triggers",
        "--column-statistics=0",
        "--result-file=$dumpFile",
        $SourceDB
    )
    
    if ($SourcePassword) {
        $mysqldumpArgs += @("-p$SourcePassword")
    }
    
    & $mysqldump @mysqldumpArgs
    
    if (-not (Test-Path $dumpFile)) {
        throw "Error: El dump no se generó correctamente"
    }o correctamente"
    }
    
    $fileSize = (Get-Item $dumpFile).Length / 1MB
    Write-Host "[OK] Dump generado exitosamente ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor $greeos en Laragon..." -ForegroundColor $green
    
    $mysql = "mysql"
    $createDBSQL = "CREATE DATABASE IF NOT EXISTS $SourceDB;"
    $dropDBSQL = "DROP DATABASE IF EXISTS $SourceDB;"
    
    
    $mysqlArgs = @(
        "-h", $TargetHost,
        "-u", $TargetUser,
        "-P", $TargetPort,
        "-e", $createDBSQL
    )
    
    if ($TargetPassword) {
        $mysqlArgs += @("-p$TargetPassword")
    }
    
    & $mysql @mysqlArgs
    Write-Host "[OK] Base de datos creada/verificada" -ForegroundColor $gree
    $importArgs = @(
        "-h", $TargetHost,
        "-u", $TargetUser,
        "-P", $TargetPort
    )
    
    if ($TargetPassword) {
        $importArgs += @("-p$TargetPassword")
    }
    
    $importArgs += @(
        $SourceDB,
        "<", $dumpFile
    )
    
    Get-Content $dumpFile | & $mysql (@(
        "-h", $TargetHost,
        "-u", $TargetUser,
        "-P", $TargetPort
    ) + (if ($TargetPassword) { "-p$TargetPassword" } else { @() }) + @( $SourceDB ))
    
    Write-Host "✓ Importación completada" -ForegroundColor $green

    # Paso 4: Verificar
    Write-Host "`n[4/4] Verificando integridad..." -ForegroundColor $green
    
    $verifyArgs [OK] Importacion completada" -ForegroundColor $greener,
        "-P", $TargetPort,
        "-e", "SELECT COUNT(*) as TablesCount FROM information_schema.TABLES WHERE TABLE_SCHEMA='$SourceDB';"
    )3/3] Verificando integridad..." -ForegroundColor $green
    
    $verifyArgs = @(
        "-h", $TargetHost,
        "-u", $TargetUser,
        "-P", $TargetPort,
        "-e", "SELECT COUNT(*) as TablesCount FROM information_schema.TABLES WHERE TABLE_SCHEMA='$SourceDB';"
    )
    
    if ($TargetPassword) {
        $verifyArgs += @("-p$TargetPassword")
    }
    
    & $mysql @verifyArgs
    
    Write-Host "`n=== [OK] MIGRACION COMPLETADA EXITOSAMENTE ===" -ForegroundColor $green
    Write-Host "La base de datos ya esta lista en Laragon" -ForegroundColor $green
    
    Remove-Item $dumpFile -Force
    Write-Host "`nArchivos temporales eliminados.`n" -ForegroundColor $green

}
catch {
    Write-Host "`n[ERROR] ERROR EN LA MIGRACION:" -ForegroundColor $red
    Write-Host $_.Exception.Message -ForegroundColor $red
    Write-Host "`nIntenta:" -ForegroundColor $yellow
    Write-Host "1. Verifica que MySQL este en PATH (mysql y mysqldump disponibles)" -ForegroundColor $yellow
    Write-Host "2. Verifica credenciales de origen y destino" -ForegroundColor $yellow
    Write-Host "3. Asegurate que Laragon MySQL este