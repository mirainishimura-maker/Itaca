"""
🔄 Evaluación 360° — Ítaca OS 2.0
Pilares I+M + Hexágono + Goleman IE
Anónima para el evaluado · Visible para Admin/Líder
Activada por periodos trimestrales
"""
import streamlit as st
import database as db
from config import (TURQ, GOLD, GREEN, RED, GRAY,
                    PILARES, DIMENSIONES_HEXAGONO, COMPETENCIAS_IE, ESCALA)

# ── Paleta visual ──
COLOR_PILARES = "#26C6DA"
COLOR_HEX     = "#7E57C2"
COLOR_IE      = "#EC407A"
COLOR_TOTAL   = "#FFB300"

ROLES_LIDERAZGO = ["Admin", "Líder", "Coordinador"]


# ═══════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════
_CSS = """
<style>
.dim-row { display:flex; align-items:center; gap:10px; margin:6px 0; }
.dim-label { min-width:200px; font-size:.9rem; font-weight:500; }
.score-pill {
    display:inline-block; border-radius:20px; padding:3px 14px;
    font-weight:700; font-size:.85rem;
}
.result-card {
    background:white; border-radius:14px; border:1px solid #E0E0E0;
    padding:18px; margin-bottom:12px;
}
.brecha-pos { color:#43A047; font-weight:700; }
.brecha-neg { color:#E53935; font-weight:700; }
.anon-badge {
    background:#E3F2FD; color:#1565C0; border-radius:8px;
    padding:6px 14px; font-size:.82rem; display:inline-block; margin-bottom:10px;
}
</style>
"""


# ═══════════════════════════════════════════════════════
# RENDER PRINCIPAL
# ═══════════════════════════════════════════════════════
def render():
    email = st.session_state.get("current_user", "")
    rol   = st.session_state.get("user_rol", "Colaborador")
    nombre = st.session_state.get("user_name", "")

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("## 🔄 Evaluación 360°")
    st.caption("Evalúa a tu equipo, conoce tu resultado y crece con feedback real.")

    # ── Periodo activo ──
    periodo = db.get_periodo_activo()

    if rol == "Admin":
        tabs = st.tabs(["📝 Evaluar", "📊 Mis Resultados", "👥 Vista Equipo", "⚙️ Admin 360"])
    elif rol in ["Líder", "Coordinador"]:
        tabs = st.tabs(["📝 Evaluar", "📊 Mis Resultados", "👥 Vista Equipo"])
    else:
        tabs = st.tabs(["📝 Evaluar", "📊 Mis Resultados"])

    with tabs[0]:
        _tab_evaluar(email, rol, nombre, periodo)

    with tabs[1]:
        _tab_mis_resultados(email, rol, periodo)

    if rol in ROLES_LIDERAZGO:
        with tabs[2]:
            _tab_vista_equipo(email, rol, periodo)

    if rol == "Admin":
        with tabs[3]:
            _tab_admin(email, periodo)


# ═══════════════════════════════════════════════════════
# TAB 1: EVALUAR
# ═══════════════════════════════════════════════════════
def _tab_evaluar(email, rol, nombre, periodo):
    if not periodo:
        st.info("⏳ No hay un periodo de evaluación 360° activo en este momento.")
        st.caption("El administrador abrirá el próximo proceso pronto.")
        return

    st.success(f"🟢 Periodo activo: **{periodo['nombre']}** "
               f"({periodo.get('fecha_inicio','')} → {periodo.get('fecha_fin','')})")
    st.markdown(
        '<span class="anon-badge">🔒 Tus evaluaciones son anónimas para el evaluado</span>',
        unsafe_allow_html=True
    )

    pid = periodo["periodo_id"]

    # ── Primero: autoevaluación ──
    ya_auto = db.has_evaluated_360_v2(email, email, pid)
    if not ya_auto:
        st.markdown("### 1️⃣ Empieza por ti: Autoevaluación")
        st.caption("Evalúate antes de evaluar a tu equipo.")
        _formulario_360(email, email, pid, nombre, rol, es_auto=True)
        return  # obliga a completar auto primero

    st.success("✅ Autoevaluación completada.")
    st.divider()

    # ── Pendientes ──
    pendientes = db.get_pending_evaluaciones(email, pid)

    if not pendientes:
        st.balloons()
        st.success("🎉 ¡Has evaluado a todos los miembros de tu unidad! Proceso completado.")
        return

    st.markdown(f"### 2️⃣ Evalúa a tu equipo ({len(pendientes)} pendiente{'s' if len(pendientes)>1 else ''})")

    # Seleccionar a quién evaluar
    nombres_pend = [f"{p['nombre']} — {p.get('rol','')}" for p in pendientes]
    idx = st.selectbox("¿A quién evalúas ahora?", range(len(nombres_pend)),
                       format_func=lambda i: nombres_pend[i])
    evaluado = pendientes[idx]

    st.markdown(f"#### Evaluando a: **{evaluado['nombre']}**")
    _formulario_360(email, evaluado["email"], pid,
                    evaluado["nombre"], rol, es_auto=False,
                    evaluado_rol=evaluado.get("rol","Colaborador"))


