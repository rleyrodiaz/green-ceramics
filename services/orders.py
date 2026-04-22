from decimal import Decimal
from sqlalchemy.orm import make_transient
from db.models import Order, OrderItem, OrderStatus, Product
from db.connection import get_db
from services import cart as cart_service
from services.products import update_stock


def _detach_order(db, order: Order) -> Order:
    """Carga relaciones y desacopla la orden de la sesión."""
    _ = [
        (item.id, item.product_id, item.quantity,
         item.unit_price, item.subtotal, item.product_name)
        for item in order.items
    ]
    db.expunge(order)
    make_transient(order)
    for item in order.items:
        make_transient(item)
    return order


def create_order_from_cart(
    user_id: int,
    shipping_name: str,
    shipping_address: str,
    shipping_city: str,
    shipping_province: str,
    shipping_zip: str,
    shipping_phone: str,
    notes: str = "",
) -> Order:
    """
    Crea una orden en DB a partir del carrito actual.
    Descuenta stock. Lanza ValueError si hay producto sin stock.
    """
    items = cart_service.get_items()
    if not items:
        raise ValueError("El carrito está vacío.")

    totals = cart_service.get_totals()

    with get_db() as db:
        # Verificar stock antes de crear la orden
        for item in items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise ValueError(f"Producto '{item.name}' no encontrado.")
            if product.stock < item.quantity:
                raise ValueError(
                    f"Stock insuficiente para '{item.name}'. "
                    f"Disponible: {product.stock}, pedido: {item.quantity}."
                )

        # Crear orden
        order = Order(
            user_id=user_id,
            status=OrderStatus.pending,
            subtotal=totals["subtotal"],
            shipping_cost=totals["shipping"],
            total=totals["total"],
            shipping_name=shipping_name,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_province=shipping_province,
            shipping_zip=shipping_zip,
            shipping_phone=shipping_phone,
            notes=notes,
        )
        db.add(order)
        db.flush()

        # Crear items y descontar stock
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.price,
                subtotal=item.subtotal,
                product_name=item.name,  # snapshot
            )
            db.add(order_item)

            # Descontar stock
            product = db.query(Product).filter(Product.id == item.product_id).first()
            product.stock -= item.quantity

        db.flush()
        return _detach_order(db, order)


def get_order_by_id(order_id: int) -> Order | None:
    with get_db() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        return _detach_order(db, order)


def get_orders_by_user(user_id: int) -> list[Order]:
    with get_db() as db:
        orders = db.query(Order).filter(
            Order.user_id == user_id
        ).order_by(Order.created_at.desc()).all()
        return [_detach_order(db, o) for o in orders]


def get_all_orders(status: str | None = None, limit: int = 100) -> list[Order]:
    """Para el panel de admin."""
    with get_db() as db:
        q = db.query(Order)
        if status:
            q = q.filter(Order.status == OrderStatus(status))
        orders = q.order_by(Order.created_at.desc()).limit(limit).all()
        return [_detach_order(db, o) for o in orders]


def update_order_status(order_id: int, new_status: str) -> Order:
    with get_db() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Orden {order_id} no encontrada.")
        order.status = OrderStatus(new_status)
        db.flush()
        return _detach_order(db, order)


def set_mp_preference(order_id: int, preference_id: str) -> None:
    """Guarda el ID de preferencia de MercadoPago en la orden."""
    with get_db() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Orden {order_id} no encontrada.")
        order.mp_preference_id = preference_id


def confirm_payment(mp_payment_id: str, mp_preference_id: str) -> Order | None:
    """
    Llamado desde el webhook de MercadoPago cuando el pago es aprobado.
    Actualiza el estado a 'paid' y guarda el payment_id.
    """
    with get_db() as db:
        order = db.query(Order).filter(
            Order.mp_preference_id == mp_preference_id
        ).first()
        if not order:
            return None
        order.status = OrderStatus.paid
        order.mp_payment_id = mp_payment_id
        db.flush()
        return _detach_order(db, order)


STATUS_LABELS = {
    "pending"  : "⏳ Pendiente",
    "paid"     : "✅ Pagado",
    "preparing": "🔨 Preparando",
    "shipped"  : "🚚 Enviado",
    "delivered": "📦 Entregado",
    "cancelled": "❌ Cancelado",
}

STATUS_FLOW = ["pending", "paid", "preparing", "shipped", "delivered"]


def next_status(current: str) -> str | None:
    """Retorna el siguiente estado en el flujo, None si es el último."""
    try:
        idx = STATUS_FLOW.index(current)
        return STATUS_FLOW[idx + 1] if idx + 1 < len(STATUS_FLOW) else None
    except ValueError:
        return None