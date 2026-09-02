// Inventory Page Module - BEES Style
// Manejo: lista de productos, creación, edición, compras, stock de seguridad e historial de gastos

// Flag para prevenir que el diálogo de archivos se abra múltiples veces
let isUploadingImage = false;
let inventoryListenersAttached = false;
let editingProductId = null;
let allProducts = [];

async function loadInventoryPage() {
    const inventoryContainer = document.getElementById('inventory');
    if (!inventoryContainer) return;

    try {
        inventoryContainer.innerHTML = '';
        inventoryListenersAttached = false;

        // Encabezado
        const header = document.createElement('div');
        header.className = 'bees-header';
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        header.style.flexWrap = 'wrap';
        header.style.gap = '15px';
        header.innerHTML = `
            <div style="display: flex; align-items: center; gap: 16px;">
                <div class="bees-header-icon">📦</div>
                <div class="bees-header-content">
                    <h1>Inventario</h1>
                    <p>Gestión de productos, stock de seguridad y traslados entre sedes</p>
                </div>
            </div>
            <button class="bees-btn bees-btn-primary" id="btn-open-transfer-modal" style="display: flex; align-items: center; gap: 8px; font-weight: 600; padding: 10px 18px; border-radius: 8px; box-shadow: 0 4px 12px rgba(108,92,231,0.35);">
                🔄 Trasladar Stock
            </button>
        `;
        inventoryContainer.appendChild(header);

        // Contenedor de rejilla para tarjetas
        const mainContainer = document.createElement('div');
        mainContainer.style.display = 'grid';
        mainContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(380px, 1fr))';
        mainContainer.style.gap = '24px';
        mainContainer.style.marginBottom = '30px';

        // 1. Tarjeta de crear/editar producto
        const createCard = document.createElement('div');
        createCard.className = 'bees-card';
        createCard.id = 'product-form-card';
        createCard.innerHTML = `
            <div class="bees-card-header">
                <div class="bees-card-icon" id="form-card-icon">➕</div>
                <div class="bees-card-header-content">
                    <h3 id="form-card-title">Crear Producto</h3>
                    <p id="form-card-subtitle">Agrega nuevos artículos al local</p>
                </div>
            </div>
            <form id="create-product-form">
                <div class="bees-form-group">
                    <label for="product-name">Nombre del Producto</label>
                    <input type="text" id="product-name" name="nombre" placeholder="Ej: Cerveza" required>
                </div>
                <div class="bees-form-group">
                    <label for="product-category">Categoría</label>
                    <input type="text" id="product-category" name="categoria" placeholder="Ej: Bebidas">
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                    <div class="bees-form-group">
                        <label for="product-cost">Costo Inicial ($)</label>
                        <input type="number" id="product-cost" name="costo" placeholder="0.00" step="0.01" required>
                    </div>
                    <div class="bees-form-group">
                        <label for="product-price">Precio Venta ($)</label>
                        <input type="number" id="product-price" name="valor" placeholder="0.00" step="0.01" required>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                    <div class="bees-form-group">
                        <label for="product-stock">Stock Inicial</label>
                        <input type="number" id="product-stock" name="stock" placeholder="0" value="0" required>
                    </div>
                    <div class="bees-form-group">
                        <label for="product-security-stock">Stock de Seguridad</label>
                        <input type="number" id="product-security-stock" name="stock_seguridad" placeholder="0" value="0" required>
                    </div>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button type="submit" class="bees-btn bees-btn-primary" style="flex: 1;" id="form-submit-btn">✅ Crear Producto</button>
                    <button type="button" class="bees-btn bees-btn-secondary" style="display: none;" id="form-cancel-btn" onclick="cancelProductEdit()">Cancelar</button>
                </div>
            </form>
        `;
        mainContainer.appendChild(createCard);

        // 2. Tarjeta de Registrar Compra
        const purchaseCard = document.createElement('div');
        purchaseCard.className = 'bees-card';
        purchaseCard.innerHTML = `
            <div class="bees-card-header">
                <div class="bees-card-icon">🛒</div>
                <div class="bees-card-header-content">
                    <h3>Registrar Compra</h3>
                    <p>Incrementa el stock de un producto existente</p>
                </div>
            </div>
            <form id="register-purchase-form">
                <div class="bees-form-group">
                    <label for="purchase-product-id">Producto</label>
                    <select id="purchase-product-id" name="producto_id" required style="width: 100%; background: var(--page-input-bg); color: var(--page-text); border: 1px solid rgba(255,255,255,0.1); padding: 10px; border-radius: 8px; outline: none; cursor: pointer;">
                        <option value="">Selecciona un producto...</option>
                    </select>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                    <div class="bees-form-group">
                        <label for="purchase-quantity">Cantidad</label>
                        <input type="number" id="purchase-quantity" name="cantidad" placeholder="0" min="1" required>
                    </div>
                    <div class="bees-form-group">
                        <label for="purchase-price">Precio Compra ($)</label>
                        <input type="number" id="purchase-price" name="precio_compra" placeholder="0.00" step="0.01" min="0.01" required>
                    </div>
                </div>
                <div class="bees-form-group">
                    <label for="purchase-provider">Proveedor</label>
                    <input type="text" id="purchase-provider" name="proveedor" placeholder="Ej: Distribuidora Central">
                </div>
                <button type="submit" class="bees-btn bees-btn-success" style="width: 100%;">📥 Registrar Compra</button>
            </form>
        `;
        mainContainer.appendChild(purchaseCard);

        // 3. Tarjeta de historial de compras y traslados
        const historyCard = document.createElement('div');
        historyCard.className = 'bees-card';
        historyCard.innerHTML = `
            <div class="bees-card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div class="bees-card-icon">💸</div>
                    <div class="bees-card-header-content">
                        <h3 id="history-card-title">Movimientos</h3>
                        <p id="history-card-subtitle">Compras y traslados</p>
                    </div>
                </div>
                <div style="display: flex; gap: 6px;">
                    <button type="button" id="tab-btn-purchases" class="bees-btn bees-btn-primary" style="font-size: 11px; padding: 5px 9px;" onclick="switchInventoryHistoryTab('purchases')">🛒 Compras</button>
                    <button type="button" id="tab-btn-transfers" class="bees-btn bees-btn-secondary" style="font-size: 11px; padding: 5px 9px;" onclick="switchInventoryHistoryTab('transfers')">🔄 Traslados</button>
                </div>
            </div>
            <div id="container-purchases-history" style="overflow-x: auto; max-height: 285px; margin-top: 10px;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: var(--page-text-secondary);">
                            <th style="padding: 8px 4px;">Producto</th>
                            <th style="padding: 8px 4px; text-align: center;">Cant</th>
                            <th style="padding: 8px 4px; text-align: right;">Costo U.</th>
                            <th style="padding: 8px 4px; text-align: right;">Total</th>
                            <th style="padding: 8px 4px; padding-left: 8px;">Fecha</th>
                        </tr>
                    </thead>
                    <tbody id="purchase-history-tbody">
                        <tr><td colspan="5" style="text-align: center; color: var(--page-text-secondary); padding: 20px;">Cargando historial...</td></tr>
                    </tbody>
                </table>
            </div>
            <div id="container-transfers-history" style="overflow-x: auto; max-height: 285px; margin-top: 10px; display: none;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: var(--page-text-secondary);">
                            <th style="padding: 8px 4px;">Tipo</th>
                            <th style="padding: 8px 4px;">Producto</th>
                            <th style="padding: 8px 4px; text-align: center;">Cant</th>
                            <th style="padding: 8px 4px;">Origen/Destino</th>
                            <th style="padding: 8px 4px; padding-left: 8px;">Fecha</th>
                        </tr>
                    </thead>
                    <tbody id="transfer-history-tbody">
                        <tr><td colspan="5" style="text-align: center; color: var(--page-text-secondary); padding: 20px;">Cargando traslados...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        mainContainer.appendChild(historyCard);

        // 4. Tarjeta de lista de productos (Ancho completo)
        const productsCard = document.createElement('div');
        productsCard.className = 'bees-card';
        productsCard.style.gridColumn = '1 / -1';
        productsCard.innerHTML = `
            <div class="bees-card-header" style="margin-bottom: 20px;">
                <div class="bees-card-icon">📋</div>
                <div class="bees-card-header-content">
                    <h3>Catálogo de Productos</h3>
                    <p>Visualización y administración de existencias</p>
                </div>
            </div>
            <ul id="product-list" style="list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
                <!-- Dinámico -->
            </ul>
        `;
        mainContainer.appendChild(productsCard);

        // Inyectar Modal de Traslado de Stock si no existe
        if (!document.getElementById('transfer-stock-modal')) {
            const transferModal = document.createElement('div');
            transferModal.id = 'transfer-stock-modal';
            transferModal.className = 'modal-overlay';
            transferModal.innerHTML = `
                <div class="card modal-card-medium" style="background: #18142a; border: 1px solid #6c5ce7; border-radius: 12px; padding: 24px; max-width: 480px; width: 90%;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 style="color: #fff; margin: 0; font-size: 1.2em; display: flex; align-items: center; gap: 8px;">
                            🔄 <span>Trasladar Stock entre Sedes</span>
                        </h3>
                        <button type="button" onclick="closeTransferModal()" style="background: none; border: none; color: #a29bfe; font-size: 24px; cursor: pointer;">&times;</button>
                    </div>
                    <form id="transfer-stock-form">
                        <div class="bees-form-group" style="margin-bottom: 14px;">
                            <label style="color: #a29bfe; font-size: 13px; font-weight: 600;">Sede Destino</label>
                            <select id="transfer-dest-local" required style="width: 100%; background: #1e1738; color: #fff; border: 1px solid rgba(255,255,255,0.2); padding: 10px; border-radius: 8px; outline: none; cursor: pointer;">
                                <option value="">Selecciona sede destino...</option>
                            </select>
                        </div>
                        <div class="bees-form-group" style="margin-bottom: 14px;">
                            <label style="color: #a29bfe; font-size: 13px; font-weight: 600;">Producto a Trasladar</label>
                            <select id="transfer-product-id" required style="width: 100%; background: #1e1738; color: #fff; border: 1px solid rgba(255,255,255,0.2); padding: 10px; border-radius: 8px; outline: none; cursor: pointer;">
                                <option value="">Selecciona producto...</option>
                            </select>
                        </div>
                        <div class="bees-form-group" style="margin-bottom: 14px;">
                            <label style="color: #a29bfe; font-size: 13px; font-weight: 600;">Cantidad a Transferir</label>
                            <input type="number" id="transfer-quantity" min="1" required style="width: 100%; background: #1e1738; color: #fff; border: 1px solid rgba(255,255,255,0.2); padding: 10px; border-radius: 8px;" placeholder="Cantidad">
                            <small id="transfer-stock-available" style="color: #81ecec; display: block; margin-top: 4px; font-size: 12px;"></small>
                        </div>
                        <div class="bees-form-group" style="margin-bottom: 18px;">
                            <label style="color: #a29bfe; font-size: 13px; font-weight: 600;">Notas / Motivo (Opcional)</label>
                            <input type="text" id="transfer-notes" placeholder="Ej: Reabastecimiento de inventario" style="width: 100%; background: #1e1738; color: #fff; border: 1px solid rgba(255,255,255,0.2); padding: 10px; border-radius: 8px;">
                        </div>
                        <div style="display: flex; gap: 12px;">
                            <button type="submit" class="bees-btn bees-btn-primary" style="flex: 1;">✅ Confirmar Traslado</button>
                            <button type="button" class="bees-btn bees-btn-secondary" onclick="closeTransferModal()">Cancelar</button>
                        </div>
                    </form>
                </div>
            `;
            document.body.appendChild(transferModal);
        }

        inventoryContainer.appendChild(mainContainer);

        // Cargar productos y compras en paralelo
        const products = await apiFetch('/productos/');
        allProducts = products;
        
        const productList = document.getElementById('product-list');
        renderProducts(products, productList);
        
        // Cargar dropdown
        populatePurchaseDropdown(products);

        // Cargar historial de compras y traslados
        try {
            const purchases = await apiFetch('/productos/compras');
            renderPurchases(purchases);
        } catch (err) {
            console.error("Error al cargar historial de compras:", err);
        }

        try {
            const transfers = await apiFetch('/productos/traslados');
            renderTransfers(transfers);
        } catch (err) {
            console.error("Error al cargar historial de traslados:", err);
        }

        // Setup listeners
        setupInventoryListeners();
    } catch (error) {
        const inventoryContainer = document.getElementById('inventory');
        if (inventoryContainer) {
            inventoryContainer.innerHTML = `
                <div class="bees-alert bees-alert-danger">
                    <span class="bees-alert-icon">❌</span>
                    <div>Error al cargar inventario: ${error.message}</div>
                </div>
            `;
        }
        showNotification(`Error: ${error.message}`, 'error');
    }
}

function populatePurchaseDropdown(products) {
    const select = document.getElementById('purchase-product-id');
    if (!select) return;
    select.innerHTML = '<option value="">Selecciona un producto...</option>';
    products.forEach(p => {
        if (p.is_active) {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.nombre} (Stock: ${p.stock})`;
            select.appendChild(opt);
        }
    });
}

