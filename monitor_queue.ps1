# MONITOR DE COLA - POWERSHELL
# Uso: .\monitor_queue.ps1 (se actualiza cada 5 segundos)
# Uso: .\monitor_queue.ps1 -Interval 2 (actualiza cada 2 segundos)

param(
    [int]$Interval = 5,
    [string]$BaseURL = "http://localhost:8000"
)

function Highlight-Status {
    param([string]$Status, [string]$Value)
    
    switch ($Status.ToLower()) {
        "reproduciendo" { Write-Host "🟢 $Value" -ForegroundColor Green }
        "aprobado" { Write-Host "🔵 $Value" -ForegroundColor Cyan }
        "pendiente_lazy" { Write-Host "🟡 $Value" -ForegroundColor Yellow }
        "pendiente" { Write-Host "🟠 $Value" -ForegroundColor DarkYellow }
        "cumplida" { Write-Host "✅ $Value" -ForegroundColor Green }
        "rechazada" { Write-Host "❌ $Value" -ForegroundColor Red }
        default { Write-Host "ℹ️  $Value" -ForegroundColor Gray }
    }
}

function Get-QueueDebug {
    try {
        $ProgressPreference = 'SilentlyContinue'
        $response = Invoke-WebRequest -Uri "$BaseURL/admin/queue/debug" -UseBasicParsing -TimeoutSec 5
        return $response.Content | ConvertFrom-Json
    }
    catch {
        Write-Host "❌ Error conectando a $BaseURL" -ForegroundColor Red
        Write-Host "Asegúrate que el backend está corriendo" -ForegroundColor Yellow
        exit 1
    }
}

function Print-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Blue
    Write-Host "  $Text" -ForegroundColor Blue
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Blue
    Write-Host ""
}

function Print-NowPlaying {
    param($Report)
    
    Write-Host "🎵 REPRODUCIENDO AHORA:" -ForegroundColor Cyan -NoNewline
    
    $nextReport = try {
        $ProgressPreference = 'SilentlyContinue'
        $r = Invoke-WebRequest -Uri "$BaseURL/admin/queue/next-to-play" -UseBasicParsing -TimeoutSec 5
        $r.Content | ConvertFrom-Json
    }
    catch { $null }
    
    if ($nextReport) {
        $status = $nextReport.status
        
        if ($status -eq "something_is_playing") {
            $playing = $nextReport.now_playing
            Write-Host " ▶ $($playing.titulo)" -ForegroundColor Green
            Write-Host "   ID: $($playing.id) | Usuario: $($playing.usuario_id) | Progreso: $($playing.progress_percent)%" -ForegroundColor Gray
            
            $next = $nextReport.next_after_current
            if ($next) {
                Write-Host "   → Siguiente: $($next.titulo) (ID: $($next.id))" -ForegroundColor Yellow
            }
        }
        elseif ($status -eq "empty") {
            Write-Host " ❌ COLA VACÍA" -ForegroundColor Red
        }
    }
}

function Print-NextSongs {
    param($Report, [int]$Limit = 15)
    
    Write-Host "↓ PRÓXIMAS $Limit CANCIONES:" -ForegroundColor Cyan
    
    $songs = $Report.what_will_play.next_20_in_queue
    
    if (-not $songs) {
        Write-Host "  (ninguna)" -ForegroundColor Yellow
        return
    }
    
    $i = 1
    foreach ($song in $songs) {
        if ($i -gt $Limit) { break }
        
        $id = $song.id
        $titulo = $song.titulo
        $usuario = $song.usuario
        $estado = $song.estado
        
        Write-Host "  $i. $titulo" -ForegroundColor Cyan
        Write-Host "     [ID: $id | Usuario: $usuario | Estado: $estado]" -ForegroundColor Gray
        $i++
    }
    
    if ($songs.Count -gt $Limit) {
        Write-Host "  ... y $($songs.Count - $Limit) más" -ForegroundColor Yellow
    }
}

