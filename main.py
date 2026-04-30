# El orden completo del archivo queda así:
# imports y setup
# app = FastAPI(...)
# mount static
# mount templates

# # Páginas
# GET /
# GET /catalogo
# GET /producto/{slug}
# GET /carrito
# GET /cuenta

# # API productos
# GET /api/productos
# GET /api/productos/{slug}
# GET /api/categorias

# # API órdenes
# POST /api/ordenes          ← ya lo tenés
# GET  /api/ordenes/usuario/{user_id}   ← nuevo

# # API auth
# POST /api/auth/login       ← nuevo
# POST /api/auth/registro    ← nuevo




from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from db.connection import test_connection
from decimal import Decimal
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    from db.connection import Base, engine, get_db
    import db.models  # noqa
    Base.metadata.create_all(bind=engine)
    
    # Seed inicial si no hay datos
    from db.models import Category, User
    with get_db() as db:
        if db.query(Category).count() == 0:
            cats = [
                Category(name="Tazas y mugs",  slug="tazas-mugs",   position=1),
                Category(name="Bowls",          slug="bowls",         position=2),
                Category(name="Jarrones",       slug="jarrones",      position=3),
                Category(name="Platos",         slug="platos",        position=4),
                Category(name="Macetas",        slug="macetas",       position=5),
                Category(name="Piezas únicas",  slug="piezas-unicas", position=6),
            ]
            db.add_all(cats)
            print("✅ Categorías creadas")

        if db.query(User).count() == 0:
            from services.auth import hash_password
            from db.models import UserRole
            admin = User(
                name="Admin",
                email="admin@ceramics.com",
                password=hash_password("admin1234"),
                role=UserRole.admin,
            )
            db.add(admin)
            print("✅ Admin creado")

    test_connection()
    print("✅ DB lista")
    yield

app = FastAPI(lifespan=lifespan)

# Archivos estáticos (CSS, JS, imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates HTML
templates = Jinja2Templates(directory="templates")

# ── Páginas ────────────────────────────────────────────────────────

IS_PRODUCTION = os.getenv("APP_ENV") == "production"

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "is_production": IS_PRODUCTION,
    })

@app.get("/catalogo", response_class=HTMLResponse)
async def catalogo(request: Request):
    return templates.TemplateResponse("catalogo.html", {
        "request": request,
        "is_production": IS_PRODUCTION,
    })

@app.get("/producto/{slug}", response_class=HTMLResponse)
async def producto(request: Request, slug: str):
    from services.products import get_product_by_slug
    product = get_product_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return templates.TemplateResponse("producto.html", {
        "request": request,
        "product": product,
        "is_production": IS_PRODUCTION,
    })


@app.get("/carrito", response_class=HTMLResponse)
async def carrito(request: Request):
    return templates.TemplateResponse("carrito.html", {
        "request": request,
        "is_production": IS_PRODUCTION,
    })

@app.get("/cuenta", response_class=HTMLResponse)
async def cuenta(request: Request):
    return templates.TemplateResponse("cuenta.html", {
        "request": request,
        "is_production": IS_PRODUCTION,
    })


# ── API de datos ────────────────────────────────────────────────────

@app.get("/api/productos")
async def api_productos(
    categoria: str | None = None,
    tecnica: str | None = None,
    buscar: str | None = None,
    destacados: bool = False,
):
    from services.products import get_products
    products = get_products(
        category_slug=categoria,
        technique=tecnica,
        search=buscar,
        only_featured=destacados,
    )
    return [
        {
            "id":          p.id,
            "nombre":      p.name,
            "slug":        p.slug,
            "precio":      float(p.price),
            "stock":       p.stock,
            "descripcion": p.description,
            "tecnica":     p.technique.value if p.technique else None,
            "dimensiones": p.dimensions,
            "destacado":   p.is_featured,
            "categoria":   p.category.name if p.category else None,
            "imagen":      _primary_image(p),
            "imagenes":    [img.url for img in p.images],
        }
        for p in products
    ]


