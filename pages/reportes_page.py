"""📄 Reportes PDF — Admin y Líderes generan el reporte mensual de su unidad"""
import streamlit as st
import database as db
from datetime import datetime

ROLES = ["Admin","Líder","Coordinador"]
MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


def render():
    email  = st.session_state.get("current_user","")
    rol    = st.session_state.get("user_rol","Colaborador")
    nombre = st.session_state.get("user_name","")

    if rol not in ROLES:
        st.error("🔒 Solo líderes y administradores pueden generar reportes."); return

    st.markdown("## 📄 Reportes PDF")
    st.caption("Genera el reporte mensual de tu unidad con todas las métricas clave.")

    ident = db.get_identidad(email)
    unidad_propia = ident.get("unidad","") if ident else ""

    if rol == "Admin":
        unidades = [u["unidad"] for u in db.get_units() if u.get("unidad")]
        unidad_sel = st.selectbox("📍 Unidad", unidades)
        lider_email = _get_lider_unidad(unidad_sel)
    else:
        unidad_sel  = unidad_propia
        lider_email = email
        st.info(f"📍 Unidad: **{unidad_sel}**")

    if not unidad_sel:
        st.warning("No tienes unidad asignada."); return

    st.divider()
    c1,c2 = st.columns(2)
    mes_idx = c1.selectbox("📅 Mes", range(12), format_func=lambda i: MESES[i], index=datetime.now().month-1)
    anio    = c2.number_input("Año", min_value=2024, max_value=2030, value=datetime.now().year)
    mes_str = f"{MESES[mes_idx]} {anio}"

    periodos = db.get_all_periodos_360()
    popts = {"(Ninguno)": None}
    for p in periodos: popts[p["nombre"]] = p["periodo_id"]
    periodo_nombre = st.selectbox("🔄 Incluir datos de Evaluación 360° (opcional)", list(popts.keys()))
    periodo_id = popts[periodo_nombre]

    st.divider()
    st.markdown("#### 📋 El reporte incluirá:")
    c = st.columns(3)
    for i,(icon,label) in enumerate([("💬","Clima & Check-ins"),("🔦","Faros"),("🎯","Focos & KRs"),
                                      ("🧭","Hexágono"),("🔄","Evaluación 360°"),("🎬","Ítaca Play")]):
        c[i%3].markdown(f"{icon} {label}")

    st.divider()
    if st.button("🚀 Generar Reporte PDF", type="primary", use_container_width=True):
        with st.spinner(f"Generando reporte de {unidad_sel} — {mes_str}…"):
            try:
                datos = db.get_reporte_unidad_completo(unidad_sel, lider_email, periodo_id)
                from reportes import generar_reporte_pdf
                pdf = generar_reporte_pdf(
                    unidad=unidad_sel, mes=mes_str, generado_por=nombre,
                    clima_data=datos["clima"], cultura_data=datos["cultura"],
                    focos_data=datos["focos"], hex_data=datos["hexagono"],
                    data_360=datos["360"], play_data=datos["play"],
                )
                fname = f"Reporte_{unidad_sel.replace(' ','_')}_{mes_str.replace(' ','_')}.pdf"
                st.success(f"✅ Reporte generado — {len(pdf)//1024} KB")
                st.download_button("⬇️ Descargar PDF", data=pdf, file_name=fname,
                                   mime="application/pdf", use_container_width=True, type="primary")
                _preview(datos, mes_str, unidad_sel)
            except Exception as e:
                st.error(f"Error: {e}")
                import traceback; st.code(traceback.format_exc())

    st.divider()
    st.markdown("#### 📁 Usos recomendados")
    st.markdown("- **Reunión mensual** — comparte clima y faros con el equipo\n"
                "- **1-on-1** — usa resultados 360° y hexágono\n"
                "- **Reporte a dirección** — focos y KRs con progreso real\n"
                "- **Archivo histórico** — guarda en Drive por unidad y mes")


def _preview(datos, mes, unidad):
    st.divider()
    st.markdown(f"#### 📊 Resumen: {unidad} — {mes}")
    clima  = datos.get("clima",{})
    cult   = datos.get("cultura",{})
    focos  = datos.get("focos",[])
    play   = datos.get("play",{})
    avg    = round(sum(f.get("progreso",0) for f in focos)/max(len(focos),1)) if focos else 0
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💬 Check-ins",    clima.get("total",0))
    c2.metric("😰 Estrés prom.", f"{clima.get('avg_estres',0)}/5")
    c3.metric("🔦 Faros",        cult.get("total_faros",0))
    c4.metric("📈 Progreso",     f"{avg}%")


def _get_lider_unidad(unidad):
    try:
        with db.get_db() as conn:
            r = conn.execute("SELECT email FROM usuarios WHERE unidad=? AND rol IN ('Líder','Admin','Coordinador') AND estado='Activo' LIMIT 1", (unidad,)).fetchone()
            return r["email"] if r else None
    except: return None