function renderProducts(products, productList) {
    productList.innerHTML = '';

    if (products.length === 0) {
        const emptyItem = document.createElement('div');
        emptyItem.style.gridColumn = '1 / -1';
        emptyItem.innerHTML = `
            <div class="bees-alert bees-alert-info">
                <span class="bees-alert-icon">ℹ️</span>
                <div>No hay productos en este establecimiento. ¡Crea el primero!</div>
            </div>
        `;
        productList.appendChild(emptyItem);
        return;
    }

    products.sort((a, b) => {
        if (a.is_active === b.is_active) {
            return a.nombre.localeCompare(b.nombre);
        }
        return a.is_active ? -1 : 1;
    });

    products.forEach(product => {
        const isLowStock = product.stock <= product.stock_seguridad;

        const stockBadgeClass = product.stock === 0
            ? 'bees-badge-danger'
            : isLowStock
                ? 'bees-badge-warning'
                : 'bees-badge-success';

        const statusBadge = product.is_active
            ? '<span class="bees-badge bees-badge-success">✓ Activo</span>'
            : '<span class="bees-badge bees-badge-danger">✗ Inactivo</span>';

        const toggleButtonClass = product.is_active ? 'btn-deactivate' : 'btn-activate';
        const toggleButtonText = product.is_active ? '❌ Desactivar' : '✅ Activar';

        // Animación sutil si es stock bajo
        const pulsingStyle = (product.is_active && isLowStock) 
            ? 'border: 1px solid rgba(243, 156, 18, 0.4); box-shadow: 0 0 10px rgba(243, 156, 18, 0.15);' 
            : '';

        const warningAlertHtml = (product.is_active && isLowStock)
            ? `<div class="pulsing-low-stock" style="color: #f39c12; font-size: 11px; font-weight: bold; margin-top: 6px; display: flex; align-items: center; gap: 4px;">
                ⚠️ Alerta: Stock de Seguridad (Mínimo: ${product.stock_seguridad})
               </div>`
            : '';

        const li = document.createElement('li');
        li.style.padding = '16px';
        li.style.background = 'var(--page-input-bg)';
        li.style.borderRadius = '12px';
        li.style.borderLeft = product.is_active 
            ? (isLowStock ? '4px solid #f39c12' : '4px solid var(--bees-green)') 
            : '4px solid var(--bees-red)';
        if (pulsingStyle) li.setAttribute('style', li.getAttribute('style') + pulsingStyle);

        li.innerHTML = `
            <div style="margin-bottom: 12px;">
                <div style="font-weight: 600; color: var(--page-text); margin-bottom: 4px; font-size: 16px; display: flex; justify-content: space-between; align-items: center;">
                    <span>${product.nombre}</span>
                    <span class="bees-badge ${stockBadgeClass}">${product.stock} uds</span>
                </div>
                <div style="font-size: 13px; color: var(--page-text-secondary); margin-bottom: 8px;">
                    ${product.categoria || 'General'}
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
                    ${statusBadge}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
                    <div><span style="color: var(--page-text-secondary);">Costo:</span> <strong style="color: var(--page-text);">$${(product.costo || 0).toFixed(2)}</strong></div>
                    <div><span style="color: var(--page-text-secondary);">Venta:</span> <strong style="color: var(--bees-yellow);">$${product.valor.toFixed(2)}</strong></div>
                </div>
                ${warningAlertHtml}
            </div>
            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px;">
                <button class="bees-btn bees-btn-success bees-btn-small upload-img-btn" data-id="${product.id}" style="padding: 4px 8px; font-size: 11px;">🖼️ Imagen</button>
                <button class="bees-btn bees-btn-info bees-btn-small btn-edit" data-id="${product.id}" style="padding: 4px 8px; font-size: 11px;">✏️ Editar</button>
                <button class="bees-btn bees-btn-info bees-btn-small ${toggleButtonClass}" data-id="${product.id}" style="padding: 4px 8px; font-size: 11px;">${toggleButtonText}</button>
                <button class="bees-btn bees-btn-danger bees-btn-small btn-delete" data-id="${product.id}" style="padding: 4px 8px; font-size: 11px;">🗑️ Eliminar</button>
            </div>
        `;
        productList.appendChild(li);
    });
}

