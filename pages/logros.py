"""🏆 Mis Logros — Gamificación"""
import streamlit as st
import database as db


def render():
    email = st.session_state.get("current_user", "")

    st.markdown("## 🏆 Mis Logros")

    puntos = db.get_total_puntos(email)
    logros = db.get_my_logros(email)

    # Nivel
    if puntos >= 500:
        nivel, emoji = "Almirante", "🎖️"
    elif puntos >= 200:
        nivel, emoji = "Capitán", "⚓"
    elif puntos >= 80:
        nivel, emoji = "Navegante", "🧭"
    else:
        nivel, emoji = "Marinero", "🚣"

    st.markdown(f"""
    <div style="text-align:center; padding:20px; background:linear-gradient(135deg, #26C6DA22, #FFB30022);
                border-radius:16px;">
        <p style="font-size:2.5rem; margin:0;">{emoji}</p>
        <h2>Nivel: {nivel}</h2>
        <p style="font-size:1.5rem;">⭐ {puntos} puntos</p>
        <p>{len(logros)} badges desbloqueados</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if logros:
        st.markdown("### 🎖️ Badges obtenidos")
        cols = st.columns(3)
        for i, l in enumerate(logros):
            with cols[i % 3]:
                st.markdown(f"""
                <div style="text-align:center; padding:15px; background:white;
                            border-radius:12px; border:1px solid #E0E0E0; margin:5px 0;">
                    <p style="font-size:2rem; margin:0;">{l.get('icono','🏆')}</p>
                    <p style="font-weight:600; margin:5px 0;">{l['nombre_badge']}</p>
                    <p style="color:#777; font-size:0.85rem;">{l.get('descripcion','')}</p>
                    <p style="color:#26C6DA;">+{l['puntos']} pts</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Aún no tienes badges. ¡Completa actividades para desbloquearlos!")
