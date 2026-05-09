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
- `main.py` — all routes, Pydantic request models, lifespan (runs DB migrations on startup)
- `services/` — business logic called from routes (`auth`, `orders`, `products`, `payments`, `storage`, `emails`, `activity`, `tokens`)
- `db/models.py` — all SQLAlchemy models in one file
- `db/connection.py` — `get_db()` context manager (commits on exit, rolls back on exception)
- `config/settings.py` — all env vars loaded via `python-dotenv`

**Frontend:**
- Each page has a corresponding JS file (`carrito.js`, `cuenta.js`, `catalogo.js`, etc.)
- `main.js` is loaded on every public page — defines `getCart()`, `getSessionId()`, `updateCartCount()`, `updateNavAdmin()`
- `admin.js` is loaded on every admin page — defines `apiAdmin()` (adds Bearer token + X-Session-ID headers), `getSessionId()` (duplicated here since main.js isn't loaded on admin pages)
- Auth state stored in `localStorage` as `session` (customers) and `admin_token` / `admin_user` (admins)

## Database migrations

There is no Alembic. Migrations run automatically in the `lifespan` function in `main.py` using raw `ALTER TABLE` / `ALTER TYPE` SQL. When adding a new column to an existing table, add it to both:
1. The SQLAlchemy model in `db/models.py`
2. The migration block in `main.py` lifespan (using `sa_inspect` to check if column exists before adding)

`Base.metadata.create_all()` handles new tables; `ALTER TABLE IF NOT EXISTS` handles new columns on existing tables.

## Key patterns

**DB session usage** — always use `get_db()` as a context manager. Never call `alog()` (activity logging) from inside an open `get_db()` block, as it opens its own session and can cause conflicts. Collect needed values, close the `with` block, then call `alog()`.

**Activity logging** — `services/activity.py` `log()` function. Pass `request=request` to capture session_id (from `X-Session-ID` header), device info (user-agent parsed via `user-agents` lib), and geo (from ip-api.com, skipped for localhost). Always call outside `with get_db()` blocks.

**Admin auth** — `verificar_admin` dependency checks Bearer JWT token (role: admin or owner). `verificar_owner` is stricter (owner only, used for Settings/Activity Log). Token payload: `{"sub": user_id_str, "rol": role}`.

**Payment flow:**
- Mercado Pago: `crear_preferencia()` → returns `init_point` URL → user redirects to MP → webhook at `/api/webhook/mp` marks order `paid`
- Transfer: order created as `pending` → customer uploads comprobante → order moves to `verifying` → admin verifies manually → marks `paid`

**Order status flow:** `pending` → `verifying`* → `paid` → `preparing` → `shipped` → `delivered` (*transfer only)

**Storage backend** — controlled by `STORAGE_BACKEND` env var (`"cloudinary"` or `"local"`). Local saves to `static/comprobantes/` (served as static). Cloudinary uses `resource_type="image"` for images and converts PDFs to JPG on upload.

## Environment variables

Required in `.env` (local) and Render environment (production):

```
DATABASE_URL          # PostgreSQL connection string
APP_SECRET_KEY        # JWT signing key
MP_ACCESS_TOKEN       # MercadoPago production token
MP_PUBLIC_KEY         # MercadoPago public key
MP_WEBHOOK_SECRET     # MercadoPago webhook signature secret (optional — skips verification if unset)
BANK_CBU / BANK_ALIAS / BANK_HOLDER   # Bank transfer details shown at checkout
SHIPPING_DOMICILIO / SHIPPING_SUCURSAL / SHIPPING_FREE_THRESHOLD  # Shipping costs (integers, ARS)
CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
STORAGE_BACKEND       # "cloudinary" (production) or "local" (development)
RESEND_API_KEY        # Transactional email
EMAIL_FROM            # Sender address (must be verified domain in production)
```

## Deployment

Deployed on Render (web service). `requirements.txt` is used by Render (not `pyproject.toml`). After adding a new dependency with `poetry add`, the lock file updates automatically but `requirements.txt` must be updated manually by appending the new package with its pinned version.
