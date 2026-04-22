# python -c "..."  o en un script temporal test.py
from services.auth import login
from services.products import get_all_categories, get_products

user = login("admin@ceramics.com", "admin1234")
print(user.name, user.role)

cats = get_all_categories()
print(f"\nCategorías: {len(cats)}")
for c in cats:
    print(f"  - {c.name}")

products = get_products()
print(f"\nProductos: {len(products)}")  # 0 por ahora, es correcto



from decimal import Decimal
from services.orders import get_all_orders, STATUS_LABELS

# Órdenes (vacío por ahora, es correcto)
orders = get_all_orders()
print(f"Órdenes: {len(orders)}")

# Probar labels
for key, label in STATUS_LABELS.items():
    print(f"  {key}: {label}")