def _formulario_360(email_evaluador, email_evaluado, periodo_id,
                    nombre_evaluado, rol_evaluador, es_auto,
                    evaluado_rol="Colaborador"):
    """Formulario de evaluación reutilizable (auto + pares)."""

    evalua_hex = evaluado_rol in ROLES_LIDERAZGO
    prefix = "auto" if es_auto else email_evaluado[:8]

    with st.form(f"form360_{prefix}_{periodo_id}"):

        # ── BLOQUE 1: Pilares I+M ──
        st.markdown(f"#### 🏛️ Pilares I+M")
        st.caption("Escala: 1 = Crítico · 3 = En desarrollo · 5 = Ejemplar")

        p_itac = st.slider(
            f"🐿️ **ITACTIVIDAD** — Proactividad, trae soluciones",
            1, 5, 3, key=f"p1_{prefix}")
        p_mas1 = st.slider(
            f"🦫 **+1 Sí Importa** — Da la milla extra, se compromete",
            1, 5, 3, key=f"p2_{prefix}")
        p_conf = st.slider(
            f"🪿 **Muro de Confianza** — Transparente, directo, cuida al equipo",
            1, 5, 3, key=f"p3_{prefix}")

        st.divider()

        # ── BLOQUE 2: Hexágono (solo para roles líderes) ──
        hex_vals = [0]*6
        if evalua_hex:
            st.markdown(f"#### 🧭 Hexágono de Liderazgo")
            st.caption("Solo aplica a líderes, coordinadores y admin")
            dims = ["Visión Corporativa","Planificación","Encaje de Talento",
                    "Entrenamiento","Evaluación y Mejora","Reconocimiento"]
            emojis = ["🎯","🗓️","🧩","🎓","🔄","🏆"]
            for i,(d,e) in enumerate(zip(dims, emojis)):
                hex_vals[i] = st.slider(
                    f"{e} **{d}**", 1, 5, 3, key=f"h{i}_{prefix}")
            st.divider()
        else:
            st.info("🧭 El Hexágono de Liderazgo no aplica para este colaborador.")
            st.divider()

        # ── BLOQUE 3: Goleman IE ──
        st.markdown("#### 🧠 Inteligencia Emocional (Goleman)")
        ie_auto_v  = st.slider("📝 **Autoconocimiento** — Se conoce, identifica sus emociones",
                                1, 5, 3, key=f"ie1_{prefix}")
        ie_autor_v = st.slider("🎯 **Autorregulación** — Gestiona bien lo que siente",
                                1, 5, 3, key=f"ie2_{prefix}")
        ie_motiv_v = st.slider("🔥 **Motivación** — Empuje interno, constancia",
                                1, 5, 3, key=f"ie3_{prefix}")
        ie_empa_v  = st.slider("❤️ **Empatía** — Entiende y considera a los demás",
                                1, 5, 3, key=f"ie4_{prefix}")
        ie_soc_v   = st.slider("🤝 **Habilidades Sociales** — Se relaciona efectivamente",
                                1, 5, 3, key=f"ie5_{prefix}")

        st.divider()

        # ── BLOQUE 4: Cualitativos ──
        st.markdown("#### 💬 Feedback cualitativo")
        fortaleza = st.text_input(
            "⭐ Principal fortaleza de esta persona",
            placeholder="Ej: Su capacidad de escuchar y proponer soluciones...",
            key=f"fort_{prefix}")
        area_mejora = st.text_input(
            "📈 Principal área de mejora",
            placeholder="Ej: Podría mejorar su gestión del tiempo...",
            key=f"area_{prefix}")
        comentario = st.text_area(
            "📝 Comentario libre (opcional)",
            max_chars=400, key=f"coment_{prefix}")

        label = "✍️ Guardar Autoevaluación" if es_auto else f"🚀 Enviar evaluación de {nombre_evaluado}"
        submit = st.form_submit_button(label, type="primary", use_container_width=True)

        if submit:
            eid = db.save_eval_360_v2(
                periodo_id=periodo_id,
                email_evaluado=email_evaluado,
                email_evaluador=email_evaluador,
                unidad=st.session_state.get("user_data", {}).get("unidad", "") if isinstance(st.session_state.get("user_data"), dict) else "",
                es_auto=es_auto,
                pilar_itactividad=p_itac, pilar_mas1=p_mas1, pilar_confianza=p_conf,
                hex_vision=hex_vals[0], hex_planificacion=hex_vals[1],
                hex_encaje=hex_vals[2], hex_entrenamiento=hex_vals[3],
                hex_evaluacion=hex_vals[4], hex_reconocimiento=hex_vals[5],
                ie_auto=ie_auto_v, ie_autor=ie_autor_v, ie_motiv=ie_motiv_v,
                ie_empatia=ie_empa_v, ie_social=ie_soc_v,
                fortaleza=fortaleza, area_mejora=area_mejora, comentario=comentario,
                evalua_hexagono=evalua_hex,
            )
            if es_auto:
                st.success("✅ Autoevaluación guardada. Ahora evalúa a tu equipo.")
            else:
                st.success(f"✅ Evaluación de **{nombre_evaluado}** enviada. ¡Gracias!")
            st.balloons()
            st.rerun()


