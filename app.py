"""
⚓ Ítaca OS 2.0 — Punto de entrada principal
"""
import streamlit as st
import sys, os, importlib

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import APP_NAME, APP_ICON, GLOBAL_CSS
import database as db

st.set_page_config(
    page_title=f"{APP_ICON} {APP_NAME}",
    page_icon="⚓",
    layout="centered",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
db.init_db()

PAGE_MAP = {
    "Inicio":             "pages.home",
    "Mi Esencia":         "pages.mi_esencia",
    "Mi Estrategia":      "pages.mi_estrategia",
    "Mi Hexágono":        "pages.hexagono",
    "Cultura Ítaca":      "pages.cultura",
    "Mi Brújula":         "pages.brujula",
    "Mis Logros":         "pages.logros",
    "🎬 Ítaca Play":      "pages.itaca_play",
    "Evaluación 360°":    "pages.eval_360",
    "🎓 Capacitaciones":  "pages.capacitaciones",
    "📄 Reportes":        "pages.reportes_page",
    "Notificaciones":     "pages.notificaciones",
    "Admin Dashboard":    "pages.admin",
}


def _show_login():
    st.markdown("""
    <div style="text-align:center;padding:40px 0 20px;">
        <h1>⚓ Bienvenido a Ítaca OS 2.0</h1>
        <p style="color:#757575;">Plataforma de Gestión y Desarrollo Humano</p>
    </div>""", unsafe_allow_html=True)
    with st.form("login_form"):
        email    = st.text_input("Correo electrónico", placeholder="tu.nombre@itaca.com")
        password = st.text_input("Contraseña", type="password")
        submit   = st.form_submit_button("🚢 Entrar a la Odisea", use_container_width=True)
        if submit:
            if not email or not password:
                st.error("Ingresa tu correo y contraseña."); return
            user = db.get_user(email)
            if not user:                          st.error("❌ Usuario no encontrado.");  return
            if user.get("password") != password:  st.error("❌ Contraseña incorrecta."); return
            if user.get("estado") != "Activo":    st.error("❌ Cuenta inactiva."); return
            st.session_state.logged_in    = True
            st.session_state.current_user = email
            st.session_state.user_rol     = user["rol"]
            st.session_state.user_name    = user["nombre"]
            st.rerun()


def _needs_pasaporte():
    email = st.session_state.get("current_user")
    if not email: return False
    ident = db.get_identidad(email)
    return bool(ident) and not ident.get("arquetipo_disc")


# ── FLUJO ──
if not st.session_state.get("logged_in"):
    _show_login()
    st.stop()

if _needs_pasaporte():
    with st.sidebar:
        st.markdown(f"## {APP_ICON} {APP_NAME}")
        st.caption(f"👤 {st.session_state.get('user_name','')}")
        st.divider()
        st.warning("🪪 Completa tu Pasaporte para desbloquear el sistema.")
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
    try:
        from pages.pasaporte import render as render_pasaporte
        render_pasaporte()
    except Exception as e:
        st.error(f"Error cargando Pasaporte: {e}")
        import traceback; st.code(traceback.format_exc())
    st.stop()

from components.sidebar import render_sidebar
render_sidebar()

page = st.session_state.get("current_page", "Inicio")
module_name = PAGE_MAP.get(page)
if module_name:
    try:
        mod = importlib.import_module(module_name)
        mod.render()
    except Exception as e:
        st.error(f"Error cargando '{page}': {e}")
        import traceback; st.code(traceback.format_exc())
else:
    st.error(f"Página no encontrada: {page}")
