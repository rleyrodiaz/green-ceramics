-- el schema en SQL puro para correr directo en psql si preferís:
-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
CREATE TYPE user_role      AS ENUM ('customer', 'admin');
CREATE TYPE order_status   AS ENUM ('pending','paid','preparing','shipped','delivered','cancelled');
CREATE TYPE technique_type AS ENUM ('torno','rollos','placas','pellizco','molde','raku','otro');

-- Users
CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    email      VARCHAR(255) UNIQUE NOT NULL,
    name       VARCHAR(120) NOT NULL,
    password   VARCHAR(255) NOT NULL,
    role       user_role NOT NULL DEFAULT 'customer',
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_users_email ON users(email);

-- Categories
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(80) UNIQUE NOT NULL,
    slug        VARCHAR(80) UNIQUE NOT NULL,
    description TEXT,
    position    INTEGER NOT NULL DEFAULT 0
);

-- Products
CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    slug         VARCHAR(200) UNIQUE NOT NULL,
    description  TEXT,
    price        NUMERIC(10,2) NOT NULL,
    stock        INTEGER NOT NULL DEFAULT 0,
    technique    technique_type,
    dimensions   VARCHAR(80),
    weight_grams INTEGER,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    category_id  INTEGER REFERENCES categories(id) ON DELETE SET NULL
);
CREATE INDEX ix_products_slug     ON products(slug);
CREATE INDEX ix_products_active   ON products(is_active);
CREATE INDEX ix_products_category ON products(category_id);

-- Product images
CREATE TABLE product_images (
    id         SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    url        VARCHAR(500) NOT NULL,
    public_id  VARCHAR(200),
    alt_text   VARCHAR(200),
    position   INTEGER NOT NULL DEFAULT 0,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE
);

-- Orders
CREATE TABLE orders (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    status           order_status NOT NULL DEFAULT 'pending',
    subtotal         NUMERIC(10,2) NOT NULL,
    shipping_cost    NUMERIC(10,2) NOT NULL DEFAULT 0,
    total            NUMERIC(10,2) NOT NULL,
    shipping_name    VARCHAR(120),
    shipping_address VARCHAR(300),
    shipping_city    VARCHAR(80),
    shipping_province VARCHAR(80),
    shipping_zip     VARCHAR(20),
    shipping_phone   VARCHAR(30),
    mp_preference_id VARCHAR(200),
    mp_payment_id    VARCHAR(200),
    notes            TEXT,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_orders_user   ON orders(user_id);
CREATE INDEX ix_orders_status ON orders(status);
CREATE INDEX ix_orders_mp     ON orders(mp_payment_id);

-- Order items
CREATE TABLE order_items (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    quantity     INTEGER NOT NULL,
    unit_price   NUMERIC(10,2) NOT NULL,
    subtotal     NUMERIC(10,2) NOT NULL,
    product_name VARCHAR(200) NOT NULL
);

-- Trigger: updated_at automático en products y orders
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();