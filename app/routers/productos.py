from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import os
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from decimal import Decimal

from app import crud, schemas, models
from app.database import SessionLocal
from app.auth import verify_token, verify_token_optional, log_admin_action
from app.services import websocket_manager  # Importamos el gestor de websockets

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_active_local_id(request: Request, api_key: Optional[dict]) -> Optional[int]:
    if not api_key:
        local_id = request.query_params.get("local_id")
        if local_id:
            return int(local_id)
        local_id_hdr = request.headers.get("X-Local-ID")
        if local_id_hdr:
            return int(local_id_hdr)
        return None

    role = api_key.get("role")
    if role == "owner":
        selected_id = None
        local_id = request.query_params.get("local_id")
        if local_id:
            selected_id = int(local_id)
        else:
            local_id_hdr = request.headers.get("X-Local-ID")
            if local_id_hdr:
                selected_id = int(local_id_hdr)
        
        # Validar pertenencia del local seleccionado al propietario (owner)
        from app.db.models.usuario_local import UsuarioLocal
        db = SessionLocal()
        try:
            owner = db.query(UsuarioLocal).filter(UsuarioLocal.email == api_key.get("sub")).first()
            if owner:
                owner_local_ids = [l.id for l in owner.locales]
                if selected_id is not None:
                    if selected_id in owner_local_ids:
                        return selected_id
                    else:
                        raise HTTPException(
                            status_code=403,
                            detail="No tienes permiso para acceder a este establecimiento."
                        )
                elif owner.locales:
                    return owner.locales[0].id
        finally:
            db.close()
        return None
    else:
        return api_key.get("local_id")

