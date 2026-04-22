import streamlit as st


def inject_css():
    with open("assets/style.css") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_navbar(cart_count: int = 0, is_admin: bool = False):
    cart_label = f"Carrito ({cart_count})" if cart_count > 0 else "Carrito"
    admin_link = '<a href="/admin">Admin</a>' if is_admin else ""

    st.markdown(f"""
        <div class="navbar">
            <div class="brand">🏺 Green Shop</div>
            <div class="nav-links">
                <a href="/catalog">Catálogo</a>
                <a href="/cart">{cart_label}</a>
                <a href="/account">Mi cuenta</a>
                {admin_link}
            </div>
        </div>
    """, unsafe_allow_html=True)


def page_setup(title: str, cart_count: int = 0, is_admin: bool = False):
    st.set_page_config(
        page_title=f"{title} — Green Shop",
        page_icon="🏺",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()
    render_navbar(cart_count=cart_count, is_admin=is_admin)