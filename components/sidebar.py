"""Sidebar con avatar, color favorito, dark mode y todos los módulos"""
import streamlit as st
from config import APP_NAME, APP_ICON
import database as db

ROL_COLORS = {"Admin":"#E53935","Líder":"#FFB300","Coordinador":"#7E57C2","Colaborador":"#43A047"}


def render_sidebar():
    with st.sidebar:
        email  = st.session_state.get("current_user", "")
        user   = db.get_user(email)
        ident  = db.get_identidad(email)
        prefs  = db.get_preferencias_ui(email)
        color  = prefs.get("color_favorito", "#26C6DA")
        rol    = user["rol"] if user else "Colaborador"
        st.session_state.user_rol  = rol
        st.session_state.user_name = user["nombre"] if user else ""
        st.session_state.user_data = ident

        # ── Logo ──
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0 6px;">
            <span style="font-size:2rem;">⚓</span>
            <div style="font-size:1.05rem;font-weight:700;color:white;">{APP_NAME}</div>
            <div style="font-size:0.68rem;color:rgba(255,255,255,0.7);">Plataforma de Gestión y Desarrollo Humano</div>
        </div>""", unsafe_allow_html=True)
        st.divider()

        # ── Avatar + info ──
        if user:
            nombre    = user["nombre"]
            iniciales = "".join(p[0].upper() for p in nombre.split()[:2])
            foto_url  = prefs.get("foto_url", "")
            if foto_url and foto_url.startswith("data:"):
                av = f'<img src="{foto_url}" style="width:52px;height:52px;border-radius:50%;object-fit:cover;border:2px solid {color};margin:0 auto;display:block;" />'
            else:
                av = f'<div style="width:52px;height:52px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px;color:white;margin:0 auto;">{iniciales}</div>'
            rol_color = ROL_COLORS.get(rol, "#26C6DA")
            unidad    = user.get("unidad","")
            disc      = ident.get("arquetipo_disc") if ident else None
            disc_lbl  = ""
            if disc:
                from config import DISC_TYPES
                d = DISC_TYPES.get(disc, {})
                disc_lbl = f'<span style="font-size:0.7rem;color:rgba(255,255,255,0.75);">{d.get("emoji","")} {disc}</span>'
            puntos    = db.get_total_puntos(email)
            unread    = db.count_unread(email)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.1);border-radius:12px;padding:12px;text-align:center;margin-bottom:6px;">
                {av}
                <div style="color:white;font-weight:600;font-size:0.88rem;margin-top:6px;">{nombre}</div>
                {disc_lbl}
                <div style="display:flex;justify-content:center;gap:5px;margin-top:5px;flex-wrap:wrap;">
                    <span style="background:{rol_color};color:white;border-radius:10px;padding:1px 8px;font-size:0.68rem;font-weight:600;">{rol}</span>
                    <span style="background:rgba(255,255,255,0.15);color:white;border-radius:10px;padding:1px 8px;font-size:0.68rem;">{unidad}</span>
                </div>
                <div style="color:rgba(255,255,255,0.8);font-size:0.75rem;margin-top:5px;">⭐ {puntos} pts{"  🔔 "+str(unread) if unread else ""}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Navegación ──
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Inicio"

        def _btn(icon, name, visible=True):
            if not visible: return
            label = f"{icon} {name}"
            if name == "Notificaciones" and user:
                n = db.count_unread(email)
                if n: label += f" ({n})"
            active = st.session_state.current_page == name
            if st.button(label, key=f"nav_{name}", use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state.current_page = name
                st.rerun()

        st.markdown("<div style='color:rgba(255,255,255,0.45);font-size:0.62rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;'>Principal</div>", unsafe_allow_html=True)
        _btn("🏠", "Inicio")
        _btn("👤", "Mi Esencia")
        _btn("🎯", "Mi Estrategia")
        _btn("❤️", "Cultura Ítaca")
        _btn("🧠", "Mi Brújula")

        st.markdown("<div style='color:rgba(255,255,255,0.45);font-size:0.62rem;text-transform:uppercase;letter-spacing:1px;margin:8px 0 4px;'>Desarrollo</div>", unsafe_allow_html=True)
        _btn("🎬", "🎬 Ítaca Play")
        _btn("🎓", "🎓 Capacitaciones")
        _btn("🔄", "Evaluación 360°")
        _btn("🏆", "Mis Logros")

        st.markdown("<div style='color:rgba(255,255,255,0.45);font-size:0.62rem;text-transform:uppercase;letter-spacing:1px;margin:8px 0 4px;'>Liderazgo</div>", unsafe_allow_html=True)
        _btn("🧭", "Mi Hexágono",   rol in ["Admin","Líder","Coordinador"])
        _btn("📄", "📄 Reportes",   rol in ["Admin","Líder","Coordinador"])
        _btn("📊", "Admin Dashboard", rol == "Admin")

        st.markdown("<div style='color:rgba(255,255,255,0.45);font-size:0.62rem;text-transform:uppercase;letter-spacing:1px;margin:8px 0 4px;'>Sistema</div>", unsafe_allow_html=True)
        _btn("🔔", "Notificaciones")

        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
        st.markdown("<div style='text-align:center;color:rgba(255,255,255,0.35);font-size:0.68rem;margin-top:6px;'>v2.0 · Odisea 2026</div>", unsafe_allow_html=True)
