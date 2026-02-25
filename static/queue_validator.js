/**
 * Queue Validator - Herramienta visual para diagnosticar problemas de cola
 * 
 * Muestra:
 * - Exactamente QUÉ va a reproducir
 * - Comparación UI vs realidad
 * - Canciones escondidas
 * - Estado actual
 */

class QueueValidator {
  constructor() {
    this.debugVisible = false;
    this.lastDebugReport = null;
    this.initDebugPanel();
  }

  /**
   * Inicializa el panel de debug
   */
  initDebugPanel() {
    // Crear elemento si no existe
    if (!document.getElementById('queue-debug-panel')) {
      const panel = document.createElement('div');
      panel.id = 'queue-debug-panel';
      panel.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 400px;
        max-height: 600px;
        background: #1a1a1a;
        border: 2px solid #00ff00;
        border-radius: 8px;
        padding: 12px;
        font-family: monospace;
        font-size: 11px;
        color: #00ff00;
        z-index: 9999;
        overflow-y: auto;
        display: none;
        box-shadow: 0 0 10px rgba(0,255,0,0.3);
      `;
      document.body.appendChild(panel);

      // Botón para abrirlo
      const toggleBtn = document.createElement('button');
      toggleBtn.id = 'queue-debug-toggle';
      toggleBtn.textContent = '🔍 DEBUG COLA';
      toggleBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 440px;
        padding: 8px 12px;
        background: #00ff00;
        color: #000;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-weight: bold;
        z-index: 9998;
      `;
      toggleBtn.onclick = () => this.toggleDebugPanel();
      document.body.appendChild(toggleBtn);
    }

    // Atajo de teclado: Ctrl+Shift+Q
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'Q') {
        this.toggleDebugPanel();
        e.preventDefault();
      }
    });
  }

  /**
   * Abre/cierra el panel de debug
   */
  toggleDebugPanel() {
    const panel = document.getElementById('queue-debug-panel');
    this.debugVisible = !this.debugVisible;
    panel.style.display = this.debugVisible ? 'block' : 'none';
    if (this.debugVisible) {
      this.refreshDebugReport();
    }
  }

  /**
   * Obtiene y muestra el reporte completo de debug
   */
  async refreshDebugReport() {
    try {
      const response = await fetch('/admin/queue/debug');
      const report = await response.json();
      this.lastDebugReport = report;
      this.renderDebugReport(report);
    } catch (error) {
      console.error('Error fetching debug report:', error);
      this.updatePanel(`❌ Error obteniendo reporte: ${error.message}`);
    }
  }

  /**
   * Renderiza el reporte en el panel
   */
  renderDebugReport(report) {
    const panel = document.getElementById('queue-debug-panel');
    let html = '';

    // ========== TÍTULO ==========
    html += '<h3 style="color:#00ff00; margin-top:0;">🔍 QUEUE DEBUG REPORT</h3>';
    html += `<div style="color:#ff6600; margin-bottom:10px;">⏱ ${new Date(report.timestamp).toLocaleTimeString()}</div>`;

    // ========== QUÉ VA A REPRODUCIR ==========
    const playing = report.what_will_play;
    html += '<div style="border-bottom:1px solid #00ff00; padding-bottom:8px; margin-bottom:8px;">';
    html += '<h4 style="color:#ffff00;">🎵 QUÉ VA A REPRODUCIR:</h4>';

    if (playing.status === 'empty') {
      html += '<span style="color:#ff0000;">❌ COLA VACÍA - NADA VA A REPRODUCIR</span>';
    } else if (playing.status === 'waiting_for_approval') {
      html += `<span style="color:#ffaa00;">⏳ ESPERANDO APROBACIÓN</span><br/>`;
      html += `First: <strong>${playing.first_lazy_waiting.titulo}</strong>`;
    } else if (playing.status === 'ready_to_play') {
      html += `<span style="color:#00ff00;">✓ LISTA PARA REPRODUCIR</span><br/>`;
      html += `Next: <strong>${playing.next_to_play.titulo}</strong>`;
    } else if (playing.status === 'something_is_playing') {
      html += `<span style="color:#00aaff;">▶ REPRODUCIENDO AHORA</span><br/>`;
      html += `<strong>${playing.now_playing.titulo}</strong><br/>`;
      html += `User: ${playing.now_playing.usuario}<br/>`;
      html += `Progress: ${playing.now_playing.progress_percent}%<br/>`;
      html += `<br/>`;
      html += `<span style="color:#ffff00;">↓ SIGUIENTE:</span><br/>`;
      if (playing.next_after_current) {
        html += `${playing.next_after_current.titulo}`;
      } else {
        html += `<span style="color:#ff0000;">NINGUNA</span>`;
      }
    }
    html += '</div>';

    // ========== NEXT 20 EN QUEUE ==========
    html += '<div style="border-bottom:1px solid #00ff00; padding-bottom:8px; margin-bottom:8px;">';
    html += '<h4 style="color:#ffff00;">📋 PRÓXIMAS 20 EN LA COLA (orden real):</h4>';
    if (playing.next_20_in_queue && playing.next_20_in_queue.length > 0) {
      html += '<table style="width:100%; font-size:10px;">';
      playing.next_20_in_queue.slice(0, 10).forEach((song, idx) => {
        html += `<tr>`;
        html += `<td style="color:#00ff00; width:30px;">#${idx + 1}</td>`;
        html += `<td>${song.titulo.substring(0, 25)}</td>`;
        html += `<td style="color:#aaa; width:50px;">${song.usuario}</td>`;
        html += `</tr>`;
      });
      if (playing.next_20_in_queue.length > 10) {
        html += `<tr><td colspan="3" style="color:#666;">... y ${playing.next_20_in_queue.length - 10} más</td></tr>`;
      }
      html += '</table>';
    } else {
      html += '<span style="color:#ff0000;">NINGUNA</span>';
    }
    html += '</div>';

    // ========== INTEGRIDAD ==========
    const checks = report.integrity_checks;
    html += '<div style="border-bottom:1px solid #00ff00; padding-bottom:8px; margin-bottom:8px;">';
    html += '<h4 style="color:#ffff00;">✓ INTEGRIDAD:</h4>';
    html += `<div style="color:${checks.now_playing_not_in_approved ? '#00ff00' : '#ff0000'};">
      ${checks.now_playing_not_in_approved ? '✓' : '❌'} now_playing no en approved
    </div>`;
    html += `<div style="color:${checks.no_duplicates ? '#00ff00' : '#ff0000'};">
      ${checks.no_duplicates ? '✓' : '❌'} Sin duplicados
    </div>`;
    html += `<div style="color:${checks.all_approved_have_correct_status ? '#00ff00' : '#ff0000'};">
      ${checks.all_approved_have_correct_status ? '✓' : '❌'} States correctos (aprobado)
    </div>`;
    html += `<div style="color:${checks.all_lazy_have_correct_status ? '#00ff00' : '#ff0000'};">
      ${checks.all_lazy_have_correct_status ? '✓' : '❌'} States correctos (lazy)
    </div>`;
    html += '</div>';

    // ========== ISSUES ==========
    if (report.issues && report.issues.length > 0) {
      html += '<div style="border-bottom:1px solid #ff0000; padding-bottom:8px; margin-bottom:8px;">';
      html += `<h4 style="color:#ff0000;">⚠ PROBLEMAS (${report.issues.length}):</h4>`;
      report.issues.slice(0, 5).forEach((issue) => {
        const color = issue.severity === 'CRITICAL' ? '#ff0000' : '#ffaa00';
        html += `<div style="color:${color}; margin-bottom:4px;">`;
        html += `[${issue.severity}] ${issue.issue}`;
        if (issue.cancion_id) html += ` (ID: ${issue.cancion_id})`;
        html += '</div>';
      });
      html += '</div>';
    }

    // ========== ESTADÍSTICAS BD ==========
    const db = report.database_state;
    html += '<div style="border-bottom:1px solid #00ff00; padding-bottom:8px;">';
    html += '<h4 style="color:#ffff00;">📊 ESTADO BD:</h4>';
    html += `Reproduciendo: <strong>${db.reproduciendo_count}</strong><br/>`;
    html += `Aprobadas: <strong style="color:#00ff00;">${db.aprobado_count}</strong><br/>`;
    html += `Lazy: <strong>${db.pendiente_lazy_count}</strong><br/>`;
    html += `Pendientes: <strong>${db.pendiente_count}</strong><br/>`;
    html += '</div>';

    // ========== BOTONES DE ACCIÓN ==========
    html += '<div style="margin-top:10px;">';
    html += `<button onclick="queueValidator.refreshDebugReport()" style="
      width: 100%;
      padding: 6px;
      background: #00ff00;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      margin-bottom: 4px;
    ">🔄 REFRESCAR</button>`;

    html += `<button onclick="queueValidator.compareUIVsReality()" style="
      width: 100%;
      padding: 6px;
      background: #00aaff;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      margin-bottom: 4px;
    ">🔎 COMPARAR UI vs REALIDAD</button>`;

    html += `<button onclick="console.log(queueValidator.lastDebugReport)" style="
      width: 100%;
      padding: 6px;
      background: #ffaa00;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    ">📋 VER JSON</button>`;
    html += '</div>';

    panel.innerHTML = html;
  }

  /**
   * Compara lo que muestra la UI vs la realidad en BD
   */
  async compareUIVsReality() {
    const upcomingContainer = document.getElementById('upcoming-list');
    const nowPlayingContainer = document.getElementById('now-playing-container');

    // Capturar estado visual actual
    const uiCancionesList = Array.from(upcomingContainer.querySelectorAll('[data-cancion-id]'));
    const uiNowPlayingId = nowPlayingContainer.querySelector('[data-cancion-id]')?.dataset.cancionId;

    const uiState = {
      now_playing: uiNowPlayingId ? { id: parseInt(uiNowPlayingId) } : null,
      upcoming: uiCancionesList.map(el => ({
        id: parseInt(el.dataset.cancionId),
        titulo: el.textContent
      }))
    };

    try {
      const response = await fetch('/admin/queue/compare-ui-vs-reality', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(uiState)
      });

      const comparison = await response.json();
      this.renderComparisonReport(comparison);
    } catch (error) {
      console.error('Error comparing UI vs reality:', error);
    }
  }

  /**
   * Renderiza el reporte de comparación
   */
  renderComparisonReport(comparison) {
    const debugContent = document.getElementById('queue-debug-panel');
    let html = '';

    html += '<h3 style="color:#ffff00;">🔎 UI vs REALIDAD - COMPARACIÓN</h3>';

    // Estado actual
    html += '<div style="border:1px solid #00aaff; padding:8px; margin-bottom:8px;">';
    html += '<span style="color:#00aaff;">UI MUESTRA:</span><br/>';
    html += `Now Playing ID: ${comparison.ui_state.now_playing_id || 'NINGUNA'}<br/>`;
    html += `Upcoming: ${comparison.ui_state.upcoming_count} canciones<br/>`;
    html += '</div>';

    html += '<div style="border:1px solid #00ff00; padding:8px; margin-bottom:8px;">';
    html += '<span style="color:#00ff00;">REALIDAD EN BD:</span><br/>';
    html += `Now Playing ID: ${comparison.reality_state.now_playing_id || 'NINGUNA'}<br/>`;
    html += `Upcoming: ${comparison.reality_state.upcoming_count} canciones<br/>`;
    html += '</div>';

    // Resumen
    const summary = comparison.summary;
    html += `<div style="color:${summary.is_synchronized ? '#00ff00' : '#ff0000'}; font-weight:bold; margin-bottom:8px;">
      ${summary.is_synchronized ? '✓ SINCRONIZADO' : '❌ DESINCRONIZADO'}
    </div>`;

    if (comparison.discrepancies.length > 0) {
      let html = `
  <div style="border:1px solid #ff0000; padding:8px;">
    ...
  </div>
`;
      html += `<span style="color:#ff0000;">⚠ ${summary.critical_issues} PROBLEMAS CRÍTICOS, ${summary.warnings} ADVERTENCIAS</span><br/>`;

      comparison.discrepancies.forEach((disc) => {
        const color = disc.severity === 'CRITICAL' ? '#ff0000' : '#ffaa00';
        html += `<div style="color:${color}; margin-top:6px; padding: 4px; background:rgba(255,0,0,0.1);">`;
        html += `<strong>[${disc.type.toUpperCase()}]</strong> ${disc.message}`;

        if (disc.type === 'hidden_songs' && disc.hidden_songs_details) {
          html += `<br/>🔴 CANCIONES ESCONDIDAS EN BD (${disc.hidden_songs_details.length}):`;
          disc.hidden_songs_details.slice(0, 5).forEach((song) => {
            html += `<br/>&nbsp;&nbsp;ID ${song.id}: <strong>${song.titulo}</strong> (${song.usuario})`;
          });
        }

        if (disc.type === 'phantom_songs') {
          html += `<br/>👻 IDs en UI pero NO en BD: ${disc.phantom_song_ids.join(', ')}`;
        }

        html += '</div>';
      });

      html += '</div>';
    } else {
      html += '<div style="color:#00ff00; padding:8px; background:rgba(0,255,0,0.1);">✓ TODO SINCRONIZADO</div>';
    }

    html += '<div style="margin-top:10px;">';
    html += `<button onclick="queueValidator.refreshDebugReport()" style="
      width: 100%;
      padding: 6px;
      background: #00ff00;
      color: #000;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    ">← VOLVER</button>`;
    html += '</div>';

    debugContent.innerHTML = html;
  }

  /**
   * Actualiza el panel con texto
   */
  updatePanel(text) {
    const panel = document.getElementById('queue-debug-panel');
    panel.innerHTML = `<pre style="margin:0;">${text}</pre>`;
  }

  /**
   * Monitorea cambios en la cola
   */
  startMonitoring() {
    console.log('🟢 Queue Validator Monitoring Started');
    setInterval(() => {
      this.validateQueueConsistency();
    }, 5000); // Cada 5 segundos
  }

  /**
   * Valida consistencia de la cola sin mostrar UI
   */
  async validateQueueConsistency() {
    try {
      const response = await fetch('/admin/queue/debug');
      const report = await response.json();

      // Chequeos rápidos
      if (!report.integrity_checks.now_playing_not_in_approved) {
        console.error('❌ CRITICAL: now_playing en approved!');
      }

      if (report.integrity_checks.issues_detected) {
        console.warn('⚠ Issues detectadas:', report.issues.length);
      }

      // Detectar canciones escondidas
      const hidden = report.database_state.aprobado_count - this.visibleSongsCount;
      if (hidden > 0) {
        console.warn(`⚠ ${hidden} CANCIONES ESCONDIDAS en BD!`);
      }
    } catch (error) {
      // Silent
    }
  }

  get visibleSongsCount() {
    return document.querySelectorAll('[data-cancion-id]').length;
  }
}

// Instancia global
const queueValidator = new QueueValidator();

// Auto-iniciar monitoreo
window.addEventListener('load', () => {
  queueValidator.startMonitoring();
  console.log('Queue Validator iniciado. Presiona Ctrl+Shift+Q para abrir debug panel.');
});