function Print-DBState {
    param($Report)
    
    Write-Host "💾 ESTADO EN BASE DE DATOS:" -ForegroundColor Cyan
    
    $db = $Report.database_state
    
    Write-Host "  Reproduciendo: $($db.reproduciendo_count)" -ForegroundColor Green -NoNewline
    Write-Host " | Aprobadas: $($db.aprobado_count)" -ForegroundColor Blue -NoNewline
    Write-Host " | Pendiente (lazy): $($db.pendiente_lazy_count)" -ForegroundColor Yellow -NoNewline
    Write-Host " | Pendiente: $($db.pendiente_count)" -ForegroundColor Yellow
    
    Write-Host "  Cumplidas: $($db.cumplida_count)" -ForegroundColor Green -NoNewline
    Write-Host " | Rechazadas: $($db.rechazada_count)" -ForegroundColor Red
}

function Print-Integrity {
    param($Report)
    
    Write-Host "🔍 VALIDACIONES:" -ForegroundColor Cyan
    
    $checks = $Report.integrity_checks
    
    foreach ($check in $checks.PSObject.Properties) {
        if ($check.Name -eq "issues_detected") { continue }
        
        $value = $check.Value
        $icon = if ($value) { "✓" } else { "✗" }
        $color = if ($value) { "Green" } else { "Red" }
        
        Write-Host "  [$icon] $($check.Name): $value" -ForegroundColor $color
    }
    
    $issues = $Report.issues
    if ($issues -and $issues.Count -gt 0) {
        Write-Host "  ⚠ Problemas detectados: $($issues.Count)" -ForegroundColor Red
        foreach ($issue in $issues | Select-Object -First 3) {
            Write-Host "    - $($issue.message)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "  ✓ Sin problemas" -ForegroundColor Green
    }
}

function Print-HiddenSongs {
    param($Report)
    
    $songs = $Report.what_will_play.next_20_in_queue
    
    if (-not $songs -or $songs.Count -le 10) {
        Write-Host "👻 CANCIONES ESCONDIDAS: Ninguna" -ForegroundColor Gray
        return
    }
    
    $hidden = $songs | Select-Object -Skip 10
    Write-Host "👻 CANCIONES ESCONDIDAS: $($hidden.Count)" -ForegroundColor Yellow
    
    foreach ($song in $hidden | Select-Object -First 5) {
        Write-Host "   - $($song.titulo) (ID: $($song.id))" -ForegroundColor Yellow
    }
    
    if ($hidden.Count -gt 5) {
        Write-Host "   ... y $($hidden.Count - 5) más" -ForegroundColor Yellow
    }
}

# ============================================================================
# MAIN LOOP
# ============================================================================

Clear-Host
Write-Host "🔧 MONITOR DE COLA QR KARAOKE" -ForegroundColor Blue -BackgroundColor Black
Write-Host "   Backend: $BaseURL" -ForegroundColor Gray
Write-Host "   Intervalo: ${Interval}s (Ctrl+C para salir)" -ForegroundColor Gray
Write-Host ""

$iteration = 0

while ($true) {
    $iteration++
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    # Limpiar pantalla (opcional - comentar si prefieres scroll)
    # Clear-Host
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
    Write-Host "📊 Actualización #$iteration - $timestamp" -ForegroundColor Blue
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
    
    $report = Get-QueueDebug
    
    Print-NowPlaying $report
    Write-Host ""
    Print-NextSongs $report 10
    Write-Host ""
    Print-DBState $report
    Write-Host ""
    Print-Integrity $report
    Write-Host ""
    Print-HiddenSongs $report
    
    Write-Host ""
    Write-Host "⏳ Próxima actualización en ${Interval}s (Ctrl+C para salir)..." -ForegroundColor Gray
    
    Start-Sleep -Seconds $Interval
}