@app.get("/api/productos/{slug}")
async def api_producto(slug: str):
    from services.products import get_product_by_slug
    p = get_product_by_slug(slug)
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {
        "id":          p.id,
        "nombre":      p.name,
        "slug":        p.slug,
        "precio":      float(p.price),
        "stock":       p.stock,
        "descripcion": p.description,
        "tecnica":     p.technique.value if p.technique else None,
        "dimensiones": p.dimensions,
        "peso":        p.weight_grams,
        "destacado":   p.is_featured,
        "categoria":   p.category.name if p.category else None,
        "imagen":      _primary_image(p),
        "imagenes":    [img.url for img in p.images],
    }


@app.get("/api/categorias")
async def api_categorias():
    from services.products import get_all_categories
    cats = get_all_categories()
    return [{"id": c.id, "nombre": c.name, "slug": c.slug} for c in cats]


from pydantic import BaseModel

class ItemOrden(BaseModel):
    producto_id: int
    cantidad:    int
    precio:      float
    nombre:      str

class OrdenRequest(BaseModel):
    nombre:    str
    email:     str
    telefono:  str = ""
    direccion: str
    ciudad:    str
    provincia: str
    cp:        str
    notas:     str = ""
    items:     list[ItemOrden]


@app.post("/api/ordenes")
async def crear_orden(data: OrdenRequest):
    from services.orders import create_order_from_cart
    from services import cart as cart_service
    from db.models import User
    from db.connection import get_db

    # Por ahora creamos un usuario guest si no está logueado
    # En el próximo paso agregamos auth real
    # Obtener o crear usuario
    user_id = None
    with get_db() as db:
        from db.models import User
        user = db.query(User).filter(User.email == data.email).first()
        if user:
            user_id = user.id
        else:
            from services.auth import hash_password
            import secrets
            new_user = User(
                name=data.nombre,
                email=data.email,
                password=hash_password(secrets.token_hex(16)),
            )
            db.add(new_user)
            db.flush()
            user_id = new_user.id

    # Crear orden
    with get_db() as db:
        from db.models import Order, OrderItem, OrderStatus, Product
        subtotal = sum(i.precio * i.cantidad for i in data.items)
        envio    = 0 ### if subtotal >= 50000 else 3500
        total    = subtotal + envio

        orden = Order(
            user_id           = user_id,
            status            = OrderStatus.pending,
            subtotal          = Decimal(str(subtotal)),
            shipping_cost     = Decimal(str(envio)),
            total             = Decimal(str(total)),
            shipping_name     = data.nombre,
            shipping_address  = data.direccion,
            shipping_city     = data.ciudad,
            shipping_province = data.provincia,
            shipping_zip      = data.cp,
            shipping_phone    = data.telefono,
            notes             = data.notas,
        )
        db.add(orden)
        db.flush()

        for item in data.items:
            db.add(OrderItem(
                order_id     = orden.id,
                product_id   = item.producto_id,
                quantity      = item.cantidad,
                unit_price   = Decimal(str(item.precio)),
                subtotal     = Decimal(str(item.precio * item.cantidad)),
                product_name = item.nombre,
            ))

            producto = db.query(Product).filter(Product.id == item.producto_id).first()
            if producto:
                producto.stock = max(0, producto.stock - item.cantidad)

        db.flush()

        # Generar preferencia de MercadoPago
        try:
            from services.payments import crear_preferencia
            items_db = db.query(OrderItem).filter(OrderItem.order_id == orden.id).all()
            preferencia = crear_preferencia(orden, items_db)
            orden.mp_preference_id = preferencia["id"]
            # mp_url = preferencia["sandbox_url"]
            mp_url = preferencia["init_point"]
        except Exception as e:
            print(f"⚠️ Error MP: {e}")
            mp_url = None

        # Enviar email de confirmación
        try:
            from services.emails import enviar_confirmacion_pedido
            enviar_confirmacion_pedido(
                to_email  = data.email,
                to_name   = data.nombre,
                order_id  = orden.id,
                items     = [
                    {
                        "nombre":   i.nombre,
                        "cantidad": i.cantidad,
                        "subtotal": i.precio * i.cantidad,
                    }
                    for i in data.items
                ],
                subtotal  = subtotal,
                shipping  = envio,
                total     = total,
                direccion = data.direccion,
                ciudad    = data.ciudad,
                provincia = data.provincia,
            )
            print(f"✅ Email enviado a {data.email}")
        except Exception as e:
            print(f"⚠️ Error email: {e}")            

        return {
            "orden_id": orden.id,
            "total":    total,
            "mp_url":   mp_url,
        }


