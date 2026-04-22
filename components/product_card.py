import streamlit as st
from db.models import Product
from services.products import get_primary_image_url
from services.storage import get_image_url
from services import cart as cart_service


def render_product_card(product: Product) -> None:
    """Renderiza una card de producto usando HTML/CSS custom."""
    image_url = get_image_url(get_primary_image_url(product))
    price_fmt = f"${product.price:,.0f}".replace(",", ".")

    if image_url:
        st.image(image_url, use_container_width=True)
    else:
        st.markdown("""
            <div style="
                aspect-ratio:1/1;
                background:#F2F0EB;
                border-radius:8px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#888780;
                font-size:2rem;
            ">🏺</div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="product-card-info">
            <div class="title">{product.name}</div>
            <div class="price">{price_fmt}</div>
            {"<div class='badge-featured'>Destacado</div>" if product.is_featured else ""}
            {"<div class='badge-stock'>Sin stock</div>" if product.stock == 0 else ""}
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ver más", key=f"detail_{product.id}", use_container_width=True):
            st.session_state.selected_product_slug = product.slug
            st.switch_page("pages/product_detail.py")
    with col2:
        disabled = product.stock == 0
        if st.button(
            "Agregar" if not disabled else "Sin stock",
            key=f"add_{product.id}",
            use_container_width=True,
            disabled=disabled,
        ):
            cart_service.add_to_cart(product)
            st.toast(f"✅ {product.name} agregado al carrito")