"""🎓 Capacitaciones Externas — registro + flujo aprobación líder"""
import streamlit as st
import database as db
from datetime import date

PUNTOS_POR_HORA   = 10
BONUS_CERTIFICADO = 50
TIPOS_CAP  = ["Online","Presencial","Taller","Bootcamp","Seminario","Conferencia","Otro"]
PLATAFORMAS = ["Coursera","Udemy","LinkedIn Learning","edX","Platzi","YouTube","Institución propia","Universidad","Otro"]


def render():
    email  = st.session_state.get("current_user","")
    rol    = st.session_state.get("user_rol","Colaborador")
    nombre = st.session_state.get("user_name","")
    es_ap  = rol in ["Admin","Líder","Coordinador"]

    st.markdown("## 🎓 Capacitaciones Externas")
    st.caption("Registra tu aprendizaje fuera de Ítaca Play y suma puntos al obtener aprobación.")

    tabs = st.tabs(["📚 Mis Capacitaciones","➕ Registrar"] +
                   (["✅ Pendientes","📊 Equipo"] if es_ap else []))

    with tabs[0]: _mis_caps(email)
    with tabs[1]: _registrar(email, nombre)
    if es_ap:
        with tabs[2]: _aprobar(email, rol)
        with tabs[3]: _equipo(email, rol)


def _pts(horas, cert): return int(horas)*PUNTOS_POR_HORA + (BONUS_CERTIFICADO if cert else 0)


def _mis_caps(email):
    caps = db.get_capacitaciones_ext(email)
    if not caps:
        st.info("Aún no has registrado capacitaciones externas.")
        st.caption("Ve a ➕ Registrar para agregar tu primera capacitación."); return
    ap = [c for c in caps if c["estado"]=="Aprobado"]
    pe = [c for c in caps if c["estado"]=="Pendiente"]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📚 Total",      len(caps))
    c2.metric("✅ Aprobadas",  len(ap))
    c3.metric("⏳ Pendientes", len(pe))
    c4.metric("⭐ Pts",        sum(c.get("puntos_otorgados",0) for c in ap))
    st.divider()
    for cap in caps:
        ico = {"Aprobado":"✅","Pendiente":"⏳","Rechazado":"❌"}.get(cap["estado"],"📚")
        pts = cap.get("puntos_otorgados",0)
        with st.expander(f"{ico} **{cap['nombre_cap']}** — {cap.get('institucion','')} | {cap.get('horas',0)}h | {cap['estado']}" + (f" | ⭐+{pts}" if pts else "")):
            c1,c2 = st.columns(2)
            c1.markdown(f"**Tipo:** {cap.get('tipo','')}")
            c1.markdown(f"**Horas:** {cap.get('horas',0)}")
            c1.markdown(f"**Fecha:** {cap.get('fecha','')}")
            c2.markdown(f"**Institución:** {cap.get('institucion','')}")
            c2.markdown(f"**Certificado:** {'🏅 Sí' if cap.get('certificado') else '—'}")
            c2.markdown(f"**Costo:** {'🏢 Empresa' if cap.get('costo_empresa') else '💰 Personal'}")
            if cap.get("notas"): st.markdown(f"**Notas:** {cap['notas']}")
            if cap["estado"]=="Rechazado" and cap.get("motivo_rechazo"):
                st.error(f"Motivo: {cap['motivo_rechazo']}")
            if cap["estado"]=="Pendiente":
                st.info("⏳ Pendiente de revisión por tu líder.")