# ═══════════════════════════════════════════════════════
# TAB 2: MIS RESULTADOS
# ═══════════════════════════════════════════════════════
def _tab_mis_resultados(email, rol, periodo):
    st.markdown("### 📊 Mis Resultados 360°")

    periodos = db.get_all_periodos_360()
    if not periodos:
        st.info("Aún no hay periodos de evaluación registrados.")
        return

    # Selector de periodo
    opciones = {p["periodo_id"]: p["nombre"] for p in periodos}
    pid_sel = st.selectbox("Periodo", list(opciones.keys()),
                           format_func=lambda k: opciones[k])

    data = db.get_resultados_360_v2(email, pid_sel)
    avgs = data["avgs"]
    auto = data["auto"]
    comentarios = data["comentarios"]

    total_ev = avgs.get("total_evaluadores", 0) if avgs else 0
    if total_ev == 0:
        st.info("Aún no tienes evaluaciones de pares en este periodo.")
        if auto:
            st.markdown("#### ✍️ Tu autoevaluación")
            _mostrar_resumen_individual(auto)
        return

    st.markdown(
        f'<span class="anon-badge">🔒 Resultados agregados de {total_ev} evaluador{"es" if total_ev>1 else ""} — anónimos</span>',
        unsafe_allow_html=True
    )

    # ── Promedios generales ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏛️ Pilares I+M",  f"{round(avgs.get('prom_pilares',0),1)}/5")
    col2.metric("🧭 Hexágono",     f"{round(avgs.get('prom_hexagono',0),1)}/5")
    col3.metric("🧠 IE Goleman",   f"{round(avgs.get('prom_ie',0),1)}/5")
    col4.metric("⭐ Total",         f"{round(avgs.get('prom_total',0),1)}/5")

    st.divider()

    # ── Detalle por bloque ──
    col_pares, col_auto = st.columns(2)

    with col_pares:
        st.markdown("#### 👥 Evaluación de pares")
        _bloque_pilares(avgs, "pares")
        _bloque_ie(avgs, "pares")
        if avgs.get("prom_hexagono", 0) > 0:
            _bloque_hexagono(avgs, "pares")

    with col_auto:
        if auto:
            st.markdown("#### ✍️ Tu autoevaluación")
            _bloque_pilares(auto, "auto")
            _bloque_ie(auto, "auto")
            if auto.get("prom_hexagono", 0) > 0:
                _bloque_hexagono(auto, "auto")
        else:
            st.info("Aún no completaste tu autoevaluación.")

    # ── Brecha pares vs auto ──
    if auto and total_ev > 0:
        st.divider()
        st.markdown("#### 🔍 Brecha: Pares vs Autoevaluación")
        st.caption("Positivo (+) = te subestimas · Negativo (−) = te sobreestimas")
        _mostrar_brechas(avgs, auto)

    # ── Comentarios cualitativos (anónimos) ──
    if comentarios:
        st.divider()
        st.markdown("#### 💬 Feedback de tu equipo")
        for c in comentarios:
            if c.get("fortaleza_principal"):
                st.markdown(f"⭐ _{c['fortaleza_principal']}_")
            if c.get("area_mejora"):
                st.markdown(f"📈 _{c['area_mejora']}_")
            if c.get("comentario"):
                st.markdown(f"💬 _{c['comentario']}_")
            st.divider()


