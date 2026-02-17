# Script rápido para verificar que el autoplay está configurado (PowerShell)
# Guardar como: verify_autoplay.ps1
# Ejecutar: .\verify_autoplay.ps1

Write-Host "`n" -ForegroundColor Cyan
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     🎵 VERIFICADOR DE AUTOPLAY            ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host "`n"

$allGood = $true

# 1. Verificar archivos clave
Write-Host "📁 Verificando archivos principales..." -ForegroundColor Yellow

$filesToCheck = @(
    "static\player.html",
    "websocket_manager.py",
    "crud.py"
)

foreach ($file in $filesToCheck) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "❌ $file NO ENCONTRADO" -ForegroundColor Red
        $allGood = $false
    }
}

# 2. Verificar contenido clave
Write-Host "`n📝 Verificando configuración..." -ForegroundColor Yellow

# Buscar fallback timer en player.html
$playerContent = Get-Content "static\player.html" -Raw
if ($playerContent -match "autoplayTimer" -and $playerContent -match "FALLBACK TIMER") {
    Write-Host "✅ Player.html tiene fallback timer" -ForegroundColor Green
} else {
    Write-Host "❌ Player.html podría no tener fallback timer" -ForegroundColor Yellow
}

# Buscar duration en websocket_manager
$wsContent = Get-Content "websocket_manager.py" -Raw
if ($wsContent -match "duration_seconds") {
    Write-Host "✅ WebSocket envía duration_seconds" -ForegroundColor Green
} else {
    Write-Host "❌ WebSocket no envía duration" -ForegroundColor Red
    $allGood = $false
}

# Buscar duration en crud
$crudContent = Get-Content "crud.py" -Raw
if ($crudContent -match "duracion_seconds or 0") {
    Write-Host "✅ CRUD pasa duracion_seconds" -ForegroundColor Green
} else {
    Write-Host "⚠️  CRUD podría no pasar duracion" -ForegroundColor Yellow
}

# 3. Verificar servidor
Write-Host "`n🌐 Verificando servidor..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/canciones/cola/extended" -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Servidor está corriendo" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ No se pudo conectar al servidor (http://localhost:8000)" -ForegroundColor Red
    Write-Host "   Asegúrate que uvicorn esté ejecutándose" -ForegroundColor Gray
    $allGood = $false
}

# 4. Resumen
Write-Host "`n" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✨ AUTOPLAY LISTO PARA USAR ✨           ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host "`nPróximos pasos:" -ForegroundColor Cyan
    Write-Host "1. Abre: http://localhost:8000/static/player.html" -ForegroundColor White
    Write-Host "2. Presiona F12 (Console Tab)" -ForegroundColor White
    Write-Host "3. Agrega canciones desde el admin" -ForegroundColor White
    Write-Host "4. ¡Verifica que se reproducen automáticamente!" -ForegroundColor White
} else {
    Write-Host "⚠️  FALTAN CONFIGURACIONES" -ForegroundColor Yellow
    Write-Host "Revisa los items marcados con ❌ arriba" -ForegroundColor Yellow
}

Write-Host "`n"
