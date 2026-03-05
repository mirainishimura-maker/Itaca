"""❤️ Cultura Ítaca — Check-ins + Faros + Pilares I+M"""
import streamlit as st
import database as db
from config import (ESTADOS_CHECKIN, AREAS_PREOCUPACION, ALL_ETIQUETAS,
                    TIPOS_FARO, PILARES, TURQ)


def render():
    email = st.session_state.get("current_user", "")

    st.markdown("## ❤️ Cultura Ítaca")

    tabs = st.tabs(["💬 Check-in", "🔦 Faros", "🏛️ Pilares I+M", "📊 Mi Historial"])

    # ── TAB 1: CHECK-IN ──
    with tabs[0]:
        done = db.checkin_done_this_week(email)
        if done:
            st.success("✅ Ya hiciste tu check-in esta semana.")
        else:
            st.markdown("#### ¿Cómo estás esta semana?")
            with st.form("checkin_form"):
                estado = st.radio("Estado general", list(ESTADOS_CHECKIN.keys()),
                                  format_func=lambda x: f"{ESTADOS_CHECKIN[x]} {x}", horizontal=True)
                estres = st.slider("Nivel de estrés", 1, 5, 3)
                area = st.selectbox("Área de preocupación", AREAS_PREOCUPACION)
                etiquetas = st.multiselect("¿Cómo te sientes?", ALL_ETIQUETAS)
                comentario = st.text_area("Comentario (opcional)", max_chars=300)
                if st.form_submit_button("Enviar Check-in", type="primary"):
                    ok, msg = db.save_checkin(email, estado, estres, area, etiquetas, comentario)
                    if ok:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning(msg)

    # ── TAB 2: FAROS ──
    with tabs[1]:
        st.markdown("#### 🔦 Enviar un Faro de Reconocimiento")
        st.caption("Máximo 3 faros por semana. ¡Los cross-company valen x2!")

        users = db.get_all_users()
        otros = [u for u in users if u["email"] != email]
        nombres = [f"{u['nombre']} ({u['unidad']})" for u in otros]

        with st.form("faro_form"):
            dest_idx = st.selectbox("¿A quién?", range(len(nombres)),
                                    format_func=lambda i: nombres[i])
            tipo = st.selectbox("Tipo de Faro", list(TIPOS_FARO.keys()),
                                format_func=lambda x: f"{TIPOS_FARO[x]['emoji']} {x}")
            mensaje = st.text_area("Mensaje", placeholder="¿Por qué merece este faro?", max_chars=300)
            if st.form_submit_button("🔦 Enviar Faro", type="primary"):
                if mensaje:
                    ok, msg = db.save_faro(email, otros[dest_idx]["email"], tipo, mensaje)
                    if ok:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.warning(msg)
                else:
                    st.warning("Escribe un mensaje para tu faro.")

        # Muro
        st.divider()
        st.markdown("#### 🌊 Muro de Faros")
        faros = db.get_faros_publicos(10)
        for f in faros:
            info = TIPOS_FARO.get(f["tipo_faro"], {})
            st.markdown(
                f"{info.get('emoji','🔦')} **{f['nombre_emisor']}** → **{f['nombre_receptor']}** "
                f"| _{f['mensaje'][:100]}_"
            )
            if st.button(f"👏 Celebrar", key=f"cel_{f['faro_id']}"):
                db.celebrar_faro(f["faro_id"])
                st.rerun()

    # ── TAB 3: PILARES ──
    with tabs[2]:
        st.markdown("#### 🏛️ Los 3 Pilares de Ítaca + Gung Ho")
        for p in PILARES:
            with st.expander(f"{p['animal']} **{p['nombre']}** — {p['gungho']}"):
                st.markdown(f"**Principio:** {p['principio']}")
                st.markdown(f"**Faro:** {p['faro']}")
                st.markdown(p["desc"])
                st.caption(f"💬 _{p['frase']}_")

    # ── TAB 4: MI HISTORIAL ──
    with tabs[3]:
        st.markdown("#### 📬 Faros Recibidos")
        recibidos = db.get_faros_recibidos(email)
        if recibidos:
            for f in recibidos:
                st.markdown(f"🔦 De **{f['nombre_emisor']}** — {f['tipo_faro']}: _{f['mensaje'][:80]}_")
        else:
            st.info("Aún no has recibido faros.")

        st.divider()
        st.markdown("#### 📤 Faros Enviados")
        enviados = db.get_faros_enviados(email)
        if enviados:
            for f in enviados:
                st.markdown(f"🔦 Para **{f['nombre_receptor']}** — {f['tipo_faro']}: _{f['mensaje'][:80]}_")
        else:
            st.info("Aún no has enviado faros.")
