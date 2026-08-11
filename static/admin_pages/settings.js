// Settings Page Module - BEES Style
// Manejo: configuración de cierre nocturno, claves API, parámetros generales

async function loadSettingsPage() {
    const settingsContainer = document.getElementById('settings');
    if (!settingsContainer) return;

    try {
        // Carga la configuración desde el backend
        let settings = {
            closing_hour: 3,
            closing_minute: 0,
            app_name: 'QR Karaoke',
            theme: 'dark',
            enable_notifications: true
        };

        try {
            const response = await apiFetch('/admin/settings');
            if (response) settings = { ...settings, ...response };
        } catch (e) {
            console.warn('Settings endpoint not available, using defaults:', e.message);
        }

        // Aplicar tema cargado
        document.body.dataset.theme = settings.theme;

        renderSettings(settings, settingsContainer);
    } catch (error) {
        const settingsContainer = document.getElementById('settings');
        if (settingsContainer) {
            settingsContainer.innerHTML = `<div class="settings-message error">
                <span class="settings-message-icon">❌</span>
                <div>${error.message}</div>
            </div>`;
        }
    }
}

function renderSettings(settings, container) {
    container.innerHTML = '';

    // Encabezado
    const header = document.createElement('div');
    header.className = 'settings-header';
    header.innerHTML = `
        <div class="settings-header-icon">⚙️</div>
        <div class="settings-header-content">
            <h1>Configuración</h1>
            <p>Personaliza tu experiencia en QR Karaoke</p>
        </div>
    `;
    container.appendChild(header);

    // Contenedor de tarjetas
    const cardsContainer = document.createElement('div');
    cardsContainer.className = 'settings-container';

    // ============= TARJETA 1: INFORMACIÓN GENERAL =============
    const generalCard = document.createElement('div');
    generalCard.className = 'settings-card';
    generalCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">📱</div>
            <div class="settings-card-header-content">
                <h3>Información General</h3>
                <p>Nombre y personalización</p>
            </div>
        </div>
        <form id="general-settings-form">
            <div class="bees-form-group">
                <label for="app-name">Nombre de la Aplicación</label>
                <input type="text" id="app-name" name="app_name" value="${settings.app_name || 'QR Karaoke'}" placeholder="Ej: QR Karaoke">
            </div>
            <button type="submit" class="bees-btn bees-btn-primary">
                💾 Guardar Cambios
            </button>
        </form>
    `;
    cardsContainer.appendChild(generalCard);

    // ============= TARJETA: LOGO CORPORATIVO =============
    const logoCard = document.createElement('div');
    logoCard.className = 'settings-card';
    logoCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🏢</div>
            <div class="settings-card-header-content">
                <h3>Imagen Corporativa (Logo)</h3>
                <p>Personaliza la pantalla de espera de tu TV</p>
            </div>
        </div>
        <form id="logo-settings-form" enctype="multipart/form-data">
            <div class="logo-preview-container" style="margin-bottom: 20px; text-align: center;">
                <img id="logo-preview-img" src="${settings.owner_logo || '/static/images/watermark.jpg'}" style="width: 120px !important; height: 120px !important; border-radius: 50% !important; border: 2.5px solid var(--primary, #9d4edd) !important; object-fit: cover !important; box-shadow: 0 0 15px rgba(157,78,221,0.3) !important;" />
            </div>
            <div class="bees-form-group">
                <label for="owner-logo-file" class="bees-label">Subir nueva imagen (PNG, JPG, WEBP)</label>
                <input type="file" id="owner-logo-file" name="file" accept="image/*" class="bees-input" style="padding: 8px !important;">
            </div>
            <button type="submit" class="bees-btn bees-btn-primary" style="margin-top: 15px !important;">
                📤 Subir Logo
            </button>
        </form>
    `;
    cardsContainer.appendChild(logoCard);

    // ============= TARJETA 2: TEMA =============
    const themeCard = document.createElement('div');
    themeCard.className = 'settings-card';
    const currentTheme = settings.theme || 'dark';
    themeCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🎨</div>
            <div class="settings-card-header-content">
                <h3>Tema Visual</h3>
                <p>Elige tu preferencia</p>
            </div>
        </div>
        <form id="theme-settings-form">
            <div class="theme-options">
                <label class="theme-option ${currentTheme === 'dark' ? 'active' : ''}">
                    <input type="radio" name="theme" value="dark" ${currentTheme === 'dark' ? 'checked' : ''} style="display:none;">
                    <div class="theme-option-icon">🌙</div>
                    <div class="theme-option-label">Oscuro</div>
                </label>
                <label class="theme-option ${currentTheme === 'light' ? 'active' : ''}">
                    <input type="radio" name="theme" value="light" ${currentTheme === 'light' ? 'checked' : ''} style="display:none;">
                    <div class="theme-option-icon">☀️</div>
                    <div class="theme-option-label">Claro</div>
                </label>
                <label class="theme-option ${currentTheme === 'auto' ? 'active' : ''}">
                    <input type="radio" name="theme" value="auto" ${currentTheme === 'auto' ? 'checked' : ''} style="display:none;">
                    <div class="theme-option-icon">🔄</div>
                    <div class="theme-option-label">Auto</div>
                </label>
            </div>
            <button type="submit" class="bees-btn bees-btn-primary">
                💾 Aplicar Tema
            </button>
        </form>
    `;
    cardsContainer.appendChild(themeCard);

    // ============= TARJETA 3: NOTIFICACIONES =============
    const notificationsCard = document.createElement('div');
    notificationsCard.className = 'settings-card';
    notificationsCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🔔</div>
            <div class="settings-card-header-content">
                <h3>Notificaciones</h3>
                <p>Controla alertas</p>
            </div>
        </div>
        <form id="notifications-settings-form">
            <div class="notification-item">
                <div class="notification-item-icon">📢</div>
                <div class="notification-item-content">
                    <p class="notification-item-title">Notificaciones Generales</p>
                    <p class="notification-item-desc">Recibe alertas importantes del sistema</p>
                </div>
                <input type="checkbox" class="bees-checkbox" id="enable-notifications" name="enable_notifications" ${settings.enable_notifications !== false ? 'checked' : ''}>
            </div>
            <div class="notification-item">
                <div class="notification-item-icon">🔔</div>
                <div class="notification-item-content">
                    <p class="notification-item-title">Sonido de Pedidos</p>
                    <p class="notification-item-desc">Reproducir sonido al recibir nuevos pedidos</p>
                </div>
                <input type="checkbox" class="bees-checkbox" id="enable-sound" name="enable_sound" ${localStorage.getItem('adminSoundEnabled') !== 'false' ? 'checked' : ''}>
            </div>
            <button type="submit" class="bees-btn bees-btn-primary">
                💾 Guardar Preferencias
            </button>
        </form>
    `;
    cardsContainer.appendChild(notificationsCard);

    // ============= TARJETA 4: HORA DE CIERRE =============
    const closingTimeCard = document.createElement('div');
    closingTimeCard.className = 'settings-card';
    const closingHour = String(settings.closing_hour || 3).padStart(2, '0');
    const closingMinute = String(settings.closing_minute || 0).padStart(2, '0');
    closingTimeCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🌙</div>
            <div class="settings-card-header-content">
                <h3>Hora de Cierre</h3>
                <p>Configurar cierre nocturno</p>
            </div>
        </div>
        <div class="closing-time-display">
            <div class="closing-time-display-label">Hora Actual</div>
            <div class="closing-time-display-value" id="closing-time-display">${closingHour}:${closingMinute}</div>
        </div>
        <form id="closing-time-form">
            <div class="closing-time-inputs">
                <div class="bees-form-group">
                    <label for="closing-hour">Hora (0-23)</label>
                    <input type="number" id="closing-hour" name="closing_hour" min="0" max="23" value="${settings.closing_hour || 3}">
                </div>
                <div class="bees-form-group">
                    <label for="closing-minute">Minuto (0-59)</label>
                    <input type="number" id="closing-minute" name="closing_minute" min="0" max="59" value="${settings.closing_minute || 0}">
                </div>
            </div>
            <button type="submit" class="bees-btn bees-btn-primary">
                💾 Guardar Hora
            </button>
        </form>
    `;
    cardsContainer.appendChild(closingTimeCard);

    // ============= TARJETA 5: CONFIGURACIÓN COLA LAZY =============
    const lazyQueueCard = document.createElement('div');
    lazyQueueCard.className = 'settings-card';
    lazyQueueCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🎵</div>
            <div class="settings-card-header-content">
                <h3>Fórmula de Entrada a Cola Lazy</h3>
                <p>Gestiona cómo los usuarios agregan canciones</p>
            </div>
        </div>
        <div style="padding: 16px; background: rgba(76, 175, 80, 0.1); border-radius: 8px; border-left: 4px solid var(--bees-green); margin-bottom: 16px;">
            <p style="margin: 0; font-size: 12px; color: #2e7d32;">
                <strong>ℹ️ Información:</strong> Estos parámetros controlan cómo los usuarios pueden agregar canciones después de hacer una compra.
            </p>
        </div>
        <form id="lazy-queue-form">
            <div class="bees-form-group">
                <label for="credit-multiplier">
                    Multiplicador de Créditos
                    <span style="font-size: 11px; color: var(--settings-text-secondary);">x Monto Gastado</span>
                </label>
                <div style="display: flex; gap: 12px; align-items: center;">
                    <input type="number" id="credit-multiplier" name="credit_multiplier" min="0.1" max="10" step="0.1" value="1.0" style="flex: 1;">
                    <span style="font-size: 14px; font-weight: bold; min-width: 60px;" id="credit-multiplier-display">1.0x</span>
                </div>
                <p style="margin: 8px 0 0 0; font-size: 12px; color: var(--settings-text-secondary);">
                    Ej: 1.0 = $100 → 100 créditos | 1.5 = $100 → 150 créditos
                </p>
            </div>

            <div class="bees-form-group">
                <label for="decay-rate">
                    Tasa de Decaimiento
                    <span style="font-size: 11px; color: var(--settings-text-secondary);">Créditos/Minuto</span>
                </label>
                <div style="display: flex; gap: 12px; align-items: center;">
                    <input type="number" id="decay-rate" name="decay_rate" min="0" step="10" value="100" style="flex: 1;">
                    <span style="font-size: 14px; font-weight: bold; min-width: 100px;" id="decay-rate-display">100/min</span>
                </div>
                <p style="margin: 8px 0 0 0; font-size: 12px; color: var(--settings-text-secondary);">
                    Créditos que se pierden cada minuto (0 = sin decaimiento)
                </p>
            </div>

            <div style="margin-top: 16px; padding-top: 16px; border-top: 2px solid var(--settings-border);">
                <h4 style="margin: 0 0 12px 0; color: var(--settings-text);">Modos Especiales</h4>
                
                <label style="display: flex; align-items: center; gap: 12px; padding: 12px; background: rgba(255, 193, 7, 0.1); border-radius: 8px; border-left: 4px solid #FFC107; cursor: pointer; margin-bottom: 12px;">
                    <input type="checkbox" id="allow-unrestricted" name="allow_unrestricted" class="bees-checkbox" style="margin: 0;">
                    <div>
                        <strong>🔓 Modo Sin Restricciones</strong>
                        <p style="margin: 4px 0 0 0; font-size: 12px; color: var(--settings-text-secondary);">
                            Permite que los usuarios agreguen canciones sin límite de créditos
                        </p>
                    </div>
                </label>
            </div>

            <div class="bees-form-group">
                <label for="max-concurrent">Máximo de Canciones Concurrentes por Usuario</label>
                <input type="number" id="max-concurrent" name="max_concurrent_songs" min="1" max="50" value="10">
                <p style="margin: 8px 0 0 0; font-size: 12px; color: var(--settings-text-secondary);">
                    Límite de canciones que puede tener un usuario en la cola simultáneamente
                </p>
            </div>

            <button type="submit" class="bees-btn bees-btn-primary" style="width: 100%; margin-top: 16px; padding: 12px;">
                💾 Guardar Configuración
            </button>
        </form>
    `;
    cardsContainer.appendChild(lazyQueueCard);

    // ============= TARJETA 6: CLAVES API =============
    const apiKeysCard = document.createElement('div');
    apiKeysCard.className = 'settings-card';
    apiKeysCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🔐</div>
            <div class="settings-card-header-content">
                <h3>Claves de API</h3>
                <p>Gestiona tus accesos</p>
            </div>
        </div>
        <div id="api-keys-list" class="api-keys-list">
            <p style="text-align: center; color: var(--settings-text-secondary);">Cargando claves...</p>
        </div>
        <div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid var(--settings-border);">
            <h4 style="margin: 0 0 16px 0; color: var(--settings-text);">Crear Nueva Clave</h4>
            <form id="create-api-key-form">
                <div class="bees-form-group">
                    <label for="key-description">Descripción</label>
                    <input type="text" id="key-description" name="description" placeholder="Ej: Mi laptop personal" required>
                </div>
                <button type="submit" class="bees-btn bees-btn-primary">
                    🔑 Generar Clave
                </button>
            </form>
            <div id="new-key-display" class="generated-key-display">
                <h4 class="generated-key-title">✅ ¡Clave Generada!</h4>
                <div class="generated-key-warning">
                    ⚠️ <strong>Guarda esta clave ahora.</strong> No podrás verla de nuevo.
                </div>
                <div class="key-input-group">
                    <input type="text" id="generated-key" readonly placeholder="Tu clave aparecerá aquí">
                    <button type="button" id="copy-generated-key" class="bees-btn bees-btn-success">
                        📋 Copiar
                    </button>
                </div>
            </div>
        </div>
    `;
    cardsContainer.appendChild(apiKeysCard);

    // ============= TARJETA: REPRODUCTOR NATIVO (PLAYER 2) =============
    const player2Card = document.createElement('div');
    player2Card.className = 'settings-card';
    player2Card.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">📺</div>
            <div class="settings-card-header-content">
                <h3>Reproductor Nativo (Player 2)</h3>
                <p>Control del reproductor Chromium local con bloqueador de publicidad</p>
            </div>
        </div>
        <div style="margin-top: 15px; display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.05); padding: 10px 15px; border-radius: 8px;">
                <span style="font-size: 14px; color: var(--page-text-secondary);">Estado del reproductor local:</span>
                <strong id="player2-status-text" style="color: var(--bees-red);">🔴 Inactivo</strong>
            </div>
            <div style="display: flex; gap: 10px;">
                <button type="button" id="btn-launch-player2" class="bees-btn bees-btn-success" style="flex: 1; padding: 12px;">🟢 Iniciar</button>
                <button type="button" id="btn-kill-player2" class="bees-btn bees-btn-danger" style="flex: 1; padding: 12px;">🔴 Detener</button>
            </div>
            <div style="font-size: 12px; color: var(--page-text-secondary); line-height: 1.4;">
                💡 <em>Nota: Esta acción ejecuta Chromium de forma local en la máquina que aloja el servidor. Si estás en la nube, ejecuta <strong>python launch_player2.py --server TU_URL_SERVER --ws TU_URL_WS</strong> localmente en el PC del bar.</em>
            </div>
        </div>
    `;
    cardsContainer.appendChild(player2Card);
    
    // Check status immediately
    setTimeout(checkPlayer2Status, 100);

    // ============= TARJETA 7: HERRAMIENTAS DE DIAGNÓSTICO =============
    const debugCard = document.createElement('div');
    debugCard.className = 'settings-card';
    debugCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon">🔍</div>
            <div class="settings-card-header-content">
                <h3>Herramientas de Diagnóstico</h3>
                <p>Verificar estado real de la cola y sincronización</p>
            </div>
        </div>
        <button class="bees-btn bees-btn-success" onclick="if(window.queueValidator) { window.queueValidator.toggleDebugPanel() } else { alert('Herramienta de debug no cargada') }" style="width: 100%; margin-top: 10px; padding: 12px;">🔍 DEBUG COLA</button>
    `;
    cardsContainer.appendChild(debugCard);

    // ============= TARJETA 8: ZONA PELIGROSA =============
    const dangerCard = document.createElement('div');
    dangerCard.className = 'settings-card';
    dangerCard.style.borderLeft = '4px solid var(--bees-red)';
    dangerCard.style.background = 'rgba(255, 68, 68, 0.05)';
    dangerCard.innerHTML = `
        <div class="settings-card-header">
            <div class="settings-card-icon" style="color: var(--bees-red);">⚠️</div>
            <div class="settings-card-header-content">
                <h3 style="color: var(--bees-red);">Zona Peligrosa</h3>
                <p>Acciones que afectan toda la aplicación</p>
            </div>
        </div>
        <div style="padding: 12px; background: rgba(255, 68, 68, 0.1); border-radius: 8px; border-left: 4px solid var(--bees-red); margin-bottom: 16px;">
            <strong style="color: var(--bees-red);">⚠️ Advertencia:</strong> Estas acciones no se pueden deshacer fácilmente.
        </div>
        <button class="bees-btn bees-btn-danger" id="reset-night-btn" style="width: 100%; padding: 12px;">🔄 Reiniciar Noche</button>
    `;
    cardsContainer.appendChild(dangerCard);

    container.appendChild(cardsContainer);

    // Configurar listeners después de renderizar
    setupSettingsListeners();
}

async function handleClosingTimeUpdate(event, form) {
    event.preventDefault();
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.closing_hour = parseInt(data.closing_hour, 10);
    data.closing_minute = parseInt(data.closing_minute, 10);

    try {
        let success = false;
        try {
            await apiFetch('/admin/settings/closing-time', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            success = true;
        } catch (e) {
            // Fallback
            const fallbackData = {
                hora_cierre: `${String(data.closing_hour).padStart(2, '0')}:${String(data.closing_minute).padStart(2, '0')}`
            };
            await apiFetch('/admin/set-closing-time', {
                method: 'POST',
                body: JSON.stringify(fallbackData)
            });
            success = true;
        }

        if (success) {
            // Actualizar display
            const display = document.getElementById('closing-time-display');
            if (display) {
                display.textContent = `${String(data.closing_hour).padStart(2, '0')}:${String(data.closing_minute).padStart(2, '0')}`;
            }
            showNotification(`✅ Hora de cierre actualizada a ${String(data.closing_hour).padStart(2, '0')}:${String(data.closing_minute).padStart(2, '0')}`, 'success');
        }
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function handleThemeChange(event, form) {
    event.preventDefault();
    const formData = new FormData(form);
    const theme = formData.get('theme');

    try {
        const data = {
            app_name: 'QR Karaoke',
            theme: theme,
            enable_notifications: true
        };

        await apiFetch('/admin/settings/general', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        // Aplicar tema
        document.body.dataset.theme = theme;

        // Actualizar botones visuales
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('active');
        });
        form.querySelector(`input[value="${theme}"]`).parentElement.classList.add('active');

        showNotification(`✅ Tema cambiado a ${theme === 'dark' ? 'Oscuro 🌙' : theme === 'light' ? 'Claro ☀️' : 'Auto 🔄'}`, 'success');
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function handleNotificationsChange(event, form) {
    event.preventDefault();
    const enableNotifications = document.getElementById('enable-notifications').checked;
    const enableSound = document.getElementById('enable-sound').checked;

    try {
        // Guardar preferencia de sonido localmente
        localStorage.setItem('adminSoundEnabled', enableSound);

        const data = {
            app_name: 'QR Karaoke',
            theme: document.body.dataset.theme || 'dark',
            enable_notifications: enableNotifications
        };

        await apiFetch('/admin/settings/general', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        showNotification(`✅ Preferencias actualizadas.`, 'success');
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function loadApiKeys() {
    const apiKeysList = document.getElementById('api-keys-list');
    if (!apiKeysList) return;

    try {
        const keys = await apiFetch('/admin/api-keys');

        if (!keys || keys.length === 0) {
            apiKeysList.innerHTML = '<p style="text-align: center; color: var(--settings-text-secondary);">No hay claves creadas todavía.</p>';
            return;
        }

        const keysTable = document.createElement('div');
        keysTable.className = 'api-keys-list';

        keys.forEach(key => {
            const keyItem = document.createElement('div');
            keyItem.className = 'api-key-item';

            const keyInfo = document.createElement('div');
            keyInfo.className = 'api-key-info';
            keyInfo.innerHTML = `
                <p class="api-key-description">🔑 ${key.description || 'Sin descripción'}</p>
                <p class="api-key-dates">
                    Creada: ${new Date(key.created_at).toLocaleString('es-ES')}
                    ${key.last_used ? `<br>Último uso: ${new Date(key.last_used).toLocaleString('es-ES')}` : ''}
                </p>
            `;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'bees-btn bees-btn-danger';
            deleteBtn.textContent = '🗑️ Eliminar';
            deleteBtn.onclick = () => handleDeleteApiKey(key.id);

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'api-key-actions';
            actionsDiv.appendChild(deleteBtn);

            keyItem.appendChild(keyInfo);
            keyItem.appendChild(actionsDiv);
            keysTable.appendChild(keyItem);
        });

        apiKeysList.innerHTML = '';
        apiKeysList.appendChild(keysTable);
    } catch (error) {
        apiKeysList.innerHTML = `<p style="text-align: center; color: var(--bees-red);">❌ Error al cargar claves: ${error.message}</p>`;
    }
}

async function handleCreateApiKey(event, form) {
    event.preventDefault();
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        const newKey = await apiFetch('/admin/api-keys', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        // Mostrar clave generada
        const newKeyDisplay = document.getElementById('new-key-display');
        const generatedKeyInput = document.getElementById('generated-key');
        generatedKeyInput.value = newKey.key;
        newKeyDisplay.classList.add('show');

        // Botón copiar
        const copyBtn = document.getElementById('copy-generated-key');
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(newKey.key).then(() => {
                showNotification('✅ Clave copiada al portapapeles.', 'success');
                copyBtn.textContent = '✔️ Copiado!';
                setTimeout(() => {
                    copyBtn.textContent = '📋 Copiar';
                }, 2000);
            }).catch(err => {
                showNotification('❌ Error al copiar clave.', 'error');
            });
        };

        showNotification('✅ Clave generada con éxito. ¡Guárdala ahora!', 'success');
        form.reset();

        // Recargar lista
        await loadApiKeys();

        // Ocultar después de 60 segundos
        setTimeout(() => {
            newKeyDisplay.classList.remove('show');
        }, 60000);
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function handleDeleteApiKey(keyId) {
    if (!confirm('🗑️ ¿Eliminar esta clave? Esta acción no se puede deshacer.')) {
        return;
    }

    try {
        await apiFetch(`/admin/api-keys/${keyId}`, { method: 'DELETE' });
        showNotification('✅ Clave eliminada con éxito.', 'success');
        await loadApiKeys();
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function handleGeneralSettingsUpdate(event, form) {
    event.preventDefault();
    const formData = new FormData(form);
    const data = {
        app_name: formData.get('app_name'),
        theme: 'dark', // Mantener tema actual, solo cambiar nombre
        enable_notifications: true // Mantener notificaciones actuales
    };

    try {
        await apiFetch('/admin/settings/general', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        showNotification(`✅ Configuración actualizada. Nombre: "${data.app_name}"`, 'success');
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function handleLogoUpload(event, form) {
    event.preventDefault();
    const fileInput = document.getElementById('owner-logo-file');
    if (!fileInput || fileInput.files.length === 0) {
        showNotification('❌ Por favor, selecciona un archivo.', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    try {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        
        const response = await fetch('/api/v1/admin/settings/logo', {
            method: 'POST',
            headers: headers,
            body: formData
        });
        
        const result = await response.json();
        if (response.ok && result.status === 'success') {
            showNotification('✅ Logo corporativo subido exitosamente.', 'success');
            const preview = document.getElementById('logo-preview-img');
            if (preview) {
                preview.src = result.owner_logo + '?t=' + Date.now();
            }
        } else {
            showNotification(`❌ ${result.message || 'Error al subir el logo'}`, 'error');
        }
    } catch (error) {
        showNotification(`❌ Error: ${error.message}`, 'error');
    }
}



async function loadLazyQueueConfig() {
    try {
        const config = await apiFetch('/admin/settings/lazy-queue');

        // Cargar valores en el formulario
        const creditMultiplierInput = document.getElementById('credit-multiplier');
        const decayRateInput = document.getElementById('decay-rate');
        const unrestricted = document.getElementById('allow-unrestricted');
        const maxConcurrentInput = document.getElementById('max-concurrent');

        if (creditMultiplierInput) {
            creditMultiplierInput.value = (config.credit_multiplier || 1.0).toFixed(1);
            const display = document.getElementById('credit-multiplier-display');
            if (display) display.textContent = (config.credit_multiplier || 1.0).toFixed(1) + 'x';
        }

        if (decayRateInput) {
            decayRateInput.value = config.decay_rate || 100;
            const display = document.getElementById('decay-rate-display');
            if (display) display.textContent = (config.decay_rate || 100) + '/min';
        }

        if (unrestricted) {
            unrestricted.checked = config.allow_unrestricted || false;
        }

        if (maxConcurrentInput) {
            maxConcurrentInput.value = config.max_concurrent_songs || 10;
        }
    } catch (error) {
        console.log('No se pudo cargar configuración de cola lazy:', error.message);
    }
}

async function handleLazyQueueUpdate(event, form) {
    event.preventDefault();
    const formData = new FormData(form);
    const data = {
        credit_multiplier: parseFloat(formData.get('credit_multiplier')) || 1.0,
        decay_rate: parseInt(formData.get('decay_rate')) || 100,
        allow_unrestricted: formData.get('allow_unrestricted') === 'on',
        max_concurrent_songs: parseInt(formData.get('max_concurrent_songs')) || 10
    };

    try {
        const result = await apiFetch('/admin/settings/lazy-queue', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        showNotification('✅ Configuración de cola lazy actualizada correctamente.', 'success');
    } catch (error) {
        showNotification(`❌ Error: ${error.message}`, 'error');
    }
}

function setupSettingsListeners() {
    const closingTimeForm = document.getElementById('closing-time-form');
    const createApiKeyForm = document.getElementById('create-api-key-form');
    const generalSettingsForm = document.getElementById('general-settings-form');
    const themeSettingsForm = document.getElementById('theme-settings-form');
    const notificationsSettingsForm = document.getElementById('notifications-settings-form');
    const resetNightBtn = document.getElementById('reset-night-btn');

    // Closing time form
    if (closingTimeForm && !closingTimeForm.dataset.listenerAttached) {
        closingTimeForm.addEventListener('submit', (e) => handleClosingTimeUpdate(e, e.target));
        closingTimeForm.dataset.listenerAttached = '1';
    }

    // API key form
    if (createApiKeyForm && !createApiKeyForm.dataset.listenerAttached) {
        createApiKeyForm.addEventListener('submit', (e) => handleCreateApiKey(e, e.target));
        createApiKeyForm.dataset.listenerAttached = '1';
    }

    // General settings form
    if (generalSettingsForm && !generalSettingsForm.dataset.listenerAttached) {
        generalSettingsForm.addEventListener('submit', (e) => handleGeneralSettingsUpdate(e, e.target));
        generalSettingsForm.dataset.listenerAttached = '1';
    }

    // Logo settings form
    const logoSettingsForm = document.getElementById('logo-settings-form');
    if (logoSettingsForm && !logoSettingsForm.dataset.listenerAttached) {
        logoSettingsForm.addEventListener('submit', (e) => handleLogoUpload(e, e.target));
        logoSettingsForm.dataset.listenerAttached = '1';
    }

    // Theme form
    if (themeSettingsForm && !themeSettingsForm.dataset.listenerAttached) {
        themeSettingsForm.addEventListener('submit', (e) => handleThemeChange(e, e.target));
        // Permitir cambio al hacer click en radio buttons
        themeSettingsForm.querySelectorAll('input[name="theme"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                e.target.closest('form').dispatchEvent(new Event('submit'));
            });
        });
        themeSettingsForm.dataset.listenerAttached = '1';
    }

    // Notifications form
    if (notificationsSettingsForm && !notificationsSettingsForm.dataset.listenerAttached) {
        notificationsSettingsForm.addEventListener('submit', (e) => handleNotificationsChange(e, e.target));
        // Cambio rápido al hacer click en checkbox
        const notificationCheckbox = document.getElementById('enable-notifications');
        const soundCheckbox = document.getElementById('enable-sound');

        if (notificationCheckbox) {
            notificationCheckbox.addEventListener('change', (e) => {
                e.target.closest('form').dispatchEvent(new Event('submit'));
            });
        }
        if (soundCheckbox) {
            soundCheckbox.addEventListener('change', (e) => {
                e.target.closest('form').dispatchEvent(new Event('submit'));
            });
        }
        notificationsSettingsForm.dataset.listenerAttached = '1';
    }

    // Reset night button
    if (resetNightBtn) {
        resetNightBtn.addEventListener('click', handleResetNight);
    }

    // Lazy Queue form
    const lazyQueueForm = document.getElementById('lazy-queue-form');
    if (lazyQueueForm && !lazyQueueForm.dataset.listenerAttached) {
        lazyQueueForm.addEventListener('submit', (e) => handleLazyQueueUpdate(e, e.target));

        // Listeners para actualización en tiempo real de los displays
        const creditMultiplierInput = document.getElementById('credit-multiplier');
        const decayRateInput = document.getElementById('decay-rate');
        const unrestricted = document.getElementById('allow-unrestricted');

        if (creditMultiplierInput) {
            creditMultiplierInput.addEventListener('input', (e) => {
                const display = document.getElementById('credit-multiplier-display');
                if (display) {
                    display.textContent = parseFloat(e.target.value).toFixed(1) + 'x';
                }
            });
        }

        if (decayRateInput) {
            decayRateInput.addEventListener('input', (e) => {
                const display = document.getElementById('decay-rate-display');
                if (display) {
                    display.textContent = e.target.value + '/min';
                }
            });
        }

        lazyQueueForm.dataset.listenerAttached = '1';
    }

    // Load current lazy queue configuration
    loadLazyQueueConfig();

    // Load API keys
    loadApiKeys();

    // Player 2 controls listeners
    const btnLaunch = document.getElementById('btn-launch-player2');
    const btnKill = document.getElementById('btn-kill-player2');
    
    if (btnLaunch && !btnLaunch.dataset.listenerAttached) {
        btnLaunch.addEventListener('click', handleLaunchPlayer2);
        btnLaunch.dataset.listenerAttached = '1';
    }
    
    if (btnKill && !btnKill.dataset.listenerAttached) {
        btnKill.addEventListener('click', handleKillPlayer2);
        btnKill.dataset.listenerAttached = '1';
    }
}

async function handleResetNight() {
    if (!confirm('⚠️ ACCIÓN DESTRUCTIVA\n\n¿Estás seguro de reiniciar la noche?\nSe borrarán: mesas, usuarios, canciones y consumos.')) {
        return;
    }

    try {
        await apiFetch('/admin/reset-night', { method: 'POST' });
        showNotification('✅ Sistema reiniciado correctamente.', 'success');
        setTimeout(() => loadSettingsPage(), 300);
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function checkPlayer2Status() {
    const statusText = document.getElementById('player2-status-text');
    if (!statusText) return;
    try {
        const response = await apiFetch('/player2/status');
        if (response && response.running) {
            statusText.textContent = '🟢 Activo (Kiosko)';
            statusText.style.color = 'var(--bees-green, #2ecc71)';
        } else {
            statusText.textContent = '🔴 Inactivo';
            statusText.style.color = 'var(--bees-red, #e74c3c)';
        }
    } catch (e) {
        console.warn('Player2 status endpoint error:', e);
    }
}

async function handleLaunchPlayer2() {
    try {
        const response = await apiFetch('/player2/launch', { method: 'POST' });
        showNotification(response.message || '🟢 Reproductor nativo iniciado.', 'success');
        setTimeout(checkPlayer2Status, 1000);
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}

async function handleKillPlayer2() {
    try {
        const response = await apiFetch('/player2/kill', { method: 'POST' });
        showNotification(response.message || '🔴 Reproductor nativo detenido.', 'info');
        setTimeout(checkPlayer2Status, 500);
    } catch (error) {
        showNotification(`❌ ${error.message}`, 'error');
    }
}
