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
        header.innerHTML = `
            <div class="bees-header-icon">📦</div>
            <div class="bees-header-content">
                <h1>Inventario</h1>
                <p>Gestión de productos, stock de seguridad e historial de compras por local</p>
            </div>
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

        // 3. Tarjeta de historial de compras / gastos
        const historyCard = document.createElement('div');
        historyCard.className = 'bees-card';
        historyCard.innerHTML = `
            <div class="bees-card-header">
                <div class="bees-card-icon">💸</div>
                <div class="bees-card-header-content">
                    <h3>Gastos e Insumos</h3>
                    <p>Historial de compras del local</p>
                </div>
            </div>
            <div style="overflow-x: auto; max-height: 285px; margin-top: 10px;">
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

        inventoryContainer.appendChild(mainContainer);

        // Cargar productos y compras en paralelo
        const products = await apiFetch('/productos/');
        allProducts = products;
        
        const productList = document.getElementById('product-list');
        renderProducts(products, productList);
        
        // Cargar dropdown
        populatePurchaseDropdown(products);

        // Cargar historial
        try {
            const purchases = await apiFetch('/productos/compras');
            renderPurchases(purchases);
        } catch (err) {
            console.error("Error al cargar historial de compras:", err);
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

    inventoryListenersAttached = true;
}