function renderPurchases(purchases) {
    const tbody = document.getElementById('purchase-history-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!purchases || purchases.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--page-text-secondary); padding: 20px;">Sin compras registradas.</td></tr>`;
        return;
    }

    purchases.forEach(compra => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        
        const dateStr = new Date(compra.fecha).toLocaleDateString('es-CO', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });

        tr.innerHTML = `
            <td style="padding: 8px 4px; font-weight: 500; color: var(--page-text);">${compra.producto ? compra.producto.nombre : 'Insumo'}</td>
            <td style="padding: 8px 4px; text-align: center; color: var(--page-text-secondary);">${compra.cantidad}</td>
            <td style="padding: 8px 4px; text-align: right; color: var(--page-text-secondary);">$${parseFloat(compra.precio_compra).toFixed(2)}</td>
            <td style="padding: 8px 4px; text-align: right; font-weight: 600; color: var(--bees-yellow);">$${parseFloat(compra.total_costo).toFixed(2)}</td>
            <td style="padding: 8px 4px; padding-left: 8px; color: var(--page-text-secondary); font-size: 11px;">${dateStr}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function handleCreateProduct(event, form) {
    event.preventDefault();
    const formData = new FormData(form);
    const productData = Object.fromEntries(formData.entries());

    productData.costo = parseFloat(productData.costo);
    productData.valor = parseFloat(productData.valor);
    productData.stock = parseInt(productData.stock, 10);
    productData.stock_seguridad = parseInt(productData.stock_seguridad, 10) || 0;

    try {
        if (editingProductId) {
            // Actualizar producto existente
            const result = await apiFetch(`/productos/${editingProductId}`, {
                method: 'PUT',
                body: JSON.stringify(productData)
            });
            showNotification(`✏️ Producto '${result.nombre}' actualizado.`, 'success');
            cancelProductEdit();
        } else {
            // Crear producto nuevo
            const result = await apiFetch('/productos/', {
                method: 'POST',
                body: JSON.stringify(productData)
            });
            showNotification(`✅ Producto '${result.nombre}' creado.`, 'success');
            form.reset();
        }
        loadInventoryPage();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function handleRegisterPurchase(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const purchaseData = Object.fromEntries(formData.entries());

    purchaseData.producto_id = parseInt(purchaseData.producto_id, 10);
    purchaseData.cantidad = parseInt(purchaseData.cantidad, 10);
    purchaseData.precio_compra = parseFloat(purchaseData.precio_compra);

    try {
        const result = await apiFetch('/productos/compras', {
            method: 'POST',
            body: JSON.stringify(purchaseData)
        });
        showNotification(`📥 Compra registrada exitosamente.`, 'success');
        form.reset();
        loadInventoryPage();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function startProductEdit(productId) {
    const product = allProducts.find(p => p.id == productId);
    if (!product) return;

    editingProductId = productId;
    
    // Cambiar visuales del formulario
    document.getElementById('form-card-icon').textContent = '✏️';
    document.getElementById('form-card-title').textContent = 'Editar Producto';
    document.getElementById('form-card-subtitle').textContent = 'Modifica los valores del producto';
    document.getElementById('form-submit-btn').textContent = '💾 Guardar Cambios';
    document.getElementById('form-cancel-btn').style.display = 'block';

    // Rellenar valores
    document.getElementById('product-name').value = product.nombre;
    document.getElementById('product-category').value = product.categoria || '';
    document.getElementById('product-cost').value = product.costo;
    document.getElementById('product-price').value = product.valor;
    document.getElementById('product-stock').value = product.stock;
    document.getElementById('product-security-stock').value = product.stock_seguridad || 0;

    // Desplazar suavemente hasta el formulario
    document.getElementById('product-form-card').scrollIntoView({ behavior: 'smooth' });
}

function cancelProductEdit() {
    editingProductId = null;
    
    const form = document.getElementById('create-product-form');
    if (form) form.reset();

    // Resetear visuales
    document.getElementById('form-card-icon').textContent = '➕';
    document.getElementById('form-card-title').textContent = 'Crear Producto';
    document.getElementById('form-card-subtitle').textContent = 'Agrega nuevos artículos al local';
    document.getElementById('form-submit-btn').textContent = '✅ Crear Producto';
    document.getElementById('form-cancel-btn').style.display = 'none';
}

async function handleToggleProductActive(event) {
    const button = event.target;
    if (!button.matches('.btn-activate, .btn-deactivate')) return;

    const productId = button.dataset.id;
    const activate = button.classList.contains('btn-activate');
    const endpoint = `/productos/${productId}/${activate ? 'activate' : 'deactivate'}`;

    try {
        const result = await apiFetch(endpoint, { method: 'POST' });
        showNotification(
            `${activate ? '✅ Activado' : '❌ Desactivado'}: '${result.nombre}'`,
            'success'
        );
        loadInventoryPage();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function handleDeleteProduct(event) {
    const button = event.target;
    if (!button.matches('.btn-delete')) return;
    const productId = button.dataset.id;

    if (!confirm('⚠️ ¿Eliminar este producto permanentemente? No se puede deshacer.')) return;

    try {
        await apiFetch(`/productos/${productId}`, { method: 'DELETE' });
        showNotification('🗑️ Producto eliminado.', 'info');
        loadInventoryPage();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function handleProductImageUpload(event) {
    const fileInput = event.target;
    const productId = fileInput.dataset.productId;
    if (!fileInput.files || fileInput.files.length === 0 || !productId) {
        delete fileInput.dataset.productId;
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    showNotification('⬆️ Subiendo imagen...', 'info', 10000);

    try {
        isUploadingImage = true;

        const response = await fetch(`${API_BASE_URL}/productos/${productId}/upload-image`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${apiKey}` },
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al subir la imagen.');
        }

        showNotification('🖼️ Imagen actualizada.', 'success');

        fileInput.value = '';
        delete fileInput.dataset.productId;

        setTimeout(async () => {
            isUploadingImage = false;

            const inventoryPage = document.getElementById('inventory');
            if (inventoryPage && inventoryPage.classList.contains('active')) {
                const products = await apiFetch('/productos/');
                const productList = document.getElementById('product-list');
                if (productList) {
                    renderProducts(products, productList);
                }
            }
        }, 300);

    } catch (error) {
        showNotification(error.message, 'error');
        fileInput.value = '';
        delete fileInput.dataset.productId;
        setTimeout(() => {
            isUploadingImage = false;
        }, 300);
    }
}

