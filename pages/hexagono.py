"""🧭 Hexágono de Liderazgo — 6 dimensiones + Plan Obligatorio"""
import streamlit as st
import database as db
from config import DIMENSIONES_HEXAGONO, ESCALA, TURQ
from datetime import datetime


def render():
    email = st.session_state.get("current_user", "")

    st.markdown("## 🧭 Hexágono de Liderazgo")
    st.caption("Los 6 mínimos que todo líder Ítaca debe dominar")

    tabs = st.tabs(["📝 Evaluar", "📈 Historial"])

    with tabs[0]:
        with st.form("hex_form"):
            st.markdown("#### Autoevaluación mensual")
            puntajes = {}
            for dim in DIMENSIONES_HEXAGONO:
                puntajes[dim["nombre"]] = st.slider(
                    f"{dim['emoji']} {dim['nombre']}: {dim['pregunta']}",
                    1, 5, 3, key=f"hex_{dim['nombre']}"
                )

            reflexion = st.text_area("Reflexión del mes", placeholder="¿Cómo me fue este mes?")

            # Detectar plan obligatorio
            vals = list(puntajes.values())
            necesita_plan = db.check_plan_obligatorio(puntajes)

            plan1 = plan_fecha1 = plan2 = plan_fecha2 = ""
            if necesita_plan:
                st.warning("⚠️ Tienes dimensiones en zona crítica (≤2). Debes crear un plan de acción.")
                plan1 = st.text_input("📋 Acción de mejora 1 (obligatoria)")
                plan_fecha1 = str(st.date_input("Fecha compromiso acción 1"))
                plan2 = st.text_input("📋 Acción de mejora 2 (opcional)")
                if plan2:
                    plan_fecha2 = str(st.date_input("Fecha compromiso acción 2"))

            if st.form_submit_button("Guardar evaluación"):
                if necesita_plan and not plan1:
                    st.error("Debes completar al menos una acción de mejora.")
                else:
                    periodo = datetime.now().strftime("%Y-%m")
                    prom = round(sum(vals) / 6, 2)
                    nombres = [d["nombre"] for d in DIMENSIONES_HEXAGONO]
                    dim_baja = nombres[vals.index(min(vals))]
                    dim_alta = nombres[vals.index(max(vals))]
                    db.save_hexagono(email, periodo, *vals, prom, reflexion,
                                     dim_baja, dim_alta, plan1, plan_fecha1, plan2, plan_fecha2)
                    st.success(f"✅ Evaluación guardada. Promedio: {prom}")
                    st.rerun()

    with tabs[1]:
        historial = db.get_my_hexagono(email)
        if historial:
            for h in historial:
                with st.expander(f"📅 {h['periodo']} — Promedio: {h['promedio']}"):
                    for dim in DIMENSIONES_HEXAGONO:
                        key = dim["nombre"].lower().replace(" ", "_").replace("ó", "o").replace("á", "a")
                        # Map dimension names to column names
                        col_map = {
                            "Visión Corporativa": "vision",
                            "Planificación": "planificacion",
                            "Encaje de Talento": "encaje",
                            "Entrenamiento": "entrenamiento",
                            "Evaluación y Mejora": "evaluacion_mejora",
                            "Reconocimiento": "reconocimiento",
                        }
                        col = col_map.get(dim["nombre"], "")
                        val = h.get(col, 0)
                        label = ESCALA.get(val, "")
                        st.markdown(f"{dim['emoji']} **{dim['nombre']}:** {val}/5 ({label})")
                    if h.get("plan_accion_1"):
                        st.markdown(f"📋 **Plan:** {h['plan_accion_1']} (hasta {h.get('plan_accion_fecha_1','')})")
        else:
            st.info("Aún no tienes evaluaciones. ¡Empieza arriba!")
