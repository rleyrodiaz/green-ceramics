# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the development server
poetry run uvicorn main:app --reload --port 8000

# Add a dependency
poetry add <package>

# Regenerate lock file after editing pyproject.toml
poetry lock
poetry install --no-root
```

No test suite exists. Manual testing is done against the running server.

## Architecture

Single-file FastAPI backend (`main.py`) serving Jinja2 HTML templates with vanilla JS frontends. No frontend build step — static files are served directly from `static/`.

**Layers:**
- `main.py` — all routes, Pydantic request models, lifespan (runs DB migrations + FK fixes + seeds `app_settings` on startup)
- `services/` — business logic: `auth`, `orders`, `products`, `payments`, `storage`, `emails`, `activity`, `tokens`, `settings_db`, `images`
- `db/models.py` — all SQLAlchemy models in one file
- `db/connection.py` — `get_db()` context manager (commits on exit, rolls back + re-raises on exception)
- `config/settings.py` — all env vars loaded via `python-dotenv`

**Frontend:**
- Each page has a corresponding JS file (`carrito.js`, `cuenta.js`, `catalogo.js`, etc.)
- `main.js` is loaded on every public page — defines `getCart()`, `getSessionId()`, `updateCartCount()`, `updateNavAdmin()`, `updateNavAccount()`, `toggleCartDrawer()`, `abrirCheckout()`, `confirmarPedido()`, and all checkout functions
- `admin.js` is loaded on every admin page — defines `apiAdmin()` (adds Bearer token + X-Session-ID headers), `getSessionId()` (duplicated here since main.js isn't loaded on admin pages)
- Auth state stored in `localStorage` as `session` (customers) and `admin_token` / `admin_user` (admins)

**Cart + Checkout flow (all in main.js):**
- Cart stored in `localStorage`. Badge only shows count when user is logged in.
- Cart drawer injected into every page via `insertAdjacentHTML` in DOMContentLoaded. Persists open state across navigation via `sessionStorage("cart_open")`.
- Checkout modal also injected by main.js — available on every page. Clicking "Proceder al pago" opens it directly on the current page without navigating to `/carrito`.
- `shippingCosts` and `cargarCostosEnvio()` defined in main.js and shared with carrito.js.
- `carrito.js` only handles the `/carrito` page rendering (item list, quantity controls). All checkout logic lives in main.js.

**Nav structure (all public templates):**
```html
<nav>
  <a class="logo">...</a>
  <div class="nav-right">
    <button class="nav-toggle">...</button>       <!-- hamburger, hidden on desktop -->
    <ul class="nav-menu">...</ul>                  <!-- links -->
    <button class="account-icon-btn">...</button>  <!-- person icon -->
    <button class="cart-icon-btn">...</button>     <!-- cart icon with badge -->
  </div>
