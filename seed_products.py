"""poetry run python seed_products.py"""
from db.connection import get_db
from db.models import Category, Product
from decimal import Decimal

with get_db() as db:
    # Categorías
    cats = db.query(Category).all()
    if not cats:
        cats = [
            Category(name="Tazas y mugs",  slug="tazas-mugs",  position=1),
            Category(name="Bowls",          slug="bowls",        position=2),
            Category(name="Jarrones",       slug="jarrones",     position=3),
            Category(name="Piezas únicas",  slug="piezas-unicas",position=4),
        ]
        db.add_all(cats)
        db.flush()
        print(f"✅ {len(cats)} categorías creadas")

    cat_map = {c.slug: c.id for c in db.query(Category).all()}

    # Productos de prueba
    productos = [
        Product(name="Mug torno negro", slug="mug-torno-negro",
                price=Decimal("4500"), stock=8,
                category_id=cat_map["tazas-mugs"], technique="torno",
                dimensions="10×8 cm", weight_grams=320,
                description="Mug hecho a torno, esmalte negro mate.", is_featured=True),
        Product(name="Bowl mediano blanco", slug="bowl-mediano-blanco",
                price=Decimal("6200"), stock=5,
                category_id=cat_map["bowls"], technique="torno",
                dimensions="15×7 cm", weight_grams=480,
                description="Bowl de cerámica blanca con textura."),
        Product(name="Jarrón rollos terracota", slug="jarron-rollos-terracota",
                price=Decimal("9800"), stock=3,
                category_id=cat_map["jarrones"], technique="rollos",
                dimensions="22×12 cm", weight_grams=650,
                description="Jarrón construido con técnica de rollos.", is_featured=True),
        Product(name="Pieza única raku", slug="pieza-unica-raku",
                price=Decimal("18000"), stock=1,
                category_id=cat_map["piezas-unicas"], technique="raku",
                dimensions="30×15 cm", weight_grams=900,
                description="Pieza irrepetible, cocción raku tradicional.", is_featured=True),
        Product(name="Mug pellizco azul", slug="mug-pellizco-azul",
                price=Decimal("3800"), stock=0,
                category_id=cat_map["tazas-mugs"], technique="pellizco",
                dimensions="9×8 cm", weight_grams=280,
                description="Mug con marcas de pellizco visibles, sin stock."),
    ]
    db.add_all(productos)
    print(f"✅ {len(productos)} productos creados")

print("\n✅ Seed completado. Corré: poetry run streamlit run app.py")