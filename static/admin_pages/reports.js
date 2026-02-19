// Reports Page Module - BEES Style
// Manejo: generación de reportes por periodo, ventas, ingresos

async function loadReportsPage() {
    const reportsContainer = document.getElementById('reports');
    if (!reportsContainer) return;

    try {
        reportsContainer.innerHTML = '';

        // Encabezado
        const header = document.createElement('div');
        header.className = 'bees-header';
        header.innerHTML = `
            <div class="bees-header-icon">📊</div>
            <div class="bees-header-content">
                <h1>Reportes</h1>
                <p>Análisis de la actividad de la noche</p>
            </div>
        `;
        reportsContainer.appendChild(header);

        // Tarjeta de reportes
        const card = document.createElement('div');
        card.className = 'bees-card';
        card.style.marginBottom = '30px';

        const cardHeader = document.createElement('div');
        cardHeader.className = 'bees-card-header';
        cardHeader.innerHTML = `
            <div class="bees-card-icon">📈</div>
            <div class="bees-card-header-content">
                <h3>Generar Reportes</h3>
                <p>Selecciona el tipo de reporte que deseas ver</p>
            </div>
        `;
        card.appendChild(cardHeader);

        const controlsDiv = document.createElement('div');
        controlsDiv.style.display = 'flex';
        controlsDiv.style.gap = '12px';
        controlsDiv.style.marginBottom = '24px';
        controlsDiv.style.flexWrap = 'wrap';

        const selector = document.createElement('select');
        selector.id = 'report-selector';
        selector.style.flex = '1';
        selector.style.minWidth = '200px';
        selector.style.border = '2px solid var(--page-border)';
        selector.style.borderRadius = '8px';
        selector.style.padding = '12px';
        selector.style.background = 'var(--page-input-bg)';
        selector.style.color = 'var(--page-text)';
        selector.innerHTML = `
            <option value="">Selecciona un reporte...</option>
            <option value="top-songs">🎵 Top Canciones Más Cantadas</option>
            <option value="top-products">🥤 Top Productos Más Consumidos</option>
            <option value="total-income">💰 Ingresos Totales</option>
            <option value="income-by-table">📊 Ingresos por Mesa</option>
            <option value="songs-by-table">🎶 Canciones por Mesa</option>
            <option value="songs-by-user">👥 Canciones por Usuario</option>
            <option value="hourly-activity">⏰ Actividad por Hora</option>
            <option value="top-rejected-songs">👎 Canciones Más Rechazadas</option>
            <option value="inactive-users">😴 Usuarios Inactivos</option>
        `;
        controlsDiv.appendChild(selector);

        const generateBtn = document.createElement('button');
        generateBtn.id = 'generate-report-btn';
        generateBtn.className = 'bees-btn bees-btn-primary';
        generateBtn.textContent = '📊 Generar Reporte';
        generateBtn.style.width = 'auto';
        generateBtn.style.minWidth = '150px';
        controlsDiv.appendChild(generateBtn);

        card.appendChild(controlsDiv);

        const outputDiv = document.createElement('div');
        outputDiv.id = 'report-output';
        outputDiv.style.marginTop = '24px';
        outputDiv.innerHTML = `
            <div class="bees-alert bees-alert-info">
                <span class="bees-alert-icon">ℹ️</span>
                <div>Selecciona un reporte y haz clic en "Generar Reporte" para ver los resultados.</div>
            </div>
        `;
        card.appendChild(outputDiv);

        reportsContainer.appendChild(card);

        // Setup listeners
        setupReportsListeners();
    } catch (error) {
        const reportsContainer = document.getElementById('reports');
        if (reportsContainer) {
            reportsContainer.innerHTML = `
                <div class="bees-alert bees-alert-danger">
                    <span class="bees-alert-icon">❌</span>
                    <div>Error al cargar reportes: ${error.message}</div>
                </div>
            `;
        }
    }
}

function setupReportsListeners() {
    const generateBtn = document.getElementById('generate-report-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', handleReportGeneration);
    }
}

async function handleReportGeneration() {
    const selector = document.getElementById('report-selector');
    const outputDiv = document.getElementById('report-output');
    const reportType = selector.value;

    if (!reportType) {
        showNotification('Selecciona un tipo de reporte', 'warning');
        return;
    }

    outputDiv.innerHTML = '<div class="bees-alert bees-alert-info"><span class="bees-alert-icon">⏳</span><div>Generando reporte...</div></div>';

    try {
        const data = await apiFetch(`/admin/reports/${reportType}`);
        console.log('Report data received:', reportType, data); // DEBUG
        renderReport(reportType, data, outputDiv);
    } catch (error) {
        outputDiv.innerHTML = `
            <div class="bees-alert bees-alert-danger">
                <span class="bees-alert-icon">❌</span>
                <div>Error generando reporte: ${error.message}</div>
            </div>
        `;
    }
}

