import streamlit as st
from components.layout import page_setup
from components.product_card import render_product_card
from components.session import is_admin
from services.products import get_products, get_all_categories
from services import cart as cart_service

page_setup(
    title="Catálogo",
    cart_count=cart_service.get_item_count(),
    is_admin=is_admin(),
)

# ── Sidebar: filtros ───────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="filter-title">Categoría</div>', unsafe_allow_html=True)
    categories = get_all_categories()
    cat_options = {"Todas": None} | {c.name: c.slug for c in categories}
    selected_cat = st.radio(
        "Categoría",
        options=list(cat_options.keys()),
        label_visibility="collapsed",
    )

    st.markdown('<div class="filter-title">Técnica</div>', unsafe_allow_html=True)
    from db.models import TechniqueType
    technique_options = {"Todas": None} | {t.value.capitalize(): t.value for t in TechniqueType}
    selected_technique = st.radio(
        "Técnica",
        options=list(technique_options.keys()),
        label_visibility="collapsed",
    )

    st.markdown('<div class="filter-title">Buscar</div>', unsafe_allow_html=True)
    search = st.text_input("Buscar", placeholder="Nombre del producto...",
                           label_visibility="collapsed")

    only_featured = st.checkbox("Solo destacados")

# ── Productos ──────────────────────────────────────────────────────
products = get_products(
    category_slug=cat_options[selected_cat],
    technique=technique_options[selected_technique],
    search=search or None,
    only_featured=only_featured,
)

st.markdown(f"**{len(products)}** piezas encontradas")

if not products:
    st.info("No hay productos que coincidan con los filtros seleccionados.")
else:
    # Grid de 3 columnas
    cols = st.columns(3, gap="medium")
    for idx, product in enumerate(products):
        with cols[idx % 3]:
            render_product_card(product)