def _bloque_pilares(data, key):
    st.markdown("**🏛️ Pilares I+M**")
    dims = [
        ("🐿️ ITACTIVIDAD",     "pilar_itactividad"),
        ("🦫 +1 Sí Importa",   "pilar_mas1"),
        ("🪿 Muro Confianza",  "pilar_confianza"),
    ]
    for label, campo in dims:
        val = round(data.get(campo, 0) or 0, 1)
        _mini_barra(label, val, COLOR_PILARES, key)


def _bloque_ie(data, key):
    st.markdown("**🧠 Inteligencia Emocional**")
    dims = [
        ("📝 Autoconocimiento",    "ie_autoconocimiento"),
        ("🎯 Autorregulación",     "ie_autorregulacion"),
        ("🔥 Motivación",          "ie_motivacion"),
        ("❤️ Empatía",             "ie_empatia"),
        ("🤝 Habilidades Sociales","ie_habilidades_sociales"),
    ]
    for label, campo in dims:
        val = round(data.get(campo, 0) or 0, 1)
        _mini_barra(label, val, COLOR_IE, key)


def _bloque_hexagono(data, key):
    st.markdown("**🧭 Hexágono Liderazgo**")
    dims = [
        ("🎯 Visión Corp.",      "hex_vision"),
        ("🗓️ Planificación",    "hex_planificacion"),
        ("🧩 Encaje Talento",    "hex_encaje"),
        ("🎓 Entrenamiento",     "hex_entrenamiento"),
        ("🔄 Eval. y Mejora",    "hex_evaluacion"),
        ("🏆 Reconocimiento",    "hex_reconocimiento"),
    ]
    for label, campo in dims:
        val = round(data.get(campo, 0) or 0, 1)
        _mini_barra(label, val, COLOR_HEX, key)


def _mini_barra(label, val, color, key):
    col1, col2 = st.columns([3, 1])
    col1.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
    col1.progress(val / 5)
    escala = ESCALA.get(round(val), "")
    col2.markdown(f"**{val}** <small style='color:{color}'>{escala}</small>",
                  unsafe_allow_html=True)


def _mostrar_brechas(avgs, auto):
    pares = [
        ("🏛️ Pilares",  avgs.get("prom_pilares",0),  auto.get("prom_pilares",0)),
        ("🧠 IE",       avgs.get("prom_ie",0),        auto.get("prom_ie",0)),
        ("⭐ Total",    avgs.get("prom_total",0),      auto.get("prom_total",0)),
    ]
    for label, v_pares, v_auto in pares:
        brecha = round((v_pares or 0) - (v_auto or 0), 2)
        signo = "+" if brecha > 0 else ""
        clase = "brecha-pos" if brecha >= 0 else "brecha-neg"
        st.markdown(
            f"**{label}** — Pares: {round(v_pares,1)} · Auto: {round(v_auto,1)} · "
            f'Brecha: <span class="{clase}">{signo}{brecha}</span>',
            unsafe_allow_html=True
        )


def _mostrar_resumen_individual(data):
    col1, col2, col3 = st.columns(3)
    col1.metric("🏛️ Pilares", f"{round(data.get('prom_pilares',0),1)}/5")
    col2.metric("🧠 IE",      f"{round(data.get('prom_ie',0),1)}/5")
    col3.metric("⭐ Total",   f"{round(data.get('prom_total',0),1)}/5")


