-- Categorías base
INSERT INTO categories (name, slug, description, position) VALUES
    ('Tazas y mugs',   'tazas-mugs',   'Para el café de cada día',        1),
    ('Bowls',          'bowls',         'Cuencos de todos los tamaños',    2),
    ('Jarrones',       'jarrones',      'Para flores y decoración',        3),
    ('Platos',         'platos',        'Platos y platillos artesanales',  4),
    ('Macetas',        'macetas',       'Para tus plantas',                5),
    ('Piezas únicas',  'piezas-unicas', 'Obras de edición limitada',      6);

-- Admin user (password: admin1234 — cambiarlo en prod)
-- Hash bcrypt de "admin1234"
INSERT INTO users (email, name, password, role) VALUES
    ('admin@ceramics.com', 'Admin', 
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhN3uXWAqK1mNJE9A0Oc.a',
     'admin');