</nav>
```
Account icon: logged-out → goes to `/cuenta`; logged-in → dropdown (Mi cuenta / Salir). Cart icon: logged-out → goes to `/cuenta`; logged-in → opens drawer.

## Database migrations

There is no Alembic. Migrations run automatically in the `lifespan` function in `main.py` using raw SQL. When adding a new column to an existing table, add it to both:
1. The SQLAlchemy model in `db/models.py`
2. The migration block in `main.py` lifespan (using `sa_inspect` to check if column exists before adding)

`Base.metadata.create_all()` handles new tables; `ALTER TABLE IF NOT EXISTS` handles new columns on existing tables.

The lifespan also runs a FK constraint block that upgrades existing constraints to the correct `ON DELETE` behavior — so adding `ondelete=` to a `ForeignKey()` in the model alone is not enough for existing databases; the lifespan block must also include the fix.

## Key patterns

**DB session usage** — always use `get_db()` as a context manager. Never call `alog()` (activity logging) from inside an open `get_db()` block — it opens its own session and will conflict. Collect needed values first, close the `with` block, then call `alog()`.

**Activity logging** — `services/activity.py` `log()` function. Pass `request=request` to capture session_id (from `X-Session-ID` header), device info (user-agent via `user-agents` lib), and geo (ip-api.com, skipped for localhost). The `log()` function swallows all exceptions internally and prints a traceback — check Render logs if entries are missing. Always call outside `with get_db()` blocks.

**Session ID** — generated in the browser as a UUID stored in `sessionStorage`. Public pages read it via `main.js:getSessionId()`; admin pages via `admin.js:getSessionId()`. Sent as `X-Session-ID` header on every fetch. For MP payment redirects (browser navigations, not fetch), the session_id is embedded in the back_url as `?sid=` and read from query params in the GET handler. For webhook events (no user session), `checkout_session_id` is stored on the `Order` at creation time and retrieved by the webhook handler.

**Direct fetch calls** — any `fetch()` call that bypasses `apiAdmin()` (e.g., FormData uploads, DELETE without body) must manually include `"X-Session-ID": window.getSessionId ? window.getSessionId() : ""` in headers, otherwise activity log entries won't have a session_id.

**Admin auth** — `verificar_admin` dependency checks Bearer JWT token (role: admin or owner). `verificar_owner` is stricter (owner only — used for Settings, Activity Log, DB reset). Token payload: `{"sub": user_id_str, "rol": role}`.

**Payment flow:**
- Mercado Pago: `crear_preferencia()` → returns `init_point` (or `sandbox_init_point` when `MP_SANDBOX=true`) → user redirects to MP → webhook at `/api/webhook/mp` marks order `paid`
- Transfer: order created as `pending` → customer uploads comprobante → order moves to `verifying` → admin verifies manually → marks `paid`

**Order status flow:** `pending` → `verifying`* → `paid` → `preparing` → `shipped` → `delivered` (*transfer only)

**Shipping cost** — read at runtime from `app_settings` via `services/settings_db.py`. Keys: `shipping.domicilio`, `shipping.sucursal`, `shipping.free_threshold`. Never hardcode these values. The global `shippingCosts` object in main.js is loaded via `cargarCostosEnvio()` and shared across the drawer and checkout modal.

**Business configuration (app_settings)** — key-value table edited from admin Settings UI. `services/settings_db.py` provides `get_setting()`, `get_int()`, `get_float()`, `get_bool()`, `set_setting()`. Seeded from env vars on first startup. Use this for any owner-configurable value (shipping costs, bank details, reminder hours, notification toggles).

**FK constraints** — defined with `ondelete=` in `ForeignKey()` in the model AND enforced via DO blocks in the lifespan migration. Current policy:
- `orders.user_id → users` CASCADE
- `order_items.order_id → orders` CASCADE
- `order_items.product_id → products` RESTRICT (cannot delete a product used in any order)
- `product_images.product_id → products` CASCADE

**DB reset endpoint** — `POST /api/admin/db/reset` (owner only). Accepts `{ groups: [...], confirm: "REINICIAR" }`. Groups: `ordenes`, `usuarios`, `productos`, `actividad`. Resets sequences to 1 after deletion. Available from admin Settings UI.

**Storage backend** — controlled by `STORAGE_BACKEND` env var (`"cloudinary"` or `"local"`). Local saves to `static/comprobantes/`. Cloudinary uses `resource_type="image"` and `format="jpg"` to convert PDFs to images on upload.

**Timestamps** — stored as UTC (`datetime.utcnow`). When displaying in the browser always append `"Z"` before constructing a `Date` object and specify `timeZone: "America/Argentina/Buenos_Aires"` in `toLocaleString`.

**APScheduler** — an `AsyncIOScheduler` runs inside the uvicorn process. It fires `enviar_recordatorios()` hourly to send reminder emails for pending MP and transfer orders. May miss jobs when the Render free-tier service sleeps.

## Environment variables

Required in `.env` (local) and Render environment (production):

```
DATABASE_URL          # PostgreSQL connection string
APP_SECRET_KEY        # JWT signing key
MP_ACCESS_TOKEN       # MercadoPago token (use test token + MP_SANDBOX=true for sandbox)
MP_PUBLIC_KEY         # MercadoPago public key
MP_WEBHOOK_SECRET     # Webhook signature secret (leave empty to skip verification)
MP_SANDBOX            # "true" to use sandbox_init_point and test credentials
BANK_CBU / BANK_ALIAS / BANK_HOLDER   # Seeded into app_settings on first startup
SHIPPING_DOMICILIO / SHIPPING_SUCURSAL / SHIPPING_FREE_THRESHOLD  # Same — seeded once
CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
STORAGE_BACKEND       # "cloudinary" (production) or "local" (development)
RESEND_API_KEY        # Transactional email
EMAIL_FROM            # Sender address (must be verified domain in production)
EMAIL_OWNER           # Owner email for visit/comprobante notifications
```

After seeding, shipping and bank values live in `app_settings` and are edited from the admin Settings UI — changing the env vars has no effect on an already-seeded database.

## Deployment

Deployed on Render (web service). `requirements.txt` is used by Render (not `pyproject.toml`). After adding a new dependency with `poetry add`, update `requirements.txt` manually with the pinned version.
