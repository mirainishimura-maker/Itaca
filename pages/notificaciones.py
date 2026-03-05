"""🔔 Notificaciones"""
import streamlit as st
import database as db


def render():
    email = st.session_state.get("current_user", "")

    st.markdown("## 🔔 Notificaciones")

    notifs = db.get_notificaciones(email)
    if notifs:
        for n in notifs:
            icon = "🔴" if n.get("prioridad") == "Alta" else "🔵"
            leida = "✅" if n.get("leida") else "🆕"
            with st.expander(f"{leida} {icon} {n['titulo']}"):
                st.markdown(f"**Tipo:** {n.get('tipo', '')}")
                st.markdown(f"**Mensaje:** {n['mensaje']}")
                st.caption(f"📅 {n['fecha'][:16]}")
                if not n.get("leida"):
                    if st.button("Marcar como leída", key=f"read_{n['notif_id']}"):
                        with db.get_db() as conn:
                            conn.execute("UPDATE notificaciones SET leida=1 WHERE notif_id=?",
                                         (n["notif_id"],))
                        st.rerun()
    else:
        st.info("No tienes notificaciones. ¡Todo en orden!")