# ═══════════════════════════════════════════════════════
# TAB 3: VISTA EQUIPO (Líder / Coordinador / Admin)
# ═══════════════════════════════════════════════════════
def _tab_vista_equipo(email, rol, periodo):
    st.markdown("### 👥 Resultados de tu Equipo")

    periodos = db.get_all_periodos_360()
    if not periodos:
        st.info("Sin periodos de evaluación registrados.")
        return

    opciones = {p["periodo_id"]: p["nombre"] for p in periodos}
    pid_sel = st.selectbox("Periodo", list(opciones.keys()),
                           format_func=lambda k: opciones[k], key="eq_periodo")

    equipo = db.get_equipo_resultados_lider(email, pid_sel)
    if not equipo:
        st.info("Tu equipo aún no tiene evaluaciones en este periodo.")
        return

    # Ranking visual
    equipo_ord = sorted(equipo, key=lambda x: x["prom_total"], reverse=True)
    for i, m in enumerate(equipo_ord, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"#{i}"
        with st.expander(
            f"{medal} **{m['nombre']}** — ⭐ {m['prom_total']}/5 "
            f"({m['total_evaluadores']} evaluadores)",
            expanded=(i == 1)
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("🏛️ Pilares", f"{m['prom_pilares']}/5")
            col2.metric("🧠 IE",      f"{m['prom_ie']}/5")
            col3.metric("⭐ Total",   f"{m['prom_total']}/5")

            # Detalle con email_evaluador visible (Admin/Líder)
            if rol in ["Admin", "Líder"]:
                detalles = db.get_resultados_360_v2_admin(m["email"], pid_sel)
                if detalles:
                    st.markdown("**Evaluaciones individuales:**")
                    for d in detalles:
                        tipo = "✍️ Auto" if d["es_autoevaluacion"] else f"👤 {d.get('nombre_evaluador','—')}"
                        st.markdown(
                            f"{tipo} — Pilares: {round(d.get('prom_pilares',0),1)} · "
                            f"IE: {round(d.get('prom_ie',0),1)} · "
                            f"Total: {round(d.get('prom_total',0),1)}"
                        )


# ═══════════════════════════════════════════════════════
# TAB 4: ADMIN — GESTIÓN DE PERIODOS
# ═══════════════════════════════════════════════════════
def _tab_admin(email, periodo_activo):
    st.markdown("### ⚙️ Gestión de Periodos 360°")

    # Stats del periodo activo
    if periodo_activo:
        pid = periodo_activo["periodo_id"]
        stats = db.get_stats_360_admin(pid)
        st.markdown(f"**Periodo activo:** {periodo_activo['nombre']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("👥 Evaluadores",  stats["total_evaluadores"])
        c2.metric("🎯 Evaluados",    stats["total_evaluados"])
        c3.metric("📝 Registros",    stats["total_registros"])

        if stats["top_colaboradores"]:
            st.markdown("#### 🏅 Top colaboradores")
            for t in stats["top_colaboradores"]:
                st.markdown(
                    f"⭐ **{t['nombre']}** ({t['unidad']}) — "
                    f"Promedio: {round(t['prom'],2)}/5"
                )

        st.divider()
        if st.button("🔒 Cerrar este periodo", type="secondary"):
            db.cerrar_periodo_360(pid)
            st.success("Periodo cerrado.")
            st.rerun()
        st.divider()
    else:
        st.info("No hay periodo activo actualmente.")
        st.divider()

    # Crear nuevo periodo
    st.markdown("#### ➕ Abrir nuevo periodo")
    with st.form("form_periodo"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre del periodo", placeholder="Ej: 360° Q1 2026")
        trimestre = col2.selectbox("Trimestre", ["Q1","Q2","Q3","Q4","Anual"])
        col3, col4 = st.columns(2)
        fecha_ini = col3.date_input("Fecha inicio")
        fecha_fin = col4.date_input("Fecha fin")
        if st.form_submit_button("🚀 Abrir periodo", type="primary", use_container_width=True):
            if nombre:
                db.crear_periodo_360(
                    nombre=nombre, trimestre=trimestre,
                    fecha_inicio=str(fecha_ini), fecha_fin=str(fecha_fin),
                    creado_por=email
                )
                st.success(f"✅ Periodo '{nombre}' abierto. Todos los usuarios pueden empezar a evaluar.")
                st.rerun()
            else:
                st.error("Ingresa un nombre para el periodo.")

    # Historial
    st.divider()
    st.markdown("#### 📋 Historial de periodos")
    todos = db.get_all_periodos_360()
    for p in todos:
        estado = "🟢 Activo" if p["activo"] else "⚫ Cerrado"
        st.markdown(
            f"{estado} **{p['nombre']}** ({p['trimestre']}) — "
            f"{p.get('fecha_inicio','')} → {p.get('fecha_fin','')}"
        )