function renderReport(type, data, container) {
    container.innerHTML = '';

    // Título del reporte
    const titles = {
        'top-songs': '🎵 Top Canciones Más Cantadas',
        'top-products': '🥤 Top Productos Más Consumidos',
        'total-income': '💰 Ingresos Totales',
        'income-by-table': '📊 Ingresos por Mesa',
        'songs-by-table': '🎶 Canciones por Mesa',
        'songs-by-user': '👥 Canciones por Usuario',
        'hourly-activity': '⏰ Actividad por Hora',
        'top-rejected-songs': '👎 Canciones Más Rechazadas',
        'inactive-users': '😴 Usuarios Inactivos'
    };

    const title = document.createElement('h3');
    title.style.marginTop = '0';
    title.textContent = titles[type] || 'Reporte';
    container.appendChild(title);

    // Renderizar tabla
    if (Array.isArray(data) && data.length > 0) {
        renderReportTable(data, type, container);
    } else if (typeof data === 'object' && data.ingresos_totales !== undefined) {
        renderReportMetrics(data, container);
    } else {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'bees-alert bees-alert-warning';
        emptyDiv.innerHTML = '<span class="bees-alert-icon">📭</span><div>No hay datos disponibles para este reporte</div>';
        container.appendChild(emptyDiv);
    }
}

function renderReportTable(data, type, container) {
    const table = document.createElement('table');
    table.className = 'bees-table';

    // Encabezados según tipo
    let headers = [];
    if (type.includes('songs')) {
        headers = ['Posición', 'Canción', 'Cantidad'];
    } else if (type.includes('products')) {
        headers = ['Posición', 'Producto', 'Cantidad'];
    } else if (type.includes('income') && type.includes('table')) {
        headers = ['Mesa', 'Ingresos'];
    } else if (type.includes('songs-by-table')) {
        headers = ['Mesa', 'Canciones'];
    } else if (type.includes('user')) {
        headers = ['Usuario', 'Canciones'];
    } else if (type.includes('hourly')) {
        headers = ['Hora', 'Canciones'];
    } else if (type.includes('inactive')) {
        headers = ['Usuario', 'Mesa', 'Estado'];
    }

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    data.slice(0, 20).forEach((row, index) => {
        // DEBUG: Inspect row data
        if (index === 0) console.log('First row data for type', type, ':', row);

        const tr = document.createElement('tr');
        // Check most specific types first before generic checks
        if (type.includes('songs-by-table')) {
            tr.innerHTML = `
                <td>${row.mesa_nombre}</td>
                <td><strong>${row.canciones_cantadas}</strong></td>
            `;
        } else if (type.includes('income') && type.includes('table')) {
            tr.innerHTML = `
                <td>${row.mesa_nombre}</td>
                <td><strong>$${parseFloat(row.ingresos_totales || 0).toFixed(2)}</strong></td>
            `;
        } else if (type.includes('songs-by-user') || (type.includes('user') && type.includes('rejected'))) {
            tr.innerHTML = `
                <td>${row.nick}</td>
                <td><strong>${row.canciones_cantadas || row.canciones_rechazadas || row.cantidad}</strong></td>
            `;
        } else if (type.includes('hourly')) {
            tr.innerHTML = `
                <td>${row.hora}:00</td>
                <td><strong>${row.canciones_cantadas || row.cantidad}</strong></td>
            `;
        } else if (type.includes('inactive')) {
            tr.innerHTML = `
                <td>${row.nick}</td>
                <td>${row.mesa_nombre || 'N/A'}</td>
                <td><span class="bees-badge bees-badge-warning">Sin consumo</span></td>
            `;
        } else if (type.includes('songs') || type.includes('products')) {
            // Generic handler for top-songs, top-products, top-rejected-songs
            const cantidad = row.cantidad || row.cantidad_total || row.veces_cantada || row.veces_rechazada || row.count;
            tr.innerHTML = `
                <td>#${index + 1}</td>
                <td>${row.nombre || row.titulo}</td>
                <td><strong>${cantidad}</strong></td>
            `;
        }
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    container.appendChild(table);

    if (data.length > 20) {
        const moreInfo = document.createElement('p');
        moreInfo.style.fontSize = '12px';
        moreInfo.style.color = 'var(--page-text-secondary)';
        moreInfo.textContent = `Mostrando 20 de ${data.length} registros`;
        container.appendChild(moreInfo);
    }
}

function renderReportMetrics(data, container) {
    const metricsDiv = document.createElement('div');
    metricsDiv.style.display = 'grid';
    metricsDiv.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
    metricsDiv.style.gap = '16px';

    Object.entries(data).forEach(([key, value]) => {
        const card = document.createElement('div');
        card.style.background = 'var(--page-input-bg)';
        card.style.padding = '16px';
        card.style.borderRadius = '12px';
        card.style.textAlign = 'center';
        card.style.borderLeft = '4px solid var(--bees-yellow)';

        const label = document.createElement('div');
        label.style.fontSize = '12px';
        label.style.fontWeight = '600';
        label.style.color = 'var(--page-text-secondary)';
        label.style.textTransform = 'uppercase';
        label.style.marginBottom = '8px';
        label.textContent = key.replace(/_/g, ' ');

        const valueDiv = document.createElement('div');
        valueDiv.style.fontSize = '24px';
        valueDiv.style.fontWeight = '700';
        valueDiv.style.color = 'var(--bees-yellow)';
        valueDiv.textContent = typeof value === 'number' && (key.includes('ingreso') || key.includes('total'))
            ? `$${parseFloat(value).toFixed(2)}`
            : value;

        card.appendChild(label);
        card.appendChild(valueDiv);
        metricsDiv.appendChild(card);
    });

    container.appendChild(metricsDiv);
}