@router.post("/", response_model=schemas.Producto, summary="Crear un nuevo producto en el catálogo")
async def create_product(request: Request, producto: schemas.ProductoCreate, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Añade un nuevo producto al catálogo del karaoke.
    """
    try:
        local_id = get_active_local_id(request, api_key)
        db_producto = crud.get_producto_by_nombre_and_local(db, nombre=producto.nombre, local_id=local_id)
        if db_producto:
            raise HTTPException(status_code=400, detail="Un producto con este nombre ya existe en este establecimiento.")

        new_product = crud.create_producto(db=db, producto=producto, local_id=local_id)
        log_admin_action(api_key.get("sub"), "create_product", f"Producto: {producto.nombre}, Local: {local_id}")
        # Lanzamos el broadcast como tarea de fondo para evitar que fallos en WS provoquen 500s
        try:
            import asyncio
            asyncio.create_task(websocket_manager.manager.broadcast_product_update())
        except Exception:
            # Si no es posible programar la tarea, lo registramos y seguimos
            import logging
            logging.getLogger(__name__).exception("No se pudo programar broadcast de producto")
        # Convertimos Decimals a float para que el frontend reciba números y pueda usar `.toFixed()`
        return JSONResponse(content=jsonable_encoder(new_product, custom_encoder={Decimal: lambda v: float(v)}))
    except HTTPException:
        # Re-raise HTTP exceptions (client errors)
        raise
    except Exception as e:
        # Log and return a JSON-friendly error so the frontend can parse it
        import logging, traceback
        logging.getLogger(__name__).exception("Error creando producto")
        # As a fallback, also dump the full traceback to a dedicated file so it's easier to find.
        try:
            with open("product_errors.log", "a", encoding="utf-8") as f:
                f.write("--- Product creation exception ---\n")
                traceback.print_exc(file=f)
                f.write("\n")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Error interno al crear el producto.")

@router.get("/", response_model=List[schemas.Producto], summary="Obtener el catálogo de productos (para admin y usuarios)")
def get_products(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), api_key: Optional[dict] = Depends(verify_token_optional)):
    """
    Devuelve una lista de todos los productos disponibles en el catálogo.
    - Si se provee una API Key de admin válida, devuelve todos los productos.
    - Si no, devuelve solo los productos activos y con stock.
    """
    local_id = get_active_local_id(request, api_key)
    
    # If api_key is provided and valid (admin), return full catalog; otherwise return only active items with stock
    if not api_key:
        query = db.query(models.Producto).filter(models.Producto.is_active == True, models.Producto.stock > 0)
        if local_id is not None:
            query = query.filter(models.Producto.local_id == local_id)
        else:
            query = query.filter(models.Producto.local_id.is_(None))
        productos = query.offset(skip).limit(limit).all()
    else:
        productos = crud.get_productos(db, skip=skip, limit=limit, local_id=local_id)

    # Convertimos Decimals a float para que el frontend reciba números y pueda usar `.toFixed()`
    return JSONResponse(content=jsonable_encoder(productos, custom_encoder={Decimal: lambda v: float(v)}))

@router.put("/{producto_id}", response_model=schemas.Producto, summary="Actualizar un producto existente")
async def update_product(request: Request, producto_id: int, producto: schemas.ProductoCreate, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Actualiza todos los detalles de un producto existente en el catálogo.
    """
    local_id = get_active_local_id(request, api_key)
    db_producto = crud.get_producto_by_id(db, producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if db_producto.local_id is not None and db_producto.local_id != local_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este producto.")

    db_producto = crud.update_producto(db, producto_id=producto_id, producto_update=producto)
    log_admin_action(api_key.get("sub"), "update_product", f"ID: {producto_id}, Nombre: {producto.nombre}, Local: {local_id}")
    await websocket_manager.manager.broadcast_product_update() # Notificamos
    return JSONResponse(content=jsonable_encoder(db_producto, custom_encoder={Decimal: lambda v: float(v)}))

@router.delete("/{producto_id}", status_code=204, summary="Eliminar un producto del catálogo")
async def delete_product(request: Request, producto_id: int, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Elimina un producto del catálogo permanentemente.
    """
    local_id = get_active_local_id(request, api_key)
    db_producto = crud.get_producto_by_id(db, producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if db_producto.local_id is not None and db_producto.local_id != local_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este producto.")

    deleted_product, message = crud.delete_producto(db, producto_id=producto_id)
    log_admin_action(api_key.get("sub"), "delete_product", f"ID: {producto_id}, Local: {local_id}")
    
    # Si deleted_product es None y el mensaje indica que no se encontró
    if deleted_product is None and "no encontrado" in message.lower():
        raise HTTPException(status_code=404, detail=message)
    
    await websocket_manager.manager.broadcast_product_update() # Notificamos
    return Response(status_code=204)

@router.put("/{producto_id}/edit-price", response_model=schemas.Producto, summary="Editar el precio de un producto")
async def edit_product_price(request: Request, producto_id: int, valor_update: schemas.ProductoValorUpdate, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Permite editar el precio de un producto del catálogo.
    """
    local_id = get_active_local_id(request, api_key)
    db_producto = crud.get_producto_by_id(db, producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if db_producto.local_id is not None and db_producto.local_id != local_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este producto.")

    db_producto = crud.update_producto_valor(db, producto_id=producto_id, nuevo_valor=valor_update.valor)
    log_admin_action(api_key.get("sub"), "edit_product_price", f"ID: {producto_id}, Nuevo valor: {valor_update.valor}, Local: {local_id}")
    await websocket_manager.manager.broadcast_product_update() # Notificamos
    return JSONResponse(content=jsonable_encoder(db_producto, custom_encoder={Decimal: lambda v: float(v)}))

@router.post("/{producto_id}/deactivate", response_model=schemas.Producto, summary="Desactivar un producto")
async def deactivate_product(request: Request, producto_id: int, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Desactiva un producto del catálogo para que no pueda ser pedido.
    """
    local_id = get_active_local_id(request, api_key)
    db_producto = crud.get_producto_by_id(db, producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if db_producto.local_id is not None and db_producto.local_id != local_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este producto.")

    db_producto = crud.update_producto_active_status(db, producto_id=producto_id, is_active=False)
    log_admin_action(api_key.get("sub"), "deactivate_product", f"ID: {producto_id}, Local: {local_id}")
    await websocket_manager.manager.broadcast_product_update() # Notificamos
    return JSONResponse(content=jsonable_encoder(db_producto, custom_encoder={Decimal: lambda v: float(v)}))

@router.post("/{producto_id}/activate", response_model=schemas.Producto, summary="Reactivar un producto")
async def activate_product(request: Request, producto_id: int, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Reactiva un producto previamente desactivado.
    """
    local_id = get_active_local_id(request, api_key)
    db_producto = crud.get_producto_by_id(db, producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if db_producto.local_id is not None and db_producto.local_id != local_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este producto.")

    db_producto = crud.update_producto_active_status(db, producto_id=producto_id, is_active=True)
    log_admin_action(api_key.get("sub"), "activate_product", f"ID: {producto_id}, Local: {local_id}")
    await websocket_manager.manager.broadcast_product_update() # Notificamos
    return JSONResponse(content=jsonable_encoder(db_producto, custom_encoder={Decimal: lambda v: float(v)}))

# 📂 Directorio donde se guardarán las imágenes
UPLOAD_DIR = "static/images/productos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/{producto_id}/upload-image", summary="Subir imagen de un producto")
async def upload_product_image(
    request: Request,
    producto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: dict = Depends(verify_token)
):
    """
    **[Admin]** Permite subir una imagen para un producto específico.
    Guarda la imagen en /static/images/productos/ y actualiza su ruta en la base de datos.
    """
    local_id = get_active_local_id(request, api_key)
    db_producto = crud.get_producto_by_id(db, producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    if db_producto.local_id is not None and db_producto.local_id != local_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este producto.")

    # Validar tipo de archivo
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido.")

    # Guardar archivo con un nombre único
    filename = f"producto_{producto_id}{extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Actualizar el producto con la URL de la imagen
    image_url = f"/static/images/productos/{filename}"
    db_producto.imagen_url = image_url
    db.flush()  # Sincronizar cambios en la misma transacción sin hacer commit
    db.refresh(db_producto)  # Obtener datos actualizados de la BD
    db.commit()  # Hacer commit de toda la transacción
    log_admin_action(api_key.get("sub"), "upload_product_image", f"ID: {producto_id}, URL: {image_url}, Local: {local_id}")
    
    # Notificar a los clientes conectados (si usas WebSocket)
    try:
        import asyncio
        asyncio.create_task(websocket_manager.manager.broadcast_product_update())
    except Exception:
        pass

    return JSONResponse(
        content={
            "message": "Imagen subida correctamente.",
            "image_url": image_url
        },
        status_code=200
    )


@router.post("/compras", response_model=schemas.Compra, summary="Registrar compra de un producto (Admin)")
async def create_purchase(request: Request, compra_in: schemas.CompraCreate, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Registra una compra de inventario para un producto, incrementando su stock y actualizando su precio de costo.
    """
    local_id = get_active_local_id(request, api_key)
    if not local_id:
        raise HTTPException(status_code=400, detail="Debe especificar o tener un local activo para registrar compras.")
        
    db_producto = crud.get_producto_by_id(db, compra_in.producto_id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    db_compra = crud.registrar_compra(db, compra_in, local_id=local_id)
    log_admin_action(api_key.get("sub"), "create_purchase", f"Producto ID: {compra_in.producto_id}, Cantidad: {compra_in.cantidad}, Local: {local_id}")
    
    try:
        import asyncio
        asyncio.create_task(websocket_manager.manager.broadcast_product_update())
    except Exception:
        pass
        
    return JSONResponse(content=jsonable_encoder(db_compra, custom_encoder={Decimal: lambda v: float(v)}))


@router.get("/compras", response_model=List[schemas.Compra], summary="Historial de compras de un local (Admin)")
async def list_purchases(request: Request, db: Session = Depends(get_db), api_key: dict = Depends(verify_token)):
    """
    **[Admin]** Devuelve la lista de compras registradas en el local actual.
    """
    local_id = get_active_local_id(request, api_key)
    if not local_id:
        raise HTTPException(status_code=400, detail="Debe especificar o tener un local activo para listar compras.")
        
    compras = crud.get_compras_by_local(db, local_id)
    return JSONResponse(content=jsonable_encoder(compras, custom_encoder={Decimal: lambda v: float(v)}))


@router.post("/traslado", response_model=schemas.saas.TrasladoInventarioOut, summary="Trasladar stock de un producto entre sedes")
async def transfer_product_stock(
    request: Request,
    traslado_in: schemas.saas.TrasladoInventarioCreate,
    db: Session = Depends(get_db),
    api_key: dict = Depends(verify_token)
):
    """
    Traslada stock de un producto desde un local de origen hacia un local de destino del mismo dueño.
    """
    if traslado_in.local_origen_id == traslado_in.local_destino_id:
        raise HTTPException(status_code=400, detail="El local de origen y destino no pueden ser el mismo.")

    if traslado_in.cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad a trasladar debe ser mayor a cero.")

    from app.db.models.local import Local
    from app.db.models.usuario_local import UsuarioLocal
    from app.db.models.producto import Producto
    from app.db.models.traslado_inventario import TrasladoInventario

    # Validar permisos sobre las sedes
    role = api_key.get("role")
    if role == "owner":
        owner = db.query(UsuarioLocal).filter(UsuarioLocal.email == api_key.get("sub")).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Propietario no encontrado.")
        owner_local_ids = [l.id for l in owner.locales]
        if traslado_in.local_origen_id not in owner_local_ids or traslado_in.local_destino_id not in owner_local_ids:
            raise HTTPException(status_code=403, detail="Ambos locales deben pertenecer a tu cuenta.")
    else:
        # Empleado
        emp_local_id = api_key.get("local_id")
        if emp_local_id != traslado_in.local_origen_id:
            raise HTTPException(status_code=403, detail="Solo puedes emitir traslados desde tu local asignado.")

    # Buscar locales
    local_origen = db.query(Local).filter(Local.id == traslado_in.local_origen_id).first()
    local_destino = db.query(Local).filter(Local.id == traslado_in.local_destino_id).first()
    if not local_origen or not local_destino:
        raise HTTPException(status_code=404, detail="Uno de los locales no fue encontrado.")

    # Buscar producto en origen
    producto_origen = db.query(Producto).filter(
        Producto.id == traslado_in.producto_id,
        Producto.local_id == traslado_in.local_origen_id
    ).first()

    if not producto_origen:
        raise HTTPException(status_code=404, detail="El producto no existe en el local de origen.")

    if producto_origen.stock < traslado_in.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente en {local_origen.nombre}. Stock actual: {producto_origen.stock}, Solicitado: {traslado_in.cantidad}"
        )

    # Descontar stock en origen
    producto_origen.stock -= traslado_in.cantidad

    # Buscar o crear producto en destino (por nombre)
    producto_destino = db.query(Producto).filter(
        Producto.local_id == traslado_in.local_destino_id,
        Producto.nombre.ilike(producto_origen.nombre)
    ).first()

    if producto_destino:
        producto_destino.stock += traslado_in.cantidad
        if producto_origen.precio_costo and not producto_destino.precio_costo:
            producto_destino.precio_costo = producto_origen.precio_costo
    else:
        # Crear copia del producto en el local destino con el stock transferido
        producto_destino = Producto(
            nombre=producto_origen.nombre,
            precio=producto_origen.precio,
            precio_costo=producto_origen.precio_costo or 0,
            categoria=producto_origen.categoria or "General",
            stock=traslado_in.cantidad,
            stock_seguridad=producto_origen.stock_seguridad or 0,
            local_id=traslado_in.local_destino_id,
            image_url=producto_origen.image_url,
            is_active=True
        )
        db.add(producto_destino)

    # Crear registro de auditoría de traslado
    user_name = api_key.get("name") or api_key.get("sub") or "Administrador"
    user_id = api_key.get("id")
    traslado = TrasladoInventario(
        local_origen_id=traslado_in.local_origen_id,
        local_destino_id=traslado_in.local_destino_id,
        producto_origen_id=producto_origen.id,
        producto_nombre=producto_origen.nombre,
        cantidad=traslado_in.cantidad,
        costo_unitario=producto_origen.precio_costo or 0,
        usuario_id=user_id,
        usuario_nombre=user_name,
        notas=traslado_in.notas
    )
    db.add(traslado)
    db.commit()
    db.refresh(traslado)

    log_admin_action(
        api_key.get("sub"),
        "transfer_stock",
        f"{traslado_in.cantidad}x {producto_origen.nombre} desde {local_origen.nombre} hacia {local_destino.nombre}"
    )

    try:
        import asyncio
        asyncio.create_task(websocket_manager.manager.broadcast_product_update())
    except Exception:
        pass

    out_data = {
        "id": traslado.id,
        "local_origen_id": traslado.local_origen_id,
        "local_destino_id": traslado.local_destino_id,
        "producto_origen_id": traslado.producto_origen_id,
        "producto_nombre": traslado.producto_nombre,
        "cantidad": traslado.cantidad,
        "costo_unitario": float(traslado.costo_unitario) if traslado.costo_unitario else 0.0,
        "usuario_id": traslado.usuario_id,
        "usuario_nombre": traslado.usuario_nombre,
        "notas": traslado.notas,
        "fecha": traslado.fecha,
        "local_origen_nombre": local_origen.nombre,
        "local_destino_nombre": local_destino.nombre
    }
    return JSONResponse(content=jsonable_encoder(out_data))


@router.get("/traslados", response_model=List[schemas.saas.TrasladoInventarioOut], summary="Historial de traslados de un local")
async def list_transfers(
    request: Request,
    db: Session = Depends(get_db),
    api_key: dict = Depends(verify_token)
):
    """
    Obtiene el historial de traslados (entrantes y salientes) del local activo.
    """
    local_id = get_active_local_id(request, api_key)
    if not local_id:
        raise HTTPException(status_code=400, detail="Debe especificar o tener un local activo para listar traslados.")

    from app.db.models.traslado_inventario import TrasladoInventario
    from app.db.models.local import Local

    traslados = db.query(TrasladoInventario).filter(
        (TrasladoInventario.local_origen_id == local_id) | (TrasladoInventario.local_destino_id == local_id)
    ).order_by(TrasladoInventario.fecha.desc()).limit(100).all()

    locales_map = {l.id: l.nombre for l in db.query(Local).all()}

    results = []
    for t in traslados:
        results.append({
            "id": t.id,
            "local_origen_id": t.local_origen_id,
            "local_destino_id": t.local_destino_id,
            "producto_origen_id": t.producto_origen_id,
            "producto_nombre": t.producto_nombre,
            "cantidad": t.cantidad,
            "costo_unitario": float(t.costo_unitario) if t.costo_unitario else 0.0,
            "usuario_id": t.usuario_id,
            "usuario_nombre": t.usuario_nombre,
            "notas": t.notas,
            "fecha": t.fecha,
            "local_origen_nombre": locales_map.get(t.local_origen_id, f"Local #{t.local_origen_id}"),
            "local_destino_nombre": locales_map.get(t.local_destino_id, f"Local #{t.local_destino_id}")
        })

    return JSONResponse(content=jsonable_encoder(results))