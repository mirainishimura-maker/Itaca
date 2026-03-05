"""📊 Admin Dashboard + Torre de Control"""
import streamlit as st
import database as db
from config import NINEBOX_LABELS


def render():
    email = st.session_state.get("current_user", "")
    rol = st.session_state.get("user_rol", "")

    if rol != "Admin":
        st.error("Acceso restringido a administradores.")
        return

    st.markdown("## 📊 Admin Dashboard")

    tabs = st.tabs(["📈 Métricas", "🔮 Torre de Control", "👥 Colaboradores"])

    # ── TAB 1: MÉTRICAS ──
    with tabs[0]:
        analytics = db.get_analytics()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Activos", analytics["total_users"])
        c2.metric("💬 Check-ins (sem)", analytics["checkins_week"])
        c3.metric("😰 Estrés prom.", analytics["avg_estres"])
        c4.metric("🔦 Faros (mes)", analytics["faros_mes"])

        st.divider()
        cultura = db.get_reporte_cultura()
        st.markdown(f"**Total faros:** {cultura['total_faros']} | "
                    f"**Cross-company:** {cultura.get('cross_company', 0)} | "
                    f"**Celebraciones:** {cultura.get('celebraciones', 0)}")

    # ── TAB 2: TORRE DE CONTROL ──
    with tabs[1]:
        st.markdown("### 🔮 Oráculo de Fugas")
        st.caption("Colaboradores con estrés alto + sin faros + tareas vencidas")
        risk = db.get_flight_risk()
        if risk:
            for r in risk:
                st.error(
                    f"🚨 **{r['nombre']}** ({r['unidad']}) — "
                    f"Estrés: {r['avg_estres']}/5 | Faros: {r['faros_total']} | "
                    f"Tareas vencidas: {r['tareas_vencidas']}"
                )
        else:
            st.success("✅ No hay alertas de fuga activas.")

        st.divider()
        st.markdown("### 📊 Matriz 9-Box")
        box_data = db.get_9box_data()
        if box_data:
            for b in box_data:
                label = NINEBOX_LABELS.get(f"{b['p_level']}/{b['d_level']}", "")
                st.markdown(
                    f"**{b['nombre']}** ({b['unidad']}) — "
                    f"Desempeño: {b['desempeno']}% | Potencial: {b['potencial']}% | "
                    f"{label}"
                )
        else:
            st.info("Sin datos suficientes para la matriz.")

    # ── TAB 3: COLABORADORES ──
    with tabs[2]:
        st.markdown("### 👥 Gestión de Colaboradores")
        all_users = db.get_all_users_admin()
        import pandas as pd
        if all_users:
            df = pd.DataFrame(all_users)
            cols_show = ["nombre", "email", "rol", "unidad", "estado", "puesto"]
            cols_exist = [c for c in cols_show if c in df.columns]
            st.dataframe(df[cols_exist], use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### ➕ Agregar Colaborador")
        with st.form("add_colab"):
            c1, c2 = st.columns(2)
            new_email = c1.text_input("Email")
            new_nombre = c2.text_input("Nombre completo")
            c3, c4 = st.columns(2)
            new_rol = c3.selectbox("Rol", ["Colaborador", "Coordinador", "Líder", "Admin"])
            new_unidad = c4.text_input("Unidad")
            c5, c6 = st.columns(2)
            new_cargo = c5.text_input("Cargo")
            new_tel = c6.text_input("Teléfono")
            new_lider = st.text_input("Email del líder")
            if st.form_submit_button("Agregar"):
                if new_email and new_nombre:
                    ok, msg = db.add_colaborador(new_email, new_nombre, new_rol,
                                                  new_unidad, new_lider, new_cargo, new_tel, "")
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
