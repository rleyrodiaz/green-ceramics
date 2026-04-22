from decimal import Decimal
from sqlalchemy.orm import joinedload, make_transient
from db.models import Product, Category, ProductImage, TechniqueType
from db.connection import get_db
from services.images import upload_image, delete_image
import re
import unicodedata


# ── Helpers ────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def _detach(obj):
    """Desacopla un objeto ORM de la sesión manteniendo sus atributos."""
    from sqlalchemy import inspect
    if obj is None:
        return None
    insp = inspect(obj)
    if not insp.detached:
        insp.session.expunge(obj)
    make_transient(obj)
    return obj


def _detach_list(objects):
    return [_detach(obj) for obj in objects]


# ── Categories ─────────────────────────────────────────────────────

def get_all_categories() -> list[Category]:
    with get_db() as db:
        cats = db.query(Category).order_by(Category.position).all()
        return _detach_list(cats)


def get_category_by_slug(slug: str) -> Category | None:
    with get_db() as db:
        cat = db.query(Category).filter(Category.slug == slug).first()
        return _detach(cat)


# ── Products ───────────────────────────────────────────────────────

def _load_product(db, query):
    """Carga un producto con sus relaciones y lo desacopla."""
    product = query.options(
        joinedload(Product.images),
        joinedload(Product.category),
    ).first()
    if not product:
        return None
    # Forzar carga de relaciones antes de cerrar sesión
    _ = [(img.url, img.public_id, img.position, img.is_primary) for img in product.images]
    if product.category:
        _ = product.category.name
    _detach(product)
    for img in product.images:
        make_transient(img)
    if product.category:
        make_transient(product.category)
    return product


def _load_products(db, query) -> list[Product]:
    """Carga una lista de productos con sus relaciones y los desacopla."""
    products = query.options(
        joinedload(Product.images),
        joinedload(Product.category),
    ).all()
    result = []
    for product in products:
        _ = [(img.url, img.public_id, img.position, img.is_primary) for img in product.images]
        if product.category:
            _ = product.category.name
        _detach(product)
        for img in product.images:
            make_transient(img)
        if product.category:
            make_transient(product.category)
        result.append(product)
    return result


def get_products(
    category_slug: str | None = None,
    technique: str | None = None,
    only_active: bool = True,
    only_featured: bool = False,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:
    with get_db() as db:
        q = db.query(Product)
        if only_active:
            q = q.filter(Product.is_active == True)
        if only_featured:
            q = q.filter(Product.is_featured == True)
        if category_slug:
            q = q.join(Category).filter(Category.slug == category_slug)
        if technique:
            q = q.filter(Product.technique == technique)
        if search:
            q = q.filter(Product.name.ilike(f"%{search}%"))
        q = q.order_by(Product.created_at.desc()).limit(limit).offset(offset)
        return _load_products(db, q)


def get_product_by_slug(slug: str) -> Product | None:
    with get_db() as db:
        q = db.query(Product).filter(Product.slug == slug)
        return _load_product(db, q)


def get_product_by_id(product_id: int) -> Product | None:
    with get_db() as db:
        q = db.query(Product).filter(Product.id == product_id)
        return _load_product(db, q)


def create_product(
    name: str,
    price: float,
    description: str = "",
    stock: int = 0,
    category_id: int | None = None,
    technique: str | None = None,
    dimensions: str = "",
    weight_grams: int | None = None,
    is_featured: bool = False,
    image_files: list[tuple[bytes, str]] = [],
) -> Product:
    slug = slugify(name)
    with get_db() as db:
        base_slug, counter = slug, 1
        while db.query(Product).filter(Product.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product = Product(
            name=name,
            slug=slug,
            description=description,
            price=Decimal(str(price)),
            stock=stock,
            category_id=category_id,
            technique=TechniqueType(technique) if technique else None,
            dimensions=dimensions,
            weight_grams=weight_grams,
            is_featured=is_featured,
        )
        db.add(product)
        db.flush()

        for position, (file_bytes, _filename) in enumerate(image_files):
            result = upload_image(file_bytes, slug, position)
            img = ProductImage(
                product_id=product.id,
                url=result["url"],
                public_id=result["public_id"],
                position=position,
                is_primary=(position == 0),
            )
            db.add(img)

        db.flush()
        q = db.query(Product).filter(Product.id == product.id)
        return _load_product(db, q)


def update_product(product_id: int, **fields) -> Product:
    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Producto {product_id} no encontrado.")
        for key, value in fields.items():
            if hasattr(product, key):
                setattr(product, key, value)
        db.flush()
        q = db.query(Product).filter(Product.id == product_id)
        return _load_product(db, q)


def toggle_product_active(product_id: int) -> bool:
    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Producto {product_id} no encontrado.")
        product.is_active = not product.is_active
        return product.is_active


def update_stock(product_id: int, quantity_delta: int) -> int:
    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Producto {product_id} no encontrado.")
        new_stock = product.stock + quantity_delta
        if new_stock < 0:
            raise ValueError(f"Stock insuficiente para '{product.name}'.")
        product.stock = new_stock
        return new_stock


def get_primary_image_url(product: Product, fallback: str = "") -> str:
    if not product.images:
        return fallback
    primary = next((img for img in product.images if img.is_primary), product.images[0])
    return primary.url