function setupInventoryListeners() {
    if (inventoryListenersAttached) return;

    const createForm = document.getElementById('create-product-form');
    const purchaseForm = document.getElementById('register-purchase-form');
    const productList = document.getElementById('product-list');
    const fileInput = document.getElementById('product-image-upload');

    if (createForm) {
        createForm.addEventListener('submit', (e) =>
            handleCreateProduct(e, e.target)
        );
    }

    if (purchaseForm) {
        purchaseForm.addEventListener('submit', handleRegisterPurchase);
    }

    if (productList) {
        productList.addEventListener('click', (e) => {
            if (
                e.target.classList.contains('btn-activate') ||
                e.target.classList.contains('btn-deactivate')
            ) {
                handleToggleProductActive(e);
                return;
            }

            if (e.target.classList.contains('btn-edit')) {
                const productId = e.target.dataset.id;
                startProductEdit(productId);
                return;
            }

            if (e.target.classList.contains('btn-delete')) {
                handleDeleteProduct(e);
                return;
            }

            if (e.target.classList.contains('upload-img-btn')) {
                if (isUploadingImage) return;

                const productId = e.target.dataset.id;
                if (fileInput) {
                    fileInput.dataset.productId = productId;
                    fileInput.click();
                }
            }
        });
    }

    if (fileInput) {
        fileInput.removeEventListener('change', handleProductImageUpload);
        fileInput.addEventListener('change', handleProductImageUpload);
        fileInput.value = '';
    }

    const btnOpenTransfer = document.getElementById('btn-open-transfer-modal');
    if (btnOpenTransfer) {
        btnOpenTransfer.addEventListener('click', openTransferModal);
    }

    const transferForm = document.getElementById('transfer-stock-form');
    if (transferForm) {
        transferForm.addEventListener('submit', handleTransferStockSubmit);
    }

    const transferProductSelect = document.getElementById('transfer-product-id');
    if (transferProductSelect) {
        transferProductSelect.addEventListener('change', (e) => {
            const selectedOpt = e.target.options[e.target.selectedIndex];
            const stock = selectedOpt ? selectedOpt.dataset.stock : null;
            const stockHelp = document.getElementById('transfer-stock-available');
            const qtyInput = document.getElementById('transfer-quantity');
            if (stockHelp && stock !== null && stock !== undefined) {
                stockHelp.textContent = `Stock disponible en origen: ${stock} unidades`;
                if (qtyInput) {
                    qtyInput.max = stock;
                    qtyInput.value = Math.min(1, parseInt(stock, 10) || 1);
                }
            } else if (stockHelp) {
                stockHelp.textContent = '';
            }
        });
    }

    inventoryListenersAttached = true;
}