def _registrar(email, nombre):
    st.markdown("#### ➕ Registrar nueva capacitación")
    st.markdown('<div style="background:#E3F2FD;border-radius:10px;padding:11px 15px;margin-bottom:14px;font-size:0.9rem;">💡 <b>Puntos:</b> 🕐 10 pts/hora + 🏅 50 pts bonus si tienes certificado</div>', unsafe_allow_html=True)
    with st.form("form_cap", clear_on_submit=True):
        nc = st.text_input("📚 Nombre del curso *")
        c1,c2 = st.columns(2)
        tipo = c1.selectbox("Tipo", TIPOS_CAP)
        plat = c2.selectbox("Institución/Plataforma", PLATAFORMAS)
        inst_custom = ""
        if plat == "Otro":
            inst_custom = st.text_input("Especifica la institución")
        c3,c4 = st.columns(2)
        horas = c3.number_input("Horas *", min_value=1, max_value=2000, value=8)
        fecha = c4.date_input("Fecha", value=date.today())
        c5,c6 = st.columns(2)
        cert  = c5.checkbox("🏅 Obtuve certificado")
        emp   = c6.checkbox("🏢 La empresa pagó")
        notas = st.text_area("Notas (opcional)", max_chars=400)
        pts_p = _pts(horas, cert)
        st.markdown(f"**Puntos estimados al aprobar: ⭐ {pts_p}** ({horas}h × 10{' + 50 cert.' if cert else ''})")
        if st.form_submit_button("📨 Enviar para aprobación", type="primary", use_container_width=True):
            if not nc.strip():
                st.error("Ingresa el nombre del curso.")
            else:
                inst = inst_custom if plat=="Otro" else plat
                ok, msg = db.registrar_capacitacion_ext(email, nc, tipo, inst, int(horas),
                                                         str(fecha), int(cert), int(emp), notas)
                if ok: st.success(f"✅ {msg}"); st.balloons()
                else:  st.error(msg)


def _aprobar(email_lider, rol):
    st.markdown("#### ✅ Pendientes de aprobación")
    pend = db.get_caps_pendientes_aprobacion(email_lider, rol)
    if not pend:
        st.success("✅ No hay capacitaciones pendientes."); return
    st.info(f"🔔 {len(pend)} esperando tu aprobación.")
    for cap in pend:
        pts = _pts(cap.get("horas",0), bool(cap.get("certificado")))
        with st.expander(f"⏳ **{cap['nombre_cap']}** — {cap.get('nombre_colaborador',cap['email'])} | {cap.get('horas',0)}h | ⭐{pts} pts"):
            c1,c2 = st.columns(2)
            c1.markdown(f"**Colaborador:** {cap.get('nombre_colaborador',cap['email'])}")
            c1.markdown(f"**Unidad:** {cap.get('unidad','')}")
            c1.markdown(f"**Tipo:** {cap.get('tipo','')}")
            c2.markdown(f"**Institución:** {cap.get('institucion','')}")
            c2.markdown(f"**Horas:** {cap.get('horas',0)}")
            c2.markdown(f"**Certificado:** {'🏅 Sí' if cap.get('certificado') else 'No'}")
            if cap.get("notas"): st.markdown(f"**Notas:** {cap['notas']}")
            st.markdown(f"**Puntos a otorgar: ⭐ {pts}**")
            ca,cb,cc = st.columns([2,2,3])
            with ca:
                if st.button("✅ Aprobar", key=f"a_{cap['cap_id']}", type="primary"):
                    db.aprobar_capacitacion(cap["cap_id"], email_lider, pts)
                    st.success(f"✅ +{pts} pts acreditados."); st.rerun()
            with cb:
                mot = st.text_input("Motivo rechazo", key=f"m_{cap['cap_id']}", placeholder="Opcional")
            with cc:
                if st.button("❌ Rechazar", key=f"r_{cap['cap_id']}"):
                    db.rechazar_capacitacion(cap["cap_id"], email_lider, mot)
                    st.warning("Rechazada."); st.rerun()


def _equipo(email_lider, rol):
    st.markdown("#### 📊 Capacitaciones de tu equipo")
    stats = db.get_caps_stats_equipo(email_lider, rol)
    if not stats:
        st.info("Tu equipo aún no tiene capacitaciones."); return
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("📚 Total",    sum(s["total"] for s in stats))
    c2.metric("✅ Aprobadas",sum(s["aprobadas"] for s in stats))
    c3.metric("🕐 Horas",    sum(s["horas_totales"] for s in stats))
    c4.metric("⭐ Puntos",   sum(s["puntos_totales"] for s in stats))
    st.divider()
    st.markdown("#### 🏅 Ranking de aprendizaje")
    for i,s in enumerate(sorted(stats, key=lambda x: x["horas_totales"], reverse=True), 1):
        med = ["🥇","🥈","🥉"][i-1] if i<=3 else f"#{i}"
        st.markdown(f"{med} **{s['nombre']}** — {s['aprobadas']} cursos | {s['horas_totales']}h | ⭐{s['puntos_totales']} pts")
