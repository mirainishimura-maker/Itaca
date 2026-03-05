"""🧠 Mi Brújula — Inteligencia Emocional + Journal"""
import streamlit as st
import database as db
from config import COMPETENCIAS_IE, TURQ


def render():
    email = st.session_state.get("current_user", "")

    st.markdown("## 🧠 Mi Brújula Emocional")

    tabs = st.tabs(["📝 Journal", "🧭 Evaluar IE", "📈 Mi Evolución"])

    # ── TAB 1: JOURNAL ──
    with tabs[0]:
        st.markdown("#### ¿Cómo te sientes hoy?")
        emociones_opciones = ["Alegría","Tristeza","Ansiedad","Calma","Frustración",
                              "Gratitud","Enojo","Esperanza","Miedo","Orgullo"]
        with st.form("journal_form"):
            emociones = st.multiselect("Emociones", emociones_opciones)
            intensidad = st.slider("Intensidad", 1, 10, 5)
            trigger = st.text_input("¿Qué lo provocó?")
            pensamiento = st.text_area("¿Qué pensaste?")
            reflexion = st.text_area("¿Qué aprendiste?")
            estrategia = st.text_input("¿Qué harás diferente?")
            if st.form_submit_button("Guardar en mi Journal"):
                if emociones:
                    ok, msg = db.save_journal(email, emociones, intensidad, trigger,
                                               pensamiento, reflexion, estrategia, 0, "Trabajo")
                    if ok:
                        st.success(msg)
                        st.rerun()
                else:
                    st.warning("Selecciona al menos una emoción.")

        st.divider()
        st.markdown("#### 📖 Mis entradas recientes")
        entries = db.get_my_journal(email, 5)
        for e in entries:
            with st.expander(f"📅 {e['fecha'][:10]} — {e.get('emociones','')}"):
                st.markdown(f"**Intensidad:** {e.get('intensidad','')}/10")
                st.markdown(f"**Trigger:** {e.get('trigger_text','')}")
                st.markdown(f"**Reflexión:** {e.get('reflexion','')}")

    # ── TAB 2: EVALUAR IE ──
    with tabs[1]:
        st.markdown("#### Autoevaluación de IE (Goleman)")
        with st.form("brujula_form"):
            puntajes = {}
            for comp in COMPETENCIAS_IE:
                puntajes[comp["nombre"]] = st.slider(
                    f"{comp['emoji']} {comp['nombre']}: {comp['pregunta']}",
                    1, 5, 3, key=f"ie_{comp['nombre']}"
                )
            reflexion = st.text_area("Reflexión")
            if st.form_submit_button("Guardar evaluación IE"):
                ok, msg = db.save_brujula(email, puntajes, reflexion)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning(msg)

    # ── TAB 3: EVOLUCIÓN ──
    with tabs[2]:
        historial = db.get_my_brujula(email)
        if historial:
            for h in historial:
                with st.expander(f"📅 {h['periodo']} — Promedio: {h['promedio']}"):
                    for comp in COMPETENCIAS_IE:
                        key = comp["nombre"].lower().replace(" ", "_").replace("á","a").replace("ó","o").replace("í","i")
                        val = h.get(key, 0)
                        st.markdown(f"{comp['emoji']} **{comp['nombre']}:** {val}/5")
                    st.markdown(f"**Punto fuerte:** {h.get('comp_alta','')}")
                    st.markdown(f"**A mejorar:** {h.get('comp_baja','')}")
        else:
            st.info("Aún no tienes evaluaciones IE.")