function switchInventoryHistoryTab(tab) {
    const btnPurchases = document.getElementById('tab-btn-purchases');
    const btnTransfers = document.getElementById('tab-btn-transfers');
    const containerPurchases = document.getElementById('container-purchases-history');
    const containerTransfers = document.getElementById('container-transfers-history');
    const title = document.getElementById('history-card-title');

    if (tab === 'purchases') {
        if (btnPurchases) btnPurchases.className = 'bees-btn bees-btn-primary';
        if (btnTransfers) btnTransfers.className = 'bees-btn bees-btn-secondary';
        if (containerPurchases) containerPurchases.style.display = 'block';
        if (containerTransfers) containerTransfers.style.display = 'none';
        if (title) title.textContent = 'Compras e Insumos';
    } else {
        if (btnPurchases) btnPurchases.className = 'bees-btn bees-btn-secondary';
        if (btnTransfers) btnTransfers.className = 'bees-btn bees-btn-primary';
        if (containerPurchases) containerPurchases.style.display = 'none';
        if (containerTransfers) containerTransfers.style.display = 'block';
        if (title) title.textContent = 'Traslados entre Sedes';
    }
}

function renderTransfers(transfers) {
    const tbody = document.getElementById('transfer-history-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (!transfers || transfers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--page-text-secondary); padding: 20px;">No hay traslados registrados para esta sede.</td></tr>';
        return;
    }

    const currentLocalId = parseInt(sessionStorage.getItem('active_local_id'), 10);

    transfers.forEach(t => {
        const isOutgoing = t.local_origen_id === currentLocalId;
        const typeBadge = isOutgoing
            ? '<span class="bees-badge bees-badge-warning">📤 Salida</span>'
            : '<span class="bees-badge bees-badge-success">📥 Entrada</span>';
        
        const otherLocal = isOutgoing
            ? `Hacia: <b>${t.local_destino_nombre || ('Sede #' + t.local_destino_id)}</b>`
            : `Desde: <b>${t.local_origen_nombre || ('Sede #' + t.local_origen_id)}</b>`;

        const dateStr = new Date(t.fecha).toLocaleDateString('es-CO', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });

        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        row.innerHTML = `
            <td style="padding: 8px 4px;">${typeBadge}</td>
            <td style="padding: 8px 4px; font-weight: 500;">${t.producto_nombre}</td>
            <td style="padding: 8px 4px; text-align: center; font-weight: 700;">${t.cantidad}</td>
            <td style="padding: 8px 4px; font-size: 12px; color: var(--page-text-secondary);">${otherLocal}</td>
            <td style="padding: 8px 4px; padding-left: 8px; font-size: 12px; color: var(--page-text-secondary);">${dateStr}</td>
        `;
        tbody.appendChild(row);
    });
}

