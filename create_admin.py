from services.auth import register
from services.products import get_all_categories

# Crear admin
try:
    user = register(
        name="Admin",
        email="admin@ceramics.com",
        password="admin1234"
    )
    print(f"[OK] Usuario creado: {user.name}")
except ValueError as e:
    print(f"[WARN] {e}")  # ya existe, no pasa nada

# Probar categorías
cats = get_all_categories()
print(f"\n[OK] Categorías ({len(cats)}):")
for c in cats:
    print(f"  - {c.name}")
