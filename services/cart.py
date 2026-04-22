import streamlit as st
from dataclasses import dataclass, field
from decimal import Decimal
from db.models import Product
from services.products import get_product_by_id, get_primary_image_url


@dataclass
class CartItem:
    product_id  : int
    name        : str
    price       : Decimal
    quantity    : int
    image_url   : str = ""
    slug        : str = ""

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity


def _get_cart() -> dict[int, CartItem]:
    """Retorna el carrito desde session_state, lo inicializa si no existe."""
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    return st.session_state.cart


def add_to_cart(product: Product, quantity: int = 1) -> None:
    cart = _get_cart()
    if product.id in cart:
        cart[product.id].quantity += quantity
    else:
        cart[product.id] = CartItem(
            product_id=product.id,
            name=product.name,
            price=product.price,
            quantity=quantity,
            image_url=get_primary_image_url(product),
            slug=product.slug,
        )


def remove_from_cart(product_id: int) -> None:
    cart = _get_cart()
    cart.pop(product_id, None)


def update_quantity(product_id: int, quantity: int) -> None:
    cart = _get_cart()
    if product_id not in cart:
        return
    if quantity <= 0:
        remove_from_cart(product_id)
    else:
        cart[product_id].quantity = quantity


def clear_cart() -> None:
    st.session_state.cart = {}


def get_items() -> list[CartItem]:
    return list(_get_cart().values())


def get_item_count() -> int:
    return sum(item.quantity for item in _get_cart().values())


def get_subtotal() -> Decimal:
    return sum(item.subtotal for item in _get_cart().values())


def is_empty() -> bool:
    return len(_get_cart()) == 0


def calculate_shipping(subtotal: Decimal) -> Decimal:
    """
    Lógica de envío simple por ahora.
    Gratis a partir de $50.000, sino $3.500 fijo.
    Ajustar según necesidad.
    """
    FREE_SHIPPING_THRESHOLD = Decimal("50000")
    SHIPPING_COST = Decimal("3500")
    return Decimal("0") if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST


def get_totals() -> dict:
    subtotal = get_subtotal()
    shipping = calculate_shipping(subtotal)
    return {
        "subtotal": subtotal,
        "shipping": shipping,
        "total": subtotal + shipping,
    }