async function openTransferModal() {
    const modal = document.getElementById('transfer-stock-modal');
    if (!modal) return;

    const currentLocalId = parseInt(sessionStorage.getItem('active_local_id'), 10);
    const destSelect = document.getElementById('transfer-dest-local');
    const prodSelect = document.getElementById('transfer-product-id');
    const qtyInput = document.getElementById('transfer-quantity');
    const notesInput = document.getElementById('transfer-notes');
    const stockHelp = document.getElementById('transfer-stock-available');

    if (qtyInput) qtyInput.value = '';
    if (notesInput) notesInput.value = '';
    if (stockHelp) stockHelp.textContent = '';

    // Cargar sedes destino
    if (destSelect) {
        destSelect.innerHTML = '<option value="">Cargando sedes destino...</option>';
        try {
            const locales = await apiFetch('/saas/locales');
            destSelect.innerHTML = '<option value="">Selecciona sede destino...</option>';
            if (locales) {
                locales.forEach(loc => {
                    if (loc.id !== currentLocalId) {
                        const opt = document.createElement('option');
                        opt.value = loc.id;
                        opt.textContent = `${loc.nombre}`;
                        destSelect.appendChild(opt);
                    }
                });
            }
        } catch (err) {
            destSelect.innerHTML = '<option value="">Error cargando sedes</option>';
        }
    }

    // Cargar productos con stock disponible del local actual
    if (prodSelect) {
        prodSelect.innerHTML = '<option value="">Selecciona producto...</option>';
        if (allProducts) {
            allProducts.forEach(p => {
                if (p.is_active && p.stock > 0) {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = `${p.nombre} (Stock actual: ${p.stock})`;
                    opt.dataset.stock = p.stock;
                    prodSelect.appendChild(opt);
                }
            });
        }
    }

    modal.classList.add('active');
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

function closeTransferModal() {
    const modal = document.getElementById('transfer-stock-modal');
    if (modal) {
        modal.classList.remove('active');
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
}

async function handleTransferStockSubmit(e) {
    e.preventDefault();
    const currentLocalId = parseInt(sessionStorage.getItem('active_local_id'), 10);
    const destLocalId = parseInt(document.getElementById('transfer-dest-local').value, 10);
    const productId = parseInt(document.getElementById('transfer-product-id').value, 10);
    const quantity = parseInt(document.getElementById('transfer-quantity').value, 10);
    const notes = document.getElementById('transfer-notes').value.trim();

    if (!destLocalId) {
        showNotification('Por favor selecciona una sede de destino.', 'error');
        return;
    }
    if (!productId) {
        showNotification('Por favor selecciona el producto a trasladar.', 'error');
        return;
    }
    if (!quantity || quantity <= 0) {
        showNotification('La cantidad debe ser mayor a 0.', 'error');
        return;
    }

    try {
        const payload = {
            local_origen_id: currentLocalId,
            local_destino_id: destLocalId,
            producto_id: productId,
            cantidad: quantity,
            notas: notes || null
        };

        const result = await apiFetch('/productos/traslado', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        showNotification(`✅ Traslado exitoso: ${quantity} unidades transferidas.`, 'success');
        closeTransferModal();

        // Recargar inventario e historial
        loadInventoryPage();
    } catch (err) {
        showNotification(`Error en traslado: ${err.message}`, 'error');
    }
}

