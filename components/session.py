import streamlit as st
from db.models import User


def get_current_user() -> User | None:
    return st.session_state.get("user", None)


def set_current_user(user: User) -> None:
    st.session_state.user = user


def logout() -> None:
    st.session_state.pop("user", None)
    st.session_state.pop("cart", None)


def is_logged_in() -> bool:
    return get_current_user() is not None


def is_admin() -> bool:
    user = get_current_user()
    if not user:
        return False
    from db.models import UserRole
    return user.role == UserRole.admin


def require_login() -> User:
    """Redirige al login si no hay sesión activa."""
    user = get_current_user()
    if not user:
        st.warning("Necesitás iniciar sesión para continuar.")
        st.stop()
    return user


def require_admin() -> User:
    """Redirige si el usuario no es admin."""
    user = require_login()
    if not is_admin():
        st.error("No tenés permisos para acceder a esta sección.")
        st.stop()
    return user