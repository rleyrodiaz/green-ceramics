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
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from db.connection import test_connection
from decimal import Decimal
import os

async def enviar_recordatorios():
    from datetime import datetime, timedelta
    from services.settings_db import get_float, get_setting
    from db.connection import get_db
    from db.models import Order, OrderStatus, PaymentMethod
    from services.emails import enviar_recordatorio_mp, enviar_recordatorio_transfer

    now = datetime.utcnow()
    print(f"⏰ Verificando recordatorios ({now.strftime('%H:%M')})")

    REMINDER_MP_HOURS       = get_float("reminders.mp_hours")
    REMINDER_TRANSFER_HOURS = get_float("reminders.transfer_hours")
    BANK_CBU    = get_setting("bank.cbu")
    BANK_ALIAS  = get_setting("bank.alias")
    BANK_HOLDER = get_setting("bank.holder")

    with get_db() as db:
        # Recordatorio MP
        mp_threshold = now - timedelta(hours=REMINDER_MP_HOURS)
        mp_orders = db.query(Order).filter(
            Order.status == OrderStatus.pending,
            Order.payment_method == PaymentMethod.mp,
            Order.mp_checkout_at.isnot(None),
            Order.mp_checkout_at <= mp_threshold,
            Order.reminder_mp_sent_at.is_(None),
        ).all()
        for o in mp_orders:
            if o.customer_email:
                ok = enviar_recordatorio_mp(o.customer_email, o.shipping_name or "", o.id, float(o.total))
                if ok:
                    o.reminder_mp_sent_at = now
                    print(f"📧 Recordatorio MP → orden #{o.id}")

        # Recordatorio transferencia
        tr_threshold = now - timedelta(hours=REMINDER_TRANSFER_HOURS)
        tr_orders = db.query(Order).filter(
            Order.status == OrderStatus.pending,
            Order.payment_method == PaymentMethod.transfer,
            Order.comprobante_url.is_(None),
            Order.created_at <= tr_threshold,
            Order.reminder_transfer_sent_at.is_(None),
        ).all()
        for o in tr_orders:
            if o.customer_email:
                ok = enviar_recordatorio_transfer(
                    o.customer_email, o.shipping_name or "", o.id, float(o.total),
                    BANK_CBU, BANK_ALIAS, BANK_HOLDER,
                )
                if ok:
                    o.reminder_transfer_sent_at = now
                    print(f"📧 Recordatorio transferencia → orden #{o.id}")


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

    # Auto-migración: columnas nuevas en orders
    from sqlalchemy import text, inspect as sa_inspect
    with engine.connect() as conn:
        cols = [c["name"] for c in sa_inspect(engine).get_columns("orders")]
        if "payment_method" not in cols:
            conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR DEFAULT 'mp'"))
            conn.commit()
            print("✅ Columna payment_method agregada")
        if "comprobante_url" not in cols:
            conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS comprobante_url VARCHAR(500)"))
            conn.commit()
            print("✅ Columna comprobante_url agregada")
        conn.execute(text("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'verifying' AFTER 'pending'"))
        conn.commit()
        for col, coltype in {
            "shipping_method":           "VARCHAR(20)",
            "shipping_branch":           "VARCHAR(200)",
            "tracking_number":           "VARCHAR(100)",
            "factura_numero":            "VARCHAR(50)",
            "factura_fecha":             "TIMESTAMP",
            "customer_email":            "VARCHAR(255)",
            "mp_checkout_at":            "TIMESTAMP",
            "reminder_mp_sent_at":       "TIMESTAMP",
            "reminder_transfer_sent_at": "TIMESTAMP",
            "checkout_session_id":       "VARCHAR(36)",
        }.items():
            if col not in cols:
                conn.execute(text(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {coltype}"))
                conn.commit()
                print(f"✅ Columna orders.{col} agregada")
        conn.execute(text("ALTER TYPE shippingmethod ADD VALUE IF NOT EXISTS 'domicilio'"))
        conn.commit()
        conn.execute(text("ALTER TYPE shippingmethod ADD VALUE IF NOT EXISTS 'sucursal'"))
        conn.commit()
        conn.execute(text("ALTER TYPE shippingmethod ADD VALUE IF NOT EXISTS 'personal'"))
        conn.commit()

    # Crear tabla activity_logs si no existe + nuevas columnas
    import db.models  # noqa
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        log_cols = [c["name"] for c in sa_inspect(engine).get_columns("activity_logs")]
        new_log_cols = {
            "session_id":  "VARCHAR(36)",
            "country":     "VARCHAR(60)",
            "city":        "VARCHAR(60)",
            "device_type": "VARCHAR(20)",
            "browser":     "VARCHAR(60)",
            "os":          "VARCHAR(60)",
            "referrer":    "TEXT",
        }
        for col, coltype in new_log_cols.items():
            if col not in log_cols:
                conn.execute(text(f"ALTER TABLE activity_logs ADD COLUMN IF NOT EXISTS {col} {coltype}"))
                conn.commit()
                print(f"✅ Columna activity_logs.{col} agregada")
        # Fix: upgrade referrer from VARCHAR(300) to TEXT if needed
        ref_col = next((c for c in sa_inspect(engine).get_columns("activity_logs") if c["name"] == "referrer"), None)
        if ref_col and "varchar" in str(ref_col.get("type", "")).lower():
            conn.execute(text("ALTER TABLE activity_logs ALTER COLUMN referrer TYPE TEXT"))
            conn.commit()
            print("✅ activity_logs.referrer ampliado a TEXT")

    # Agregar ON DELETE CASCADE a FK constraints si todavía no lo tienen
    _fk_updates = [
        # (child_table, column, parent_table, constraint_name, on_delete)
        ("orders",         "user_id",    "users",    "orders_user_id_fkey",          "CASCADE"),
        ("order_items",    "order_id",   "orders",   "order_items_order_id_fkey",    "CASCADE"),
        ("order_items",    "product_id", "products", "order_items_product_id_fkey",  "RESTRICT"),
        ("product_images", "product_id", "products", "product_images_product_id_fkey","CASCADE"),
    ]
    _deltype_map = {"CASCADE": "c", "RESTRICT": "r", "SET NULL": "n"}
    with engine.connect() as conn:
        for child, col, parent, cname, on_del in _fk_updates:
            target = _deltype_map[on_del]
            conn.execute(text(f"""
                DO $$
                DECLARE v_name text;
                BEGIN
                    SELECT conname INTO v_name
                    FROM pg_constraint
                    WHERE conrelid  = '{child}'::regclass
                      AND confrelid = '{parent}'::regclass
                      AND contype   = 'f'
                      AND confdeltype != '{target}';
                    IF v_name IS NOT NULL THEN
                        EXECUTE 'ALTER TABLE {child} DROP CONSTRAINT ' || quote_ident(v_name);
                        ALTER TABLE {child} ADD CONSTRAINT {cname}
                            FOREIGN KEY ({col}) REFERENCES {parent}(id) ON DELETE {on_del};
                    END IF;
                END $$;
            """))
            conn.commit()
    print("✅ FK constraints OK")

    # Seed app_settings con valores de EVs (solo si la clave no existe)
    from services.settings_db import seed_defaults
    from config.settings import (
        BANK_CBU, BANK_ALIAS, BANK_HOLDER,
        SHIPPING_DOMICILIO, SHIPPING_SUCURSAL, SHIPPING_FREE_THRESHOLD,
        REMINDER_MP_HOURS, REMINDER_TRANSFER_HOURS,
    )
    import os
    seed_defaults({
        "shipping.domicilio":           str(SHIPPING_DOMICILIO),
        "shipping.sucursal":            str(SHIPPING_SUCURSAL),
        "shipping.free_threshold":      str(SHIPPING_FREE_THRESHOLD),
        "reminders.mp_hours":           str(REMINDER_MP_HOURS),
        "reminders.transfer_hours":     str(REMINDER_TRANSFER_HOURS),
        "bank.cbu":                     BANK_CBU,
        "bank.alias":                   BANK_ALIAS,
        "bank.holder":                  BANK_HOLDER,
        "notifications.visit_email":    "false",
        "notifications.visit_email_to": os.getenv("EMAIL_OWNER", "rleyrodiaz@hotmail.com"),
    })
    print("✅ App settings OK")

    test_connection()
    print("✅ DB lista")

    scheduler.add_job(enviar_recordatorios, "interval", hours=1, id="recordatorios", replace_existing=True)
    scheduler.start()
    print("✅ Scheduler iniciado")

    yield

    scheduler.shutdown()

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
    nombre:          str
    email:           str
    telefono:        str = ""
    direccion:       str = ""
    ciudad:          str = ""
    provincia:       str = ""
    cp:              str = ""
    notas:           str = ""
    payment_method:  str = "mp"
    shipping_method: str = "domicilio"
    shipping_branch: str = ""
    items:           list[ItemOrden]


@app.post("/api/ordenes")
async def crear_orden(data: OrdenRequest, request: Request):
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
        from db.models import Order, OrderItem, OrderStatus, Product, ShippingMethod
        from services.settings_db import get_int
        ship_domicilio      = get_int("shipping.domicilio")
        ship_sucursal       = get_int("shipping.sucursal")
        ship_free_threshold = get_int("shipping.free_threshold")

        subtotal = sum(i.precio * i.cantidad for i in data.items)

        if subtotal >= ship_free_threshold:
            envio = 0
        elif data.shipping_method == "sucursal":
            envio = ship_sucursal
        else:
            envio = ship_domicilio

        total = subtotal + envio

        from db.models import PaymentMethod
        orden = Order(
            user_id           = user_id,
            status            = OrderStatus.pending,
            payment_method    = PaymentMethod(data.payment_method),
            shipping_method   = ShippingMethod(data.shipping_method),
            shipping_branch   = data.shipping_branch or None,
            customer_email    = data.email,
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

        # Generar preferencia de MercadoPago (solo si paga con MP)
        mp_url = None
        if data.payment_method == "mp":
            try:
                from services.payments import crear_preferencia
                items_db   = db.query(OrderItem).filter(OrderItem.order_id == orden.id).all()
                _sid       = request.headers.get("X-Session-ID", "")
                preferencia = crear_preferencia(orden, items_db, session_id=_sid)
                orden.mp_preference_id    = preferencia["id"]
                orden.mp_checkout_at      = __import__("datetime").datetime.utcnow()
                orden.checkout_session_id = _sid or None
                mp_url = preferencia["init_point"]
            except Exception as e:
                print(f"⚠️ Error MP: {e}")
                raise HTTPException(status_code=500, detail="Error al procesar el pago. Intentá de nuevo.")

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

        _orden_id = orden.id
        _result   = {
            "orden_id":       orden.id,
            "total":          total,
            "mp_url":         mp_url,
            "payment_method": data.payment_method,
        }

    from services.activity import log as alog
    alog("order_created", "order", _orden_id, f"Orden #{_orden_id} — {data.nombre}",
         detail=f"Total: ${total:,.0f} | Método: {data.payment_method}",
         user_id=user_id, user_name=data.nombre, request=request)

    return _result

# ── Helper ──────────────────────────────────────────────────────────

# def _primary_image(product) -> str:
#     from services.products import get_primary_image_url
#     return get_primary_image_url(product, fallback="")

def _primary_image(product) -> str:
    from services.products import get_primary_image_url
    url = get_primary_image_url(product, fallback="")
    # print(f"🖼️ imagen de {product.slug}: '{url}' | imágenes: {len(product.images)}")
    return url



class LoginRequest(BaseModel):
    email:    str
    password: str

class RegistroRequest(BaseModel):
    nombre:   str
    email:    str
    password: str


@app.post("/api/auth/login")
async def api_login(data: LoginRequest, request: Request):
    from services.auth import login
    from services.tokens import crear_token
    user = login(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")

    # Capturar valores antes de cualquier manipulación del objeto ORM
    uid, uname, uemail, urol = user.id, user.name, user.email, user.role.value
    token = crear_token(uid, urol)

    from services.activity import log as alog
    alog("user_login", "user", uid, uemail, user_id=uid, user_name=uname, request=request)
    return {
        "id":     uid,
        "nombre": uname,
        "email":  uemail,
        "rol":    urol,
        "token":  token,
    }


@app.post("/api/auth/registro")
async def api_registro(data: RegistroRequest, request: Request):
    from services.auth import register
    try:
        user = register(
            name=data.nombre,
            email=data.email,
            password=data.password,
        )
        uid, uname, uemail, urol = user.id, user.name, user.email, user.role.value
        from services.activity import log as alog
        from services.emails import enviar_bienvenida
        alog("user_registered", "user", uid, uemail, user_id=uid, user_name=uname, request=request)
        enviar_bienvenida(uemail, uname)
        return {
            "id":     uid,
            "nombre": uname,
            "email":  uemail,
            "rol":    urol,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ordenes/usuario/{user_id}")
async def api_ordenes_usuario(user_id: int, request: Request):
    from services.orders import get_orders_by_user
    orders = get_orders_by_user(user_id)
    return [
        {
            "id":             o.id,
            "status":         o.status.value,
            "total":          float(o.total),
            "created_at":     o.created_at.isoformat(),
            "payment_method":  o.payment_method.value  if o.payment_method  else "mp",
            "comprobante_url": o.comprobante_url,
            "shipping_method": o.shipping_method.value if o.shipping_method else "domicilio",
            "shipping_branch": o.shipping_branch,
            "tracking_number": o.tracking_number,
            "factura_numero":  o.factura_numero,
            "shipping_cost":   float(o.shipping_cost) if o.shipping_cost else 0,
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


@app.get("/api/admin/settings/values")
async def api_get_settings(owner=Depends(verificar_owner)):
    from services.settings_db import get_all_settings
    return get_all_settings()


@app.put("/api/admin/settings/values/{key:path}")
async def api_set_setting(key: str, body: dict, owner=Depends(verificar_owner)):
    from services.settings_db import set_setting
    set_setting(key, str(body.get("value", "")))
    return {"ok": True}


@app.get("/api/admin/activity")
async def api_activity_log(
    page:        int = 1,
    page_size:   int = 50,
    action:      str = None,
    entity_type: str = None,
    session_id:  str = None,
    date_from:   str = None,
    date_to:     str = None,
    owner=Depends(verificar_owner),
):
    from db.connection import get_db
    from db.models import ActivityLog
    from sqlalchemy import desc

    with get_db() as db:
        q = db.query(ActivityLog)

        if action:
            q = q.filter(ActivityLog.action == action)
        if entity_type:
            q = q.filter(ActivityLog.entity_type == entity_type)
        if session_id:
            q = q.filter(ActivityLog.session_id == session_id)
        if date_from:
            from datetime import datetime
            q = q.filter(ActivityLog.timestamp >= datetime.fromisoformat(date_from))
        if date_to:
            from datetime import datetime
            q = q.filter(ActivityLog.timestamp <= datetime.fromisoformat(date_to + "T23:59:59"))

        total = q.count()
        rows  = q.order_by(desc(ActivityLog.timestamp)) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size) \
                 .all()

        return {
            "total": total,
            "page":  page,
            "pages": max(1, -(-total // page_size)),
            "rows": [
                {
                    "id":          r.id,
                    "timestamp":   r.timestamp.isoformat(),
                    "session_id":  r.session_id,
                    "user_id":     r.user_id,
                    "user_name":   r.user_name,
                    "action":      r.action,
                    "entity_type": r.entity_type,
                    "entity_id":   r.entity_id,
                    "entity_desc": r.entity_desc,
                    "detail":      r.detail,
                    "country":     r.country,
                    "city":        r.city,
                    "device_type": r.device_type,
                    "browser":     r.browser,
                    "os":          r.os,
                    "referrer":    r.referrer,
                }
                for r in rows
            ],
        }

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
            "id":             o.id,
            "status":         o.status.value,
            "total":          float(o.total),
            "nombre":         o.shipping_name,
            "email":          "",
            "ciudad":         o.shipping_city,
            "created_at":     o.created_at.isoformat(),
            "payment_method":  o.payment_method.value  if o.payment_method  else "mp",
            "comprobante_url": o.comprobante_url,
            "shipping_method": o.shipping_method.value if o.shipping_method else "domicilio",
            "shipping_branch": o.shipping_branch,
            "tracking_number": o.tracking_number,
            "factura_numero":  o.factura_numero,
            "factura_fecha":   o.factura_fecha.isoformat() if o.factura_fecha else None,
            "shipping_cost":   float(o.shipping_cost)  if o.shipping_cost  else 0,
            "subtotal":        float(o.subtotal),
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
    request: Request,
    admin=Depends(verificar_admin)
):
    from services.orders import update_order_status
    from services.activity import log as alog
    from db.connection import get_db as _gdb
    from db.models import Order as _O
    from services.emails import enviar_pago_confirmado, enviar_pedido_enviado, enviar_pedido_entregado

    if body["status"] == "shipped":
        with _gdb() as db:
            o = db.query(_O).filter(_O.id == orden_id).first()
            if not o or not (o.tracking_number or "").strip():
                raise HTTPException(status_code=400, detail="Se requiere número de seguimiento para marcar como enviada.")

    orden = update_order_status(orden_id, body["status"])
    alog("order_status_changed", "order", orden_id, f"Orden #{orden_id}",
         detail=f"→ {body['status']}", user_id=int(admin.get("sub", 0)), request=request)

    try:
        with _gdb() as db:
            o = db.query(_O).filter(_O.id == orden_id).first()
            if o and o.customer_email:
                if body["status"] == "paid":
                    enviar_pago_confirmado(
                        o.customer_email, o.shipping_name or "", o.id,
                        [{"nombre": i.product_name, "cantidad": i.quantity, "subtotal": float(i.subtotal)} for i in o.items],
                        float(o.subtotal), float(o.shipping_cost), float(o.total),
                        o.shipping_method.value if o.shipping_method else "domicilio",
                        o.shipping_address or "", o.shipping_branch or "",
                    )
                elif body["status"] == "shipped":
                    enviar_pedido_enviado(
                        o.customer_email, o.shipping_name or "", o.id,
                        o.shipping_method.value if o.shipping_method else "domicilio",
                        o.shipping_address or "", o.shipping_branch or "",
                        o.tracking_number or "",
                    )
                elif body["status"] == "delivered":
                    enviar_pedido_entregado(o.customer_email, o.shipping_name or "", o.id)
    except Exception as e:
        print(f"⚠️ Error email status change: {e}")

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
    request: Request,
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
        nombre_producto = product.name

    from services.activity import log as alog
    alog("product_updated", "product", product_id, nombre_producto,
         user_id=int(admin.get("sub", 0)), request=request)
    return {"ok": True}

@app.delete("/api/admin/productos/{product_id}")
async def api_borrar_producto(
    product_id: int,
    request: Request,
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

        nombre_producto = product.name
        delete_product_images(product_id)
        db.delete(product)

    from services.activity import log as alog
    alog("product_deleted", "product", product_id, nombre_producto,
         user_id=int(admin.get("sub", 0)), request=request)
    return {"ok": True}


# ── Envío ──────────────────────────────────────────────────────────

@app.get("/api/envio/costos")
async def api_envio_costos():
    from services.settings_db import get_int
    return {
        "domicilio":      get_int("shipping.domicilio"),
        "sucursal":       get_int("shipping.sucursal"),
        "free_threshold": get_int("shipping.free_threshold"),
    }


@app.put("/api/admin/ordenes/{orden_id}/factura")
async def api_update_factura(
    orden_id: int,
    body: dict,
    request: Request,
    admin=Depends(verificar_admin)
):
    from db.connection import get_db
    from db.models import Order
    from services.activity import log as alog
    from datetime import datetime

    with get_db() as db:
        orden = db.query(Order).filter(Order.id == orden_id).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada.")
        orden.factura_numero = body.get("factura_numero", "")
        orden.factura_fecha  = datetime.utcnow()

    alog("factura_emitida", "order", orden_id, f"Orden #{orden_id}",
         detail=body.get("factura_numero", ""), user_id=int(admin.get("sub", 0)), request=request)
    return {"ok": True}


@app.put("/api/admin/ordenes/{orden_id}/tracking")
async def api_update_tracking(
    orden_id: int,
    body: dict,
    request: Request,
    admin=Depends(verificar_admin)
):
    from db.connection import get_db
    from db.models import Order
    from services.activity import log as alog

    with get_db() as db:
        orden = db.query(Order).filter(Order.id == orden_id).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada.")
        orden.tracking_number = body.get("tracking_number", "")

    alog("tracking_updated", "order", orden_id, f"Orden #{orden_id}",
         detail=body.get("tracking_number", ""), user_id=int(admin.get("sub", 0)), request=request)
    return {"ok": True}


# ── Transferencia bancaria ─────────────────────────────────────────

@app.get("/api/banco")
async def api_banco():
    from services.settings_db import get_setting
    return {
        "cbu":     get_setting("bank.cbu"),
        "alias":   get_setting("bank.alias"),
        "titular": get_setting("bank.holder"),
    }


@app.post("/api/ordenes/{orden_id}/comprobante")
async def subir_comprobante(orden_id: int, request: Request):
    from fastapi import UploadFile
    from services.storage import upload_comprobante
    from db.connection import get_db
    from db.models import Order, OrderStatus

    form  = await request.form()
    file  = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="No se recibió archivo.")

    file_bytes = await file.read()

    # Validar tipo de archivo por magic bytes
    is_jpeg = file_bytes[:3] == b'\xff\xd8\xff'
    is_png  = file_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    is_webp = file_bytes[:4] == b'RIFF' and file_bytes[8:12] == b'WEBP'
    is_pdf  = file_bytes[:4] == b'%PDF'
    if not (is_jpeg or is_png or is_webp or is_pdf):
        raise HTTPException(status_code=400, detail="Solo se aceptan imágenes (JPG, PNG) o PDF.")

    result = upload_comprobante(file_bytes, orden_id, filename=file.filename or "")

    with get_db() as db:
        orden = db.query(Order).filter(Order.id == orden_id).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada.")
        if orden.payment_method != PaymentMethod.transfer:
            raise HTTPException(status_code=400, detail="Esta orden no es de transferencia.")
        if orden.status not in (OrderStatus.pending, OrderStatus.verifying):
            raise HTTPException(status_code=400, detail=f"No se puede subir comprobante en estado '{orden.status.value}'.")
        orden.comprobante_url = result["url"]
        orden.status = OrderStatus.verifying

    from services.activity import log as alog
    from services.emails import enviar_comprobante_recibido, enviar_comprobante_al_owner
    from services.settings_db import get_setting
    alog("comprobante_uploaded", "order", orden_id, f"Orden #{orden_id}",
         user_name="cliente", request=request)
    try:
        with get_db() as db:
            o = db.query(Order).filter(Order.id == orden_id).first()
            if o:
                if o.customer_email:
                    enviar_comprobante_recibido(o.customer_email, o.shipping_name or "", o.id, float(o.total))
                owner_email = get_setting("notifications.visit_email_to")
                if owner_email:
                    enviar_comprobante_al_owner(
                        owner_email, o.id, o.shipping_name or "", float(o.total), result["url"]
                    )
    except Exception as e:
        print(f"⚠️ Error email comprobante: {e}")
    return {"ok": True, "url": result["url"]}


@app.get("/pago/transferencia", response_class=HTMLResponse)
async def pago_transferencia(request: Request):
    return templates.TemplateResponse("pago_transferencia.html", {
        "request":       request,
        "is_production": IS_PRODUCTION,
    })


# ── Páginas de retorno MercadoPago ─────────────────────────────────

@app.get("/pago/exitoso", response_class=HTMLResponse)
async def pago_exitoso(request: Request):
    return templates.TemplateResponse("pago_exitoso.html", {"request": request})


@app.get("/pago/fallido", response_class=HTMLResponse)
async def pago_fallido(request: Request):
    from services.activity import log as alog
    from db.connection import get_db as _get_db
    from db.models import Order as _Order
    from services.emails import enviar_pago_fallido

    order_id   = request.query_params.get("external_reference")
    session_id = request.query_params.get("sid", "")
    pref_id    = request.query_params.get("preference_id", "")

    alog("payment_mp_failed", "order",
         int(order_id) if order_id else None,
         f"Orden #{order_id}" if order_id else "desconocida",
         detail=f"preference_id: {pref_id}",
         session_id=session_id or None,
         request=request)

    if order_id:
        try:
            with _get_db() as db:
                o = db.query(_Order).filter(_Order.id == int(order_id)).first()
                if o and o.customer_email:
                    enviar_pago_fallido(o.customer_email, o.shipping_name or "", o.id, float(o.total))
        except Exception as e:
            print(f"⚠️ Error email pago fallido: {e}")

    return templates.TemplateResponse("pago_fallido.html", {"request": request, "is_production": IS_PRODUCTION})


@app.get("/pago/pendiente", response_class=HTMLResponse)
async def pago_pendiente(request: Request):
    from services.activity import log as alog
    order_id   = request.query_params.get("external_reference")
    session_id = request.query_params.get("sid", "")
    alog("payment_mp_pending", "order",
         int(order_id) if order_id else None,
         f"Orden #{order_id}" if order_id else "desconocida",
         session_id=session_id or None,
         request=request)
    return templates.TemplateResponse("pago_pendiente.html", {"request": request, "is_production": IS_PRODUCTION})


# ── Session tracking ──────────────────────────────────────────────

@app.post("/api/session/start")
async def session_start(request: Request):
    from services.activity import log as alog, get_geo, get_client_ip, parse_device
    from services.settings_db import get_bool, get_setting
    from services.emails import enviar_notificacion_visita

    body       = await request.json()
    session_id = body.get("session_id")
    entry_page = body.get("entry_page", "")
    referrer   = body.get("referrer", "")

    alog("session_start", detail=f"entry: {entry_page} | ref: {referrer}",
         session_id=session_id, request=request)

    if get_bool("notifications.visit_email"):
        try:
            ip     = get_client_ip(request)
            geo    = get_geo(ip)
            device = parse_device(request.headers.get("User-Agent", ""))
            to     = get_setting("notifications.visit_email_to")
            if to:
                enviar_notificacion_visita(
                    to_email   = to,
                    country    = geo.get("country", ""),
                    city       = geo.get("city", ""),
                    device     = device.get("device_type", ""),
                    browser    = device.get("browser", ""),
                    os         = device.get("os", ""),
                    referrer   = referrer,
                    entry_page = entry_page,
                    session_id = session_id or "",
                )
        except Exception as e:
            print(f"⚠️ Error email visita: {e}")

    return {"ok": True}


# ── Reset DB ──────────────────────────────────────────────────────

@app.post("/api/admin/db/reset")
async def api_db_reset(body: dict, owner=Depends(verificar_owner)):
    from db.connection import get_db as _gdb
    from sqlalchemy import text as _text

    if body.get("confirm") != "REINICIAR":
        raise HTTPException(status_code=400, detail="Escribí exactamente REINICIAR para confirmar.")

    groups = set(body.get("groups", []))
    if not groups:
        raise HTTPException(status_code=400, detail="Seleccioná al menos una opción.")

    resultado = {}
    with _gdb() as db:
        if "actividad" in groups:
            resultado["actividad"] = db.execute(_text("DELETE FROM activity_logs")).rowcount

        # Orden FK-safe: primero order_items, luego orders, luego users/products
        if "ordenes" in groups:
            db.execute(_text("DELETE FROM order_items"))
            resultado["ordenes"] = db.execute(_text("DELETE FROM orders")).rowcount

        if "usuarios" in groups:
            if "ordenes" not in groups:
                # CASCADE maneja order_items → orders de los usuarios borrados
                db.execute(_text(
                    "DELETE FROM order_items WHERE order_id IN "
                    "(SELECT id FROM orders WHERE user_id IN "
                    "(SELECT id FROM users WHERE role != 'owner'))"
                ))
                db.execute(_text("DELETE FROM orders WHERE user_id IN "
                                 "(SELECT id FROM users WHERE role != 'owner')"))
            resultado["usuarios"] = db.execute(
                _text("DELETE FROM users WHERE role != 'owner'")
            ).rowcount

        if "productos" in groups:
            en_uso = db.execute(_text(
                "SELECT COUNT(*) FROM order_items oi "
                "JOIN orders o ON o.id = oi.order_id "
                "WHERE o.status NOT IN ('cancelled')"
            )).scalar()
            if en_uso:
                raise HTTPException(
                    status_code=400,
                    detail=f"No se pueden borrar los productos: {en_uso} ítem(s) están en órdenes activas. "
                           f"Primero reiniciá las órdenes o cancelalas."
                )
            db.execute(_text("DELETE FROM product_images"))
            resultado["productos"] = db.execute(_text("DELETE FROM products")).rowcount

    partes = []
    labels = {"actividad": "registros de actividad", "ordenes": "órdenes",
              "usuarios": "usuarios", "productos": "productos"}
    for g in ["actividad", "ordenes", "usuarios", "productos"]:
        if g in resultado:
            partes.append(f"{resultado[g]} {labels[g]}")

    return {"ok": True, "mensaje": f"Eliminados: {', '.join(partes) or 'nada'}."}


# ── Webhook MercadoPago ────────────────────────────────────────────

@app.post("/api/webhook/mp")
async def webhook_mp(request: Request):
    from config.settings import MP_WEBHOOK_SECRET
    from services.payments import procesar_webhook, verificar_firma_webhook
    from services.orders import update_order_status

    if MP_WEBHOOK_SECRET:
        if not verificar_firma_webhook(request, MP_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Firma inválida")

    data = await request.json()
    print(f"📩 Webhook MP: {data}")

    resultado = procesar_webhook(data)
    if not resultado:
        return {"ok": True}

    from services.activity import log as alog
    if resultado["status"] == "approved" and resultado["order_id"]:
        update_order_status(resultado["order_id"], "paid")
        print(f"✅ Orden {resultado['order_id']} marcada como pagada")
        _sid_approved = None
        try:
            with _gdb() as db:
                _o = db.query(_O).filter(_O.id == resultado["order_id"]).first()
                _sid_approved = _o.checkout_session_id if _o else None
        except Exception:
            pass
        alog("payment_mp_approved", "order", resultado["order_id"],
             f"Orden #{resultado['order_id']}",
             detail=f"Payment ID: {resultado['payment_id']} | ${resultado['amount']:,.0f}",
             session_id=_sid_approved,
             user_name="mercadopago")
        try:
            from db.connection import get_db as _gdb
            from db.models import Order as _O, OrderItem as _OI
            from services.emails import enviar_pago_confirmado
            with _gdb() as db:
                o = db.query(_O).filter(_O.id == resultado["order_id"]).first()
                if o and o.customer_email:
                    enviar_pago_confirmado(
                        o.customer_email, o.shipping_name or "", o.id,
                        [{"nombre": i.product_name, "cantidad": i.quantity, "subtotal": float(i.subtotal)} for i in o.items],
                        float(o.subtotal), float(o.shipping_cost), float(o.total),
                        o.shipping_method.value if o.shipping_method else "domicilio",
                        o.shipping_address or "", o.shipping_branch or "",
                    )
        except Exception as e:
            print(f"⚠️ Error email pago confirmado: {e}")
    elif resultado["status"] in ("rejected", "cancelled") and resultado["order_id"]:
        _sid_rejected = None
        try:
            with _gdb() as db:
                _o = db.query(_O).filter(_O.id == resultado["order_id"]).first()
                _sid_rejected = _o.checkout_session_id if _o else None
        except Exception:
            pass
        alog("payment_mp_rejected", "order", resultado["order_id"],
             f"Orden #{resultado['order_id']}",
             detail=f"status: {resultado['status']} | Payment ID: {resultado['payment_id']}",
             session_id=_sid_rejected,
             user_name="mercadopago")

    return {"ok": True}

class ContactoRequest(BaseModel):
    nombre: str
    email:  str
    mensaje: str

@app.post("/api/contacto")
async def api_contacto(data: ContactoRequest):
    from services.emails import enviar_email_contacto
    try:
        enviar_email_contacto(
            nombre=data.nombre,
            email=data.email,
            mensaje=data.mensaje,
        )
        return {"ok": True}
    except Exception as e:
        print(f"⚠️ Error email contacto: {e}")
        raise HTTPException(status_code=500, detail="Error enviando email.")