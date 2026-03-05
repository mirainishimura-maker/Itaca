"""
🎬 Ítaca Play — Capacitaciones Gamificadas con YouTube
Todos los usuarios · Admin gestiona desde aquí y desde Admin Dashboard
"""
import streamlit as st
import database as db
from config import TURQ, GOLD, GREEN, RED, BLACK, GRAY

# ── Categorías y colores ──
CAT_COLORS = {
    "Liderazgo": "#7E57C2",
    "IE":        "#EC407A",
    "Estrategia":"#26C6DA",
    "Comunicación":"#43A047",
    "General":  "#FFB300",
}
DIFICULTAD_BADGE = {
    "Básico":     ("🟢", "#E8F5E9", "#43A047"),
    "Intermedio": ("🟡", "#FFFDE7", "#F9A825"),
    "Avanzado":   ("🔴", "#FFEBEE", "#C62828"),
}


def _yt_embed(yt_id: str) -> str:
    return f"https://www.youtube.com/embed/{yt_id}?rel=0&modestbranding=1"


def _card_css():
    return """
    <style>
    .play-card {
        background: white;
        border-radius: 16px;
        border: 1px solid #E0E0E0;
        padding: 20px;
        margin-bottom: 12px;
        transition: box-shadow .2s;
    }
    .play-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
    .play-badge {
        display: inline-block;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .play-titulo { font-size: 1.05rem; font-weight: 700; margin: 8px 0 4px; }
    .play-desc { color: #666; font-size: 0.88rem; margin-bottom: 10px; }
    .play-pts { color: #FFB300; font-weight: 700; }
    .aprobado-banner {
        background: #E8F5E9; border-radius: 10px; padding: 10px 16px;
        color: #2E7D32; font-weight: 600; text-align: center; margin-bottom: 12px;
    }
    .hint-box {
        background: #E3F2FD; border-radius: 10px; padding: 12px 16px;
        color: #1565C0; font-size: 0.9rem; margin: 10px 0;
    }
    </style>
    """


# ═══════════════════════════════════════════════════
# RENDER PRINCIPAL
# ═══════════════════════════════════════════════════
def render():
    email = st.session_state.get("current_user", "")
    rol = st.session_state.get("user_rol", "Colaborador")
    es_admin = rol == "Admin"

    st.markdown(_card_css(), unsafe_allow_html=True)
    st.markdown("## 🎬 Ítaca Play")
    st.caption("Aprende, demuestra lo que sabes y gana puntos en cada video.")

    if es_admin:
        tabs = st.tabs(["🎓 Aprender", "📊 Panel Admin", "➕ Agregar Curso"])
    else:
        tabs = st.tabs(["🎓 Aprender", "🏅 Mi Progreso"])

    # ── TAB APRENDER ──
    with tabs[0]:
        _tab_aprender(email)

    if es_admin:
        with tabs[1]:
            _tab_admin_stats()
        with tabs[2]:
            _tab_agregar_curso(email)
    else:
        with tabs[1]:
            _tab_mi_progreso(email)


# ═══════════════════════════════════════════════════
# TAB: APRENDER
# ═══════════════════════════════════════════════════
def _tab_aprender(email):
    cursos = db.get_play_cursos(solo_activos=True)
    if not cursos:
        st.info("Aún no hay cursos disponibles. ¡Pronto habrá contenido!")
        return

    progreso = db.get_play_progreso_usuario(email)

    # Filtros
    categorias = ["Todas"] + sorted(set(c["categoria"] for c in cursos))
    col1, col2 = st.columns([2, 1])
    cat_sel = col1.selectbox("Categoría", categorias, key="play_cat")
    estado_sel = col2.selectbox("Estado", ["Todos", "Pendientes", "Completados"], key="play_estado")

    if cat_sel != "Todas":
        cursos = [c for c in cursos if c["categoria"] == cat_sel]
    if estado_sel == "Pendientes":
        cursos = [c for c in cursos if not progreso.get(c["curso_id"], {}).get("aprobado")]
    elif estado_sel == "Completados":
        cursos = [c for c in cursos if progreso.get(c["curso_id"], {}).get("aprobado")]

    # Contador
    completados = sum(1 for c in cursos if progreso.get(c["curso_id"], {}).get("aprobado"))
    st.markdown(f"**{completados}/{len(cursos)}** cursos completados")
    st.progress(completados / max(len(cursos), 1))
    st.divider()

    # Lista de cursos
    if not cursos:
        st.info("No hay cursos con ese filtro.")
        return

    for curso in cursos:
        _render_curso_card(email, curso, progreso)


