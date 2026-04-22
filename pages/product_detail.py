import streamlit as st
from components.layout import page_setup
from components.session import is_admin
from services.products import get_product_by_slug, get_primary_image_url
from services.storage import get_image_url
from services import cart as cart_service

page_setup(
    title="Producto",
    cart_count=cart_service.get_item_count(),
    is_admin=is_admin(),
)

# ── Obtener producto ───────────────────────────────────────────────
slug = st.session_state.get("selected_product_slug")
if not slug:
    st.error("Producto no encontrado.")
    if st.button("← Volver al catálogo"):
        st.switch_page("pages/catalog.py")
    st.stop()

product = get_product_by_slug(slug)
if not product:
    st.error("Producto no encontrado.")
    if st.button("← Volver al catálogo"):
        st.switch_page("pages/catalog.py")
    st.stop()

# ── Layout ─────────────────────────────────────────────────────────
if st.button("← Volver al catálogo"):
    st.switch_page("pages/catalog.py")

col_img, col_info = st.columns([1, 1], gap="large")

with col_img:
    # Galería de imágenes
    if product.images:
        main_url = get_image_url(get_primary_image_url(product))
        if main_url:
            st.image(main_url, use_container_width=True)

        # Thumbnails si hay más de una imagen
        if len(product.images) > 1:
            thumb_cols = st.columns(len(product.images))
            for i, img in enumerate(product.images):
                with thumb_cols[i]:
                    thumb_url = get_image_url(img.url)
                    if thumb_url:
                        st.image(thumb_url, use_container_width=True)
    else:
        st.markdown("""
            <div style="
                aspect-ratio:1/1;background:#F2F0EB;
                border-radius:10px;display:flex;
                align-items:center;justify-content:center;
                font-size:4rem;
            ">🏺</div>
        """, unsafe_allow_html=True)

with col_info:
    price_fmt = f"${product.price:,.0f}".replace(",", ".")

    st.markdown(f'<div class="product-detail-title">{product.name}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="product-detail-price">{price_fmt}</div>',
                unsafe_allow_html=True)

    # Stock
    if product.stock == 0:
        st.markdown('<div class="stock-out">✗ Sin stock</div>', unsafe_allow_html=True)
    elif product.stock <= 3:
        st.markdown(f'<div class="stock-low">⚠ Últimas {product.stock} unidades</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="stock-ok">✓ En stock</div>', unsafe_allow_html=True)

    # Metadatos
    if product.category:
        st.markdown(f'<div class="product-detail-meta">Categoría: {product.category.name}</div>',
                    unsafe_allow_html=True)
    if product.technique:
        st.markdown(f'<div class="product-detail-meta">Técnica: {product.technique.value.capitalize()}</div>',
                    unsafe_allow_html=True)
    if product.dimensions:
        st.markdown(f'<div class="product-detail-meta">Medidas: {product.dimensions}</div>',
                    unsafe_allow_html=True)
    if product.weight_grams:
        st.markdown(f'<div class="product-detail-meta">Peso: {product.weight_grams}g</div>',
                    unsafe_allow_html=True)

    if product.description:
        st.markdown(f'<div class="product-detail-description">{product.description}</div>',
                    unsafe_allow_html=True)

    st.divider()

    # Cantidad + agregar al carrito
    if product.stock > 0:
        quantity = st.number_input(
            "Cantidad",
            min_value=1,
            max_value=product.stock,
            value=1,
            step=1,
        )
        if st.button("Agregar al carrito", use_container_width=True, type="primary"):
            cart_service.add_to_cart(product, quantity=int(quantity))
            st.toast(f"✅ {product.name} agregado al carrito")
    else:
        st.button("Sin stock", disabled=True, use_container_width=True)