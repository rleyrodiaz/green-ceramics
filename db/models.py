from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String, Text, Numeric, Integer, Boolean,
    DateTime, ForeignKey, Enum as PgEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from db.connection import Base


# ── Enums ──────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    customer = "customer"
    admin    = "admin"


class OrderStatus(str, enum.Enum):
    pending   = "pending"    # creado, sin pagar
    paid      = "paid"       # pago confirmado
    preparing = "preparing"  # en preparación
    shipped   = "shipped"    # enviado
    delivered = "delivered"  # entregado
    cancelled = "cancelled"  # cancelado


class TechniqueType(str, enum.Enum):
    torno       = "torno"
    rollos      = "rollos"
    placas      = "placas"
    pellizco    = "pellizco"
    molde       = "molde"
    raku        = "raku"
    otro        = "otro"


# ── Modelos ────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id         : Mapped[int]      = mapped_column(Integer, primary_key=True)
    email      : Mapped[str]      = mapped_column(String(255), unique=True, nullable=False)
    name       : Mapped[str]      = mapped_column(String(120), nullable=False)
    password   : Mapped[str]      = mapped_column(String(255), nullable=False)  # bcrypt hash
    role       : Mapped[UserRole] = mapped_column(PgEnum(UserRole), default=UserRole.customer)
    is_active  : Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders     : Mapped[list["Order"]] = relationship(back_populates="user")

    __table_args__ = (Index("ix_users_email", "email"),)


class Category(Base):
    __tablename__ = "categories"

    id          : Mapped[int]  = mapped_column(Integer, primary_key=True)
    name        : Mapped[str]  = mapped_column(String(80), unique=True, nullable=False)
    slug        : Mapped[str]  = mapped_column(String(80), unique=True, nullable=False)
    description : Mapped[str]  = mapped_column(Text, nullable=True)
    position    : Mapped[int]  = mapped_column(Integer, default=0)  # orden en el menú

    products    : Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id           : Mapped[int]           = mapped_column(Integer, primary_key=True)
    name         : Mapped[str]           = mapped_column(String(200), nullable=False)
    slug         : Mapped[str]           = mapped_column(String(200), unique=True, nullable=False)
    description  : Mapped[str]           = mapped_column(Text, nullable=True)
    price        : Mapped[Decimal]       = mapped_column(Numeric(10, 2), nullable=False)
    stock        : Mapped[int]           = mapped_column(Integer, default=0)
    technique    : Mapped[TechniqueType] = mapped_column(PgEnum(TechniqueType), nullable=True)
    dimensions   : Mapped[str]           = mapped_column(String(80), nullable=True)   # ej: "12×8 cm"
    weight_grams : Mapped[int]           = mapped_column(Integer, nullable=True)
    is_active    : Mapped[bool]          = mapped_column(Boolean, default=True)
    is_featured  : Mapped[bool]          = mapped_column(Boolean, default=False)
    created_at   : Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)
    updated_at   : Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow,
                                                          onupdate=datetime.utcnow)

    category_id  : Mapped[int]           = mapped_column(ForeignKey("categories.id"), nullable=True)
    category     : Mapped["Category"]    = relationship(back_populates="products")
    images       : Mapped[list["ProductImage"]] = relationship(
                       back_populates="product",
                       order_by="ProductImage.position",
                       cascade="all, delete-orphan"
                   )
    order_items  : Mapped[list["OrderItem"]] = relationship(back_populates="product")

    __table_args__ = (
        Index("ix_products_slug", "slug"),
        Index("ix_products_active", "is_active"),
        Index("ix_products_category", "category_id"),
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id          : Mapped[int]  = mapped_column(Integer, primary_key=True)
    product_id  : Mapped[int]  = mapped_column(ForeignKey("products.id"), nullable=False)
    url         : Mapped[str]  = mapped_column(String(500), nullable=False)   # URL de Cloudinary
    public_id   : Mapped[str]  = mapped_column(String(200), nullable=True)    # ID en Cloudinary (para borrar)
    alt_text    : Mapped[str]  = mapped_column(String(200), nullable=True)
    position    : Mapped[int]  = mapped_column(Integer, default=0)            # 0 = imagen principal
    is_primary  : Mapped[bool] = mapped_column(Boolean, default=False)

    product     : Mapped["Product"] = relationship(back_populates="images")


class Order(Base):
    __tablename__ = "orders"

    id              : Mapped[int]         = mapped_column(Integer, primary_key=True)
    user_id         : Mapped[int]         = mapped_column(ForeignKey("users.id"), nullable=False)
    status          : Mapped[OrderStatus] = mapped_column(PgEnum(OrderStatus), default=OrderStatus.pending)

    # Totales
    subtotal        : Mapped[Decimal]     = mapped_column(Numeric(10, 2), nullable=False)
    shipping_cost   : Mapped[Decimal]     = mapped_column(Numeric(10, 2), default=Decimal("0"))
    total           : Mapped[Decimal]     = mapped_column(Numeric(10, 2), nullable=False)

    # Envío
    shipping_name   : Mapped[str]         = mapped_column(String(120), nullable=True)
    shipping_address: Mapped[str]         = mapped_column(String(300), nullable=True)
    shipping_city   : Mapped[str]         = mapped_column(String(80), nullable=True)
    shipping_province: Mapped[str]        = mapped_column(String(80), nullable=True)
    shipping_zip    : Mapped[str]         = mapped_column(String(20), nullable=True)
    shipping_phone  : Mapped[str]         = mapped_column(String(30), nullable=True)

    # MercadoPago
    mp_preference_id: Mapped[str]         = mapped_column(String(200), nullable=True)
    mp_payment_id   : Mapped[str]         = mapped_column(String(200), nullable=True)

    notes           : Mapped[str]         = mapped_column(Text, nullable=True)
    created_at      : Mapped[datetime]    = mapped_column(DateTime, default=datetime.utcnow)
    updated_at      : Mapped[datetime]    = mapped_column(DateTime, default=datetime.utcnow,
                                                           onupdate=datetime.utcnow)

    user            : Mapped["User"]            = relationship(back_populates="orders")
    items           : Mapped[list["OrderItem"]] = relationship(
                          back_populates="order",
                          cascade="all, delete-orphan"
                      )

    __table_args__ = (
        Index("ix_orders_user", "user_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_mp", "mp_payment_id"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id          : Mapped[int]     = mapped_column(Integer, primary_key=True)
    order_id    : Mapped[int]     = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id  : Mapped[int]     = mapped_column(ForeignKey("products.id"), nullable=False)

    # Snapshot del precio al momento de compra (el precio puede cambiar después)
    quantity    : Mapped[int]     = mapped_column(Integer, nullable=False)
    unit_price  : Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal    : Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    product_name: Mapped[str]     = mapped_column(String(200), nullable=False)  # snapshot nombre

    order       : Mapped["Order"]   = relationship(back_populates="items")
    product     : Mapped["Product"] = relationship(back_populates="order_items")