def _render_curso_card(email, curso, progreso):
    cid = curso["curso_id"]
    aprobado = progreso.get(cid, {}).get("aprobado", False)
    cat_color = CAT_COLORS.get(curso["categoria"], "#757575")
    dif_emoji, dif_bg, dif_color = DIFICULTAD_BADGE.get(curso["dificultad"], ("⚪", "#F5F5F5", "#757575"))

    # Header de la card
    estado_icon = "✅" if aprobado else "🎬"
    with st.expander(
        f"{estado_icon} **{curso['titulo']}** "
        f"| {dif_emoji} {curso['dificultad']} "
        f"| ⭐ {curso['puntos']} pts",
        expanded=False
    ):
        # Badges
        st.markdown(
            f'<span class="play-badge" style="background:{cat_color}22; color:{cat_color};">'
            f'{curso["categoria"]}</span>'
            f'<span class="play-badge" style="background:{dif_bg}; color:{dif_color};">'
            f'{dif_emoji} {curso["dificultad"]}</span>'
            f'<span class="play-badge" style="background:#FFF8E1; color:#F9A825;">'
            f'⭐ {curso["puntos"]} puntos</span>',
            unsafe_allow_html=True
        )
        st.markdown(f'<p class="play-desc">{curso.get("descripcion","")}</p>', unsafe_allow_html=True)

        # Si ya aprobó
        if aprobado:
            st.markdown(
                '<div class="aprobado-banner">✅ ¡Curso completado! Has ganado este badge. '
                f'Obtuviste {progreso[cid]["puntos_ganados"]} puntos.</div>',
                unsafe_allow_html=True
            )
            return

        # Video embebido
        yt_id = curso.get("youtube_id") or db._extract_youtube_id(curso["youtube_url"])
        if yt_id:
            st.markdown("#### 📺 Video del curso")
            st.markdown(
                f'<iframe width="100%" height="340" src="{_yt_embed(yt_id)}" '
                f'frameborder="0" allowfullscreen style="border-radius:12px;"></iframe>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"[🔗 Ver video en YouTube]({curso['youtube_url']})")

        # Instrucciones
        st.markdown(
            '<div class="hint-box">📌 <b>Instrucciones:</b> Ve el video completo, '
            'luego ingresa la <b>palabra clave</b> que escuches y responde la pregunta.</div>',
            unsafe_allow_html=True
        )

        # Formulario de evaluación
        with st.form(key=f"play_form_{cid}"):
            st.markdown("#### ✍️ Demuestra lo que aprendiste")
            palabra = st.text_input(
                "🔑 Palabra clave del video",
                placeholder="Escribe la palabra que mencionaron...",
                key=f"pal_{cid}"
            )
            st.markdown(f"**Pregunta:** {curso['pregunta']}")
            opciones = {
                "A": curso["opcion_a"],
                "B": curso["opcion_b"],
                "C": curso["opcion_c"],
                "D": curso["opcion_d"],
            }
            respuesta = st.radio(
                "Selecciona tu respuesta:",
                list(opciones.keys()),
                format_func=lambda k: f"**{k})** {opciones[k]}",
                key=f"resp_{cid}",
                horizontal=False
            )
            submit = st.form_submit_button("🚀 Enviar respuestas", type="primary", use_container_width=True)

            if submit:
                if not palabra.strip():
                    st.error("⚠️ Ingresa la palabra clave del video.")
                else:
                    resultado = db.submit_play_intento(email, cid, palabra, respuesta)
                    _mostrar_resultado(resultado, curso)


def _mostrar_resultado(resultado, curso):
    if not resultado["ok"]:
        st.warning(resultado["msg"])
        return

    if resultado["aprobado"]:
        st.balloons()
        st.success(
            f"🎉 ¡APROBADO! Ganaste **{resultado['puntos']} puntos** "
            f"y el badge {curso.get('badge_icono','🎬')} **{curso.get('badge_nombre','')}**"
        )
        st.rerun()
    else:
        msgs = []
        if not resultado["pal_ok"]:
            msgs.append("❌ Palabra clave incorrecta")
        if not resultado["resp_ok"]:
            msgs.append("❌ Respuesta incorrecta")
        st.error(" · ".join(msgs) + f" — Intento #{resultado['intento_num']}. Revisa el video e inténtalo de nuevo.")


# ═══════════════════════════════════════════════════
# TAB: MI PROGRESO
# ═══════════════════════════════════════════════════
def _tab_mi_progreso(email):
    cursos = db.get_play_cursos(solo_activos=True)
    progreso = db.get_play_progreso_usuario(email)

    completados = [c for c in cursos if progreso.get(c["curso_id"], {}).get("aprobado")]
    pendientes = [c for c in cursos if not progreso.get(c["curso_id"], {}).get("aprobado")]
    total_pts = sum(progreso.get(c["curso_id"], {}).get("puntos_ganados", 0) for c in completados)

    col1, col2, col3 = st.columns(3)
    col1.metric("🎬 Completados", len(completados))
    col2.metric("⏳ Pendientes", len(pendientes))
    col3.metric("⭐ Puntos Play", total_pts)

    st.progress(len(completados) / max(len(cursos), 1),
                text=f"Progreso: {len(completados)}/{len(cursos)} cursos")

    if completados:
        st.divider()
        st.markdown("### 🏅 Cursos Completados")
        for c in completados:
            pts = progreso[c["curso_id"]]["puntos_ganados"]
            st.markdown(
                f"✅ **{c['titulo']}** "
                f"| {c.get('badge_icono','🎬')} {c.get('badge_nombre','')} "
                f"| ⭐ +{pts} pts"
            )

    if pendientes:
        st.divider()
        st.markdown("### 🎯 Próximos por completar")
        for c in pendientes[:3]:
            st.markdown(f"▶️ **{c['titulo']}** | ⭐ {c['puntos']} pts disponibles")


# ═══════════════════════════════════════════════════
# TAB: PANEL ADMIN — ESTADÍSTICAS
# ═══════════════════════════════════════════════════
def _tab_admin_stats():
    stats = db.get_play_stats_admin()

    c1, c2, c3 = st.columns(3)
    c1.metric("🎬 Cursos activos", stats["total_cursos"])
    c2.metric("✅ Aprobaciones", stats["total_aprobados"])
    c3.metric("📊 Intentos totales", stats["total_intentos"])

    # Cursos más populares
    if stats["top_cursos"]:
        st.divider()
        st.markdown("#### 🔥 Top Cursos")
        for t in stats["top_cursos"]:
            tasa = round((t["aprobados"] / max(t["intentos"], 1)) * 100)
            st.markdown(
                f"**{t['titulo']}** — {t['intentos']} intentos · "
                f"{t['aprobados']} aprobados · Tasa: {tasa}%"
            )

    # Ranking de colaboradores
    if stats["ranking"]:
        st.divider()
        st.markdown("#### 🏅 Ranking Ítaca Play")
        for i, r in enumerate(stats["ranking"], 1):
            medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"#{i}"
            st.markdown(
                f"{medal} **{r['nombre']}** ({r['unidad']}) — "
                f"{r['cursos_completados']} cursos · ⭐ {r['puntos_play']} pts"
            )

    # Gestión de cursos existentes
    st.divider()
    st.markdown("#### 🗂️ Gestión de Cursos")
    cursos = db.get_play_cursos(solo_activos=False)
    if cursos:
        for c in cursos:
            activo = bool(c["activo"])
            col1, col2, col3 = st.columns([4, 1, 1])
            col1.markdown(f"{'✅' if activo else '⏸️'} **{c['titulo']}** "
                          f"| {c['categoria']} | {c['puntos']} pts")
            if col2.button("🔄", key=f"tog_{c['curso_id']}", help="Activar/Pausar"):
                db.toggle_play_curso(c["curso_id"], not activo)
                st.rerun()
            if col3.button("🗑️", key=f"del_{c['curso_id']}", help="Eliminar"):
                db.delete_play_curso(c["curso_id"])
                st.rerun()


# ═══════════════════════════════════════════════════
# TAB: AGREGAR CURSO (Admin)
# ═══════════════════════════════════════════════════
def _tab_agregar_curso(email_admin):
    st.markdown("#### ➕ Nuevo Curso en Ítaca Play")
    st.caption("Completa todos los campos. La palabra clave y la respuesta correcta son sensibles a mayúsculas en la evaluación — se normalizan a minúsculas.")

    with st.form("form_nuevo_curso", clear_on_submit=True):
        col1, col2 = st.columns(2)
        titulo = col1.text_input("Título del curso *")
        categoria = col2.selectbox("Categoría", list(CAT_COLORS.keys()))

        descripcion = st.text_area("Descripción breve", max_chars=300)

        col3, col4 = st.columns(2)
        youtube_url = col3.text_input("URL de YouTube *", placeholder="https://www.youtube.com/watch?v=...")
        dificultad = col4.selectbox("Dificultad", ["Básico", "Intermedio", "Avanzado"])

        col5, col6, col7 = st.columns(3)
        puntos = col5.number_input("Puntos al aprobar", 10, 500, 100, step=10)
        badge_nombre = col6.text_input("Nombre del Badge", placeholder="🎯 Estratega")
        badge_icono = col7.text_input("Ícono del Badge", placeholder="🎯", max_chars=4)

        st.divider()
        st.markdown("**🔑 Anti-trampa**")
        palabra_clave = st.text_input(
            "Palabra clave (debe aparecer en el video)",
            placeholder="Ej: resiliencia"
        )

        st.divider()
        st.markdown("**❓ Pregunta de evaluación**")
        pregunta = st.text_input("Pregunta *")
        c1, c2 = st.columns(2)
        opcion_a = c1.text_input("Opción A")
        opcion_b = c2.text_input("Opción B")
        c3, c4 = st.columns(2)
        opcion_c = c3.text_input("Opción C")
        opcion_d = c4.text_input("Opción D")
        respuesta_correcta = st.selectbox(
            "Respuesta correcta *", ["A", "B", "C", "D"]
        )
        orden = st.number_input("Orden de aparición", 0, 999, 0)

        submit = st.form_submit_button("🚀 Publicar Curso", type="primary", use_container_width=True)

        if submit:
            errores = []
            if not titulo.strip():
                errores.append("Falta el título.")
            if not youtube_url.strip():
                errores.append("Falta la URL de YouTube.")
            if not palabra_clave.strip():
                errores.append("Falta la palabra clave.")
            if not pregunta.strip():
                errores.append("Falta la pregunta.")
            if not all([opcion_a, opcion_b, opcion_c, opcion_d]):
                errores.append("Completa las 4 opciones.")

            if errores:
                for e in errores:
                    st.error(e)
            else:
                cid = db.add_play_curso(
                    titulo=titulo, descripcion=descripcion,
                    youtube_url=youtube_url, categoria=categoria,
                    dificultad=dificultad, puntos=int(puntos),
                    badge_nombre=badge_nombre, badge_icono=badge_icono or "🎬",
                    palabra_clave=palabra_clave, pregunta=pregunta,
                    opcion_a=opcion_a, opcion_b=opcion_b,
                    opcion_c=opcion_c, opcion_d=opcion_d,
                    respuesta_correcta=respuesta_correcta,
                    creado_por=email_admin, orden=int(orden)
                )
                st.success(f"✅ Curso publicado con ID: `{cid}` — Ya está disponible para todos los usuarios.")
                st.balloons()