# ── Helper ──────────────────────────────────────────────────────────

# def _primary_image(product) -> str:
#     from services.products import get_primary_image_url
#     return get_primary_image_url(product, fallback="")

def _primary_image(product) -> str:
    from services.products import get_primary_image_url
    url = get_primary_image_url(product, fallback="")
    print(f"🖼️ imagen de {product.slug}: '{url}' | imágenes: {len(product.images)}")
    return url



class LoginRequest(BaseModel):
    email:    str
    password: str

class RegistroRequest(BaseModel):
    nombre:   str
    email:    str
    password: str


@app.post("/api/auth/login")
async def api_login(data: LoginRequest):
    from services.auth import login
    from services.tokens import crear_token
    user = login(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")
    token = crear_token(user.id, user.role.value)
    return {
        "id":     user.id,
        "nombre": user.name,
        "email":  user.email,
        "rol":    user.role.value,
        "token":  token,
    }


@app.post("/api/auth/registro")
async def api_registro(data: RegistroRequest):
    from services.auth import register
    try:
        user = register(
            name=data.nombre,
            email=data.email,
            password=data.password,
        )
        return {
            "id":     user.id,
            "nombre": user.name,
            "email":  user.email,
            "rol":    user.role.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ordenes/usuario/{user_id}")
async def api_ordenes_usuario(user_id: int, request: Request):
    from services.orders import get_orders_by_user
    orders = get_orders_by_user(user_id)
    return [
        {
            "id":         o.id,
            "status":     o.status.value,
            "total":      float(o.total),
            "created_at": o.created_at.isoformat(),
            "items": [
                {
                    "product_name": i.product_name,
                    "quantity":     i.quantity,
                    "subtotal":     float(i.subtotal),
                }
                for i in o.items
            ],
        }
        for o in orders
    ]    

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


def verificar_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    from services.tokens import es_admin_token
    if not credentials or not es_admin_token(credentials.credentials):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    from services.tokens import verificar_token
    return verificar_token(credentials.credentials)

def verificar_owner(credentials: HTTPAuthorizationCredentials = Depends(security)):
    from services.tokens import verificar_token
    if not credentials:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    payload = verificar_token(credentials.credentials)
    if not payload or payload.get("rol") != "owner":
        raise HTTPException(status_code=403, detail="Acceso reservado al owner.")
    return payload    


# ── Páginas admin ──────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


@app.get("/admin/productos", response_class=HTMLResponse)
async def admin_productos(request: Request):
    return templates.TemplateResponse("admin/productos.html", {"request": request})


@app.get("/admin/ordenes", response_class=HTMLResponse)
async def admin_ordenes(request: Request):
    return templates.TemplateResponse("admin/ordenes.html", {"request": request})

@app.get("/admin/usuarios", response_class=HTMLResponse)
async def admin_usuarios(request: Request):
    return templates.TemplateResponse("admin/usuarios.html", {"request": request})

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    return templates.TemplateResponse("admin/settings.html", {"request": request}) 
   
@app.get("/api/admin/settings/check")
async def check_owner(owner=Depends(verificar_owner)):
    return {"ok": True}

# ── API usuarios ───────────────────────────────────────────────────

@app.get("/api/admin/usuarios")
async def api_get_usuarios(admin=Depends(verificar_admin)):
    from db.connection import get_db
    from db.models import User
    with get_db() as db:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return [
            {
                "id":         u.id,
                "nombre":     u.name,
                "email":      u.email,
                "rol":        u.role.value,
                "activo":     u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]


@app.put("/api/admin/usuarios/{user_id}")
async def api_actualizar_usuario(
    user_id: int,
    body: dict,
    admin=Depends(verificar_admin)
):
    from db.connection import get_db
    from db.models import User, UserRole
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        if "rol" in body:
            user.role = UserRole(body["rol"])
        if "activo" in body:
            user.is_active = body["activo"]
        if "nombre" in body:
            user.name = body["nombre"]
    return {"ok": True}


@app.delete("/api/admin/usuarios/{user_id}")
async def api_borrar_usuario(
    user_id: int,
    admin=Depends(verificar_admin)
):
    from db.connection import get_db
    from db.models import User, Order
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        tiene_ordenes = db.query(Order).filter(Order.user_id == user_id).first()
        if tiene_ordenes:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede borrar '{user.name}' porque tiene pedidos asociados."
            )
        db.delete(user)
    return {"ok": True}

# ── API admin ──────────────────────────────────────────────────────

@app.get("/api/admin/stats")
async def api_admin_stats(admin=Depends(verificar_admin)):
    from db.connection import get_db
    from db.models import Product, Order, User, OrderStatus
    with get_db() as db:
        total_productos = db.query(Product).filter(Product.is_active == True).count()
        total_ordenes   = db.query(Order).count()
        ordenes_pending = db.query(Order).filter(Order.status == OrderStatus.pending).count()
        ordenes_paid    = db.query(Order).filter(Order.status == OrderStatus.paid).count()
        total_usuarios  = db.query(User).count()
        from sqlalchemy import func
        revenue = db.query(func.sum(Order.total)).filter(
            Order.status.in_([OrderStatus.paid, OrderStatus.delivered])
        ).scalar() or 0
    return {
        "productos":      total_productos,
        "ordenes":        total_ordenes,
        "pendientes":     ordenes_pending,
        "pagadas":        ordenes_paid,
        "usuarios":       total_usuarios,
        "revenue":        float(revenue),
    }


@app.get("/api/admin/ordenes")
async def api_admin_ordenes(
    status: str | None = None,
    admin=Depends(verificar_admin)
):
    from services.orders import get_all_orders
    orders = get_all_orders(status=status)
    return [
        {
            "id":       o.id,
            "status":   o.status.value,
            "total":    float(o.total),
            "nombre":   o.shipping_name,
            "email":    "",
            "ciudad":   o.shipping_city,
            "created_at": o.created_at.isoformat(),
            "items": [
                {
                    "product_name": i.product_name,
                    "quantity":     i.quantity,
                    "subtotal":     float(i.subtotal),
                }
                for i in o.items
            ],
        }
        for o in orders
    ]


@app.put("/api/admin/ordenes/{orden_id}/status")
async def api_update_orden_status(
    orden_id: int,
    body: dict,
    admin=Depends(verificar_admin)
):
    from services.orders import update_order_status
    orden = update_order_status(orden_id, body["status"])
    return {"ok": True, "status": orden.status.value}


@app.get("/api/admin/productos")
async def api_admin_productos(admin=Depends(verificar_admin)):
    from services.products import get_products
    products = get_products(only_active=False)
    return [
        {
            "id":          p.id,
            "nombre":      p.name,
            "descripcion": p.description,
            "slug":        p.slug,
            "precio":      float(p.price),
            "stock":       p.stock,
            "activo":      p.is_active,
            "destacado":   p.is_featured,
            "categoria":   p.category.name if p.category else None,
            "imagen":      _primary_image(p),
            "tecnica":     p.technique,
            "dimensiones": p.dimensions,
            "peso": p.weight_grams,
        }
        for p in products
    ]


@app.post("/api/admin/productos")
async def api_crear_producto(
    request: Request,
    admin=Depends(verificar_admin)
):
    from fastapi import Form, UploadFile, File
    form = await request.form()
    nombre      = form.get("nombre")
    precio      = float(form.get("precio", 0))
    stock       = int(form.get("stock", 0))
    descripcion = form.get("descripcion", "")
    categoria   = form.get("categoria_id")
    tecnica     = form.get("tecnica", "")
    dimensiones = form.get("dimensiones", "")
    peso        = form.get("peso_gramos")
    destacado   = form.get("destacado") == "true"

    image_files = []
    for key, val in form.multi_items():
        if key == "imagenes" and hasattr(val, "read"):
            content = await val.read()
            if content:
                image_files.append((content, val.filename))

    from services.products import create_product
    product = create_product(
        name=nombre,
        price=precio,
        description=descripcion,
        stock=stock,
        category_id=int(categoria) if categoria else None,
        technique=tecnica or None,
        dimensions=dimensiones,
        weight_grams=int(peso) if peso else None,
        is_featured=destacado,
        image_files=image_files,
    )
    return {"ok": True, "id": product.id, "slug": product.slug}

@app.post("/api/admin/productos/{product_id}/imagenes")
async def api_actualizar_imagenes(
    product_id: int,
    request: Request,
    admin=Depends(verificar_admin)
):
    print(f"📸 Actualizando imágenes del producto {product_id}")
    from services.images import delete_product_images, add_image_to_product
    from services.storage import upload_image
    from db.connection import get_db
    from db.models import Product

    form = await request.form()
    image_files = []
    for key, val in form.multi_items():
        if key == "imagenes" and hasattr(val, "read"):
            content = await val.read()
            if content:
                image_files.append((content, val.filename))

    if not image_files:
        raise HTTPException(status_code=400, detail="No se enviaron imágenes.")

    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")
        slug = product.slug

    # Borrar imágenes anteriores
    delete_product_images(product_id)

    # Subir nuevas
    for position, (file_bytes, filename) in enumerate(image_files):
        result = upload_image(file_bytes, slug, position)
        add_image_to_product(
            product_id=product_id,
            url=result["url"],
            public_id=result["public_id"],
            position=position,
            alt_text=slug,
        )

    return {"ok": True, "imagenes": len(image_files)}

@app.put("/api/admin/productos/{product_id}")
async def api_actualizar_producto(
    product_id: int,
    body: dict,
    admin=Depends(verificar_admin)
):

    from services.products import update_product, toggle_product_active
    from db.connection import get_db
    from db.models import Product

    print(f"📝 Actualizando producto {product_id} con: {body}")

    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")

        if "activo" in body:
            product.is_active = body["activo"]
        if "name" in body:
            product.name = body["name"]
        if "price" in body:
            from decimal import Decimal
            product.price = Decimal(str(body["price"]))
        if "description" in body:
            product.description = body["description"]
        if "stock" in body:
            product.stock = int(body["stock"])
        if "dimensions" in body:
            product.dimensions = body["dimensions"]
        if "weight_grams" in body:
            product.weight_grams = body["weight_grams"]
        if "is_featured" in body:
            product.is_featured = body["is_featured"]
        if "technique" in body:
            from db.models import TechniqueType
            product.technique = TechniqueType(body["technique"]) if body["technique"] else None
        if "category_id" in body and body["category_id"]:
            product.category_id = int(body["category_id"])

    return {"ok": True}

@app.delete("/api/admin/productos/{product_id}")
async def api_borrar_producto(
    product_id: int,
    admin=Depends(verificar_admin)
):
    from db.connection import get_db
    from db.models import Product, OrderItem
    from services.images import delete_product_images

    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado.")

        # Verificar si tiene pedidos
        tiene_pedidos = db.query(OrderItem).filter(
            OrderItem.product_id == product_id
        ).first()

        if tiene_pedidos:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede borrar '{product.name}' porque tiene pedidos asociados."
            )

        # Borrar imágenes del storage
        delete_product_images(product_id)

        # Borrar producto
        db.delete(product)

    return {"ok": True}


# ── Páginas de retorno MercadoPago ─────────────────────────────────

@app.get("/pago/exitoso", response_class=HTMLResponse)
async def pago_exitoso(request: Request):
    return templates.TemplateResponse("pago_exitoso.html", {"request": request})


@app.get("/pago/fallido", response_class=HTMLResponse)
async def pago_fallido(request: Request):
    return templates.TemplateResponse("pago_fallido.html", {"request": request})


@app.get("/pago/pendiente", response_class=HTMLResponse)
async def pago_pendiente(request: Request):
    return templates.TemplateResponse("pago_pendiente.html", {"request": request})


# ── Webhook MercadoPago ────────────────────────────────────────────

@app.post("/api/webhook/mp")
async def webhook_mp(request: Request):
    data = await request.json()
    print(f"📩 Webhook MP: {data}")

    from services.payments import procesar_webhook
    from services.orders import confirm_payment

    resultado = procesar_webhook(data)
    if not resultado:
        return {"ok": True}

    if resultado["status"] == "approved":
        confirm_payment(
            mp_payment_id=resultado["payment_id"],
            mp_preference_id="",  # usamos external_reference
        )
        # Actualizar por order_id directamente
        from services.orders import update_order_status
        if resultado["order_id"]:
            update_order_status(resultado["order_id"], "paid")
            print(f"✅ Orden {resultado['order_id']} marcada como pagada")

    return {"ok": True}    