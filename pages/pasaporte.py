"""
⚓ MÓDULO 0: PASAPORTE ÍTACA
Test DISC obligatorio de Onboarding.
Si el usuario no tiene arquetipo, no puede acceder al sistema.
"""
import streamlit as st
import database as db
from config import DISC_TYPES, TURQ, TURQ_DARK, TURQ_LIGHT, GOLD, BLACK

# ═══════════════════════════════════════════
# TEST DISC — 20 PREGUNTAS LABORALES
# ═══════════════════════════════════════════
TEST_DISC = [
    {
        "q": "1. Cuando te comunicas con tus compañeros de equipo o clientes, utilizas palabras...",
        "opts": {
            "a": ("Directas, orientadas a la acción y a veces exigentes.", "Rojo"),
            "b": ("De cortesía, amables, buscando consenso y tranquilidad.", "Verde"),
            "c": ("Precisas, técnicas, detalladas y bien estructuradas.", "Azul"),
            "d": ("Entusiastas, informales, motivadoras y expresivas.", "Amarillo"),
        },
    },
    {
        "q": "2. En tu entorno laboral, te identificas más como alguien...",
        "opts": {
            "a": ("Orientado a resultados e independiente.", "Rojo"),
            "b": ("Estructurado y disciplinado con los procesos.", "Azul"),
            "c": ("Conciliador y buen jugador de equipo.", "Verde"),
            "d": ("Carismático y dinamizador del grupo.", "Amarillo"),
        },
    },
    {
        "q": "3. En los recesos o antes de iniciar una reunión de trabajo, sueles hablar de:",
        "opts": {
            "a": ("Cómo está el equipo, anécdotas o temas familiares.", "Verde"),
            "b": ("Datos, métricas, aspectos técnicos o detalles del proyecto.", "Azul"),
            "c": ("Ideas nuevas, actividades divertidas o anécdotas graciosas.", "Amarillo"),
            "d": ("Metas a alcanzar, toma de decisiones o próximos desafíos.", "Rojo"),
        },
    },
    {
        "q": "4. Al interactuar con un cliente o colega por primera vez, tu estilo es...",
        "opts": {
            "a": ("Concreto, profesional y enfocado en la información exacta.", "Azul"),
            "b": ("Extrovertido, amigable y buscando romper el hielo.", "Amarillo"),
            "c": ("Directo, yendo al grano y tomando el control de la conversación.", "Rojo"),
            "d": ("Cálido, atento y cuidadoso de no incomodar al otro.", "Verde"),
        },
    },
    {
        "q": "5. Durante una presentación o debate en la oficina, te caracterizas por...",
        "opts": {
            "a": ("Mucho movimiento, gesticular con las manos y ser muy expresivo.", "Amarillo"),
            "b": ("Postura firme, movimientos rápidos y proyectar seguridad.", "Rojo"),
            "c": ("Postura relajada, movimientos pausados y actitud receptiva.", "Verde"),
            "d": ("Movimientos controlados, postura formal y enfocada en los datos.", "Azul"),
        },
    },
    {
        "q": "6. Si tus compañeros de trabajo tuvieran que describirte, dirían que eres...",
        "opts": {
            "a": ("El perfeccionista que asegura que todo esté sin errores.", "Azul"),
            "b": ("El comprensivo que siempre apoya a quien tiene un problema.", "Verde"),
            "c": ("El optimista que anima las reuniones y levanta la moral.", "Amarillo"),
            "d": ("El audaz que toma riesgos y empuja para que las cosas pasen.", "Rojo"),
        },
    },
    {
        "q": "7. Cuando discutes un proyecto, tu tono de voz suele ser:",
        "opts": {
            "a": ("Suave, calmado y constante para no generar tensión.", "Verde"),
            "b": ("Lineal, formal y enfocado en pronunciar claramente los hechos.", "Azul"),
            "c": ("Alto, animado y con mucha variación según tu entusiasmo.", "Amarillo"),
            "d": ("Fuerte, intenso y muy seguro (algunos dirían que autoritario).", "Rojo"),
        },
    },
    {
        "q": "8. Tu ritmo al explicar una tarea a otro compañero es...",
        "opts": {
            "a": ("Pausado, asegurándote de que el otro se sienta cómodo.", "Verde"),
            "b": ("Rápido y saltando de una idea a otra con energía.", "Amarillo"),
            "c": ("Rápido, yendo directo al punto sin rodeos.", "Rojo"),
            "d": ("Moderado y metódico, paso a paso para no omitir detalles.", "Azul"),
        },
    },
    {
        "q": "9. Mientras escuchas instrucciones de un superior o un cliente, tu expresión es...",
        "opts": {
            "a": ("Sonriente, asintiendo mucho y manteniendo contacto visual activo.", "Amarillo"),
            "b": ("Seria, analizando la información rápidamente.", "Rojo"),
            "c": ("Relajada y empática, mostrando que estás prestando atención al factor humano.", "Verde"),
            "d": ("Concentrada, imperturbable y analítica.", "Azul"),
        },
    },
    {
        "q": "10. En un escenario de negociación o convencimiento en el trabajo, tu mayor fortaleza es:",
        "opts": {
            "a": ("Tener toda la información, datos y estrategia preparada de antemano.", "Azul"),
            "b": ("Generar confianza a largo plazo y entender la necesidad real del otro.", "Verde"),
            "c": ("El empuje para cerrar el trato rápido y tomar acción inmediata.", "Rojo"),
            "d": ("Tu capacidad de persuasión, carisma y actitud positiva ante objeciones.", "Amarillo"),
        },
    },
    {
        "q": "11. Al enfrentarte a tus tareas diarias, tiendes a:",
        "opts": {
            "a": ("Trabajar a un ritmo constante, prefiriendo hacer una cosa a la vez.", "Verde"),
            "b": ("Ser muy metódico, revisar listas y asegurar la calidad ante todo.", "Azul"),
            "c": ("Empezar varias cosas con entusiasmo, aunque a veces te cueste el orden.", "Amarillo"),
            "d": ("Querer hacer todo rápido, priorizando la velocidad y el resultado final.", "Rojo"),
        },
    },
    {
        "q": "12. ¿Qué actitud asumes cuando un compañero de tu equipo comete un error?",
        "opts": {
            "a": ("Te frustras por la falta de precisión e intentas corregir el proceso.", "Azul"),
            "b": ("Le restas importancia al detalle y valoras que al menos lo intentó.", "Amarillo"),
            "c": ("Eres directo, señalas el error rápido porque hay que avanzar.", "Rojo"),
            "d": ("Le ayudas a corregirlo en privado, cuidando de no herir sus sentimientos.", "Verde"),
        },
    },
    {
        "q": "13. Cuando participas en un proyecto grupal, lo que más te motiva es...",
        "opts": {
            "a": ("Que tu contribución sea notada y el equipo tenga un buen ambiente.", "Amarillo"),
            "b": ("Tomar el liderazgo, influir en la dirección y lograr la meta rápido.", "Rojo"),
            "c": ("Que todos colaboren en armonía y haya sinceridad en el equipo.", "Verde"),
            "d": ("Aportar conocimiento técnico y asegurar que se tomen decisiones lógicas.", "Azul"),
        },
    },
    {
        "q": "14. Frente a un día con mucha presión laboral, tu estado de ánimo se vuelve...",
        "opts": {
            "a": ("Tenso, impaciente y exigente con los demás para cumplir.", "Rojo"),
            "b": ("Tratas de mantener la calma y seguir apoyando al equipo.", "Verde"),
            "c": ("Más reservado, te aíslas para concentrarte y evitar equivocarte.", "Azul"),
            "d": ("Ansioso o disperso, pero buscas hablarlo para liberar la tensión.", "Amarillo"),
        },
    },
    {
        "q": "15. En tu escritorio o en la gestión de tus archivos digitales, eres...",
        "opts": {
            "a": ("Relajado, tienes tu propio orden aunque a otros les parezca desordenado.", "Verde"),
            "b": ("Extremadamente metódico; cada documento tiene su carpeta exacta.", "Azul"),
            "c": ("Visual y creativo; a veces desorganizado porque pasas rápido a otro tema.", "Amarillo"),
            "d": ("Funcional; organizas lo justo para no perder tiempo y avanzar.", "Rojo"),
        },
    },
    {
        "q": "16. Tu energía en el ámbito profesional está orientada principalmente a...",
        "opts": {
            "a": ("Hacer el trabajo con la máxima calidad, perfección y conocimiento.", "Azul"),
            "b": ("Ser reconocido, inspirar a otros y tener visibilidad en la empresa.", "Amarillo"),
            "c": ("Alcanzar las metas propuestas, superar retos y liderar.", "Rojo"),
            "d": ("Mantener la estabilidad del equipo, ser útil y sentirte valorado.", "Verde"),
        },
    },
    {
        "q": "17. Cuando surge un conflicto fuerte en una reunión de trabajo...",
        "opts": {
            "a": ("Tratas de suavizar el ambiente con humor o buscas una salida rápida.", "Amarillo"),
            "b": ("Defiendes tu postura con pasión, debatiendo fuerte.", "Rojo"),
            "c": ("Evitas la confrontación directa, prefieres ceder un poco para mantener la paz.", "Verde"),
            "d": ("Te apegas a las reglas, los datos y la lógica, ocultando tus emociones.", "Azul"),
        },
    },
    {
        "q": "18. Si tienes que negociar plazos o recursos con otro departamento, tú...",
        "opts": {
            "a": ("Presionas hasta conseguir lo que tu equipo necesita.", "Rojo"),
            "b": ("Buscas conciliar para que ambas partes queden tranquilas y sin roces.", "Verde"),
            "c": ("Analizas los datos, cronogramas y viabilidad antes de aceptar cualquier cosa.", "Azul"),
            "d": ("Usas tus contactos y simpatía para convencerlos amigablemente.", "Amarillo"),
        },
    },
    {
        "q": "19. Cuando debes tomar una decisión importante en tu área, te basas en...",
        "opts": {
            "a": ("Cómo afectará al equipo y el consenso general.", "Verde"),
            "b": ("La información detallada, los datos históricos y el análisis de riesgos.", "Azul"),
            "c": ("Tu intuición, experiencia y lo que crees que será más innovador.", "Amarillo"),
            "d": ("El resultado final, el ROI y lo que genere impacto más rápido.", "Rojo"),
        },
    },
    {
        "q": "20. Al terminar un debate laboral o una negociación difícil, lo que más te importa es...",
        "opts": {
            "a": ("Saber que se tomó la decisión lógicamente correcta.", "Azul"),
            "b": ("Salir bien parado y mantener una imagen positiva.", "Amarillo"),
            "c": ("Haber logrado tu objetivo y mantener el control de la situación.", "Rojo"),
            "d": ("Que nadie haya salido lastimado y la relación siga siendo buena.", "Verde"),
        },
    },
]


# ═══════════════════════════════════════════
# CALCULAR RESULTADO DISC
# ═══════════════════════════════════════════
def calcular_disc(respuestas):
    """
    Recibe dict {0: "a", 1: "c", ...} con la opción elegida por pregunta.
    Retorna: (principal, secundario, puntajes_dict, porcentajes_dict)
    """
    conteo = {"Rojo": 0, "Amarillo": 0, "Verde": 0, "Azul": 0}
    for idx, letra in respuestas.items():
        pregunta = TEST_DISC[int(idx)]
        _, color = pregunta["opts"][letra]
        conteo[color] += 1

    total = sum(conteo.values())  # siempre 20
    porcentajes = {k: round((v / total) * 100) for k, v in conteo.items()}

    # Ordenar de mayor a menor
    ranking = sorted(conteo.items(), key=lambda x: -x[1])
    principal = ranking[0][0]
    secundario = ranking[1][0]

    return principal, secundario, conteo, porcentajes


# ═══════════════════════════════════════════
# RENDER — PANTALLA DEL PASAPORTE
# ═══════════════════════════════════════════
def render():
    email = st.session_state.get("current_user")
    if not email:
        st.warning("Selecciona un usuario primero.")
        return

    ident = db.get_identidad(email)
    nombre = ident["nombre"] if ident else email

    # ── Si ya tiene resultado, mostrar resumen ──
    if ident and ident.get("arquetipo_disc"):
        _mostrar_resultado_existente(ident)
        return

    # ── PANTALLA DE BIENVENIDA + TEST ──
    st.markdown(f"""
    <div style="text-align:center; padding: 30px 20px 10px;">
        <h1 style="font-size:2.5rem; margin-bottom:0;">🪪 Pasaporte Ítaca</h1>
        <p style="color:{TURQ_DARK}; font-size:1.2rem; margin-top:5px;">
            Bienvenido/a a bordo, <strong>{nombre.split()[0]}</strong>
        </p>
        <p style="color:#757575; max-width:600px; margin:10px auto;">
            Antes de zarpar, necesitamos conocer tu estilo de navegación.
            Responde las 20 preguntas con honestidad — no hay respuestas correctas.
        </p>
    </div>
    <hr style="border-color:{TURQ_LIGHT}; margin: 10px 40px 20px;">
    """, unsafe_allow_html=True)

    # ── FORMULARIO PAGINADO ──
    PER_PAGE = 5
    total_pages = len(TEST_DISC) // PER_PAGE  # 4 páginas de 5
    page = st.session_state.get("disc_page", 0)

    # Inicializar respuestas en session_state
    if "disc_answers" not in st.session_state:
        st.session_state.disc_answers = {}

    # Barra de progreso
    answered = len(st.session_state.disc_answers)
    st.progress(answered / len(TEST_DISC), text=f"Progreso: {answered}/{len(TEST_DISC)} preguntas")

    # Mostrar preguntas de la página actual
    start = page * PER_PAGE
    end = start + PER_PAGE
    current_qs = TEST_DISC[start:end]

    for i, q_data in enumerate(current_qs):
        q_idx = start + i
        st.markdown(f"""
        <div style="background:white; border-radius:12px; padding:18px 20px;
                    margin:12px 0; border-left:4px solid {TURQ};">
            <strong style="color:{BLACK};">{q_data['q']}</strong>
        </div>
        """, unsafe_allow_html=True)

        options_labels = [f"{letra.upper()}) {text}" for letra, (text, _) in q_data["opts"].items()]
        options_keys = list(q_data["opts"].keys())

        # Recuperar respuesta previa si existe
        prev = st.session_state.disc_answers.get(str(q_idx))
        prev_index = options_keys.index(prev) if prev in options_keys else None

        choice = st.radio(
            "Elige una opción:",
            options_keys,
            format_func=lambda k, q=q_data: f"{k.upper()}) {q['opts'][k][0]}",
            key=f"disc_q_{q_idx}",
            index=prev_index,
            label_visibility="collapsed",
        )

        if choice:
            st.session_state.disc_answers[str(q_idx)] = choice

    # ── NAVEGACIÓN ──
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if page > 0:
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.disc_page = page - 1
                st.rerun()

    with col3:
        if page < total_pages - 1:
            # Verificar que las 5 preguntas de esta página estén respondidas
            page_answered = all(str(start + i) in st.session_state.disc_answers for i in range(PER_PAGE))
            if st.button("Siguiente ➡️", use_container_width=True, disabled=not page_answered):
                st.session_state.disc_page = page + 1
                st.rerun()

    # ── BOTÓN FINAL: DESCUBRIR ARQUETIPO ──
    if page == total_pages - 1 and len(st.session_state.disc_answers) == len(TEST_DISC):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="text-align:center; padding:20px; background:{TURQ_LIGHT};
                    border-radius:16px; margin:10px 0;">
            <p style="font-size:1.1rem; color:{TURQ_DARK}; margin:0;">
                🎉 ¡Todas las preguntas respondidas! Descubre tu arquetipo.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🪪 DESCUBRIR MI ARQUETIPO", use_container_width=True, type="primary"):
            _procesar_resultado(email)


def _procesar_resultado(email):
    """Calcula DISC, guarda en BD y muestra resultado"""
    principal, secundario, conteo, porcentajes = calcular_disc(st.session_state.disc_answers)

    # Guardar en BD
    db.update_identidad(email,
        arquetipo_disc=principal,
        arquetipo_secundario=secundario,
        disc_d=conteo.get("Rojo", 0),
        disc_i=conteo.get("Amarillo", 0),
        disc_s=conteo.get("Verde", 0),
        disc_c=conteo.get("Azul", 0),
    )

    # Limpiar state del test
    st.session_state.disc_answers = {}
    st.session_state.disc_page = 0
    st.session_state.disc_done = True

    st.balloons()

    # Mostrar resultado
    info = DISC_TYPES[principal]
    info_sec = DISC_TYPES[secundario]

    st.markdown(f"""
    <div style="text-align:center; padding:40px 20px; background:linear-gradient(135deg, {info['color']}22, {info_sec['color']}22);
                border-radius:20px; margin:20px 0;">
        <p style="font-size:3rem; margin:0;">{info['emoji']}</p>
        <h1 style="color:{info['color']}; margin:5px 0;">Eres {info['name']}</h1>
        <p style="font-size:1.1rem; color:#555;">Arquetipo principal: <strong>{principal}</strong> | Secundario: <strong>{secundario}</strong></p>
        <p style="color:#777; max-width:500px; margin:15px auto;">{info['desc']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Barras de porcentaje
    st.markdown("#### Tu composición DISC:")
    for color_name in ["Rojo", "Amarillo", "Verde", "Azul"]:
        dinfo = DISC_TYPES[color_name]
        pct = porcentajes[color_name]
        st.markdown(f"{dinfo['emoji']} **{dinfo['name']}** ({color_name})")
        st.progress(pct / 100, text=f"{pct}%")

    st.markdown("---")
    st.success("✅ Tu Pasaporte Ítaca ha sido sellado. ¡Bienvenido/a a la tripulación!")

    if st.button("🚢 Zarpar hacia Ítaca OS", use_container_width=True, type="primary"):
        st.rerun()


def _mostrar_resultado_existente(ident):
    """Si ya completó el test, muestra un resumen bonito"""
    principal = ident["arquetipo_disc"]
    secundario = ident.get("arquetipo_secundario", "")
    info = DISC_TYPES.get(principal, {})

    st.markdown(f"""
    <div style="text-align:center; padding:30px; background:linear-gradient(135deg, {info.get('color','#26C6DA')}15, #fff);
                border-radius:16px;">
        <p style="font-size:2.5rem; margin:0;">{info.get('emoji','🪪')}</p>
        <h2 style="color:{info.get('color','#333')};">Tu Pasaporte: {info.get('name', principal)}</h2>
        <p>Principal: <strong>{principal}</strong> | Secundario: <strong>{secundario or 'N/A'}</strong></p>
        <p style="color:#777;">{info.get('desc','')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Barras
    st.markdown("#### Tu composición:")
    total = (ident.get("disc_d",0) + ident.get("disc_i",0) + ident.get("disc_s",0) + ident.get("disc_c",0)) or 1
    for campo, color_name in [("disc_d","Rojo"),("disc_i","Amarillo"),("disc_s","Verde"),("disc_c","Azul")]:
        dinfo = DISC_TYPES[color_name]
        val = ident.get(campo, 0)
        pct = round((val / total) * 100)
        st.markdown(f"{dinfo['emoji']} **{dinfo['name']}** — {val}/20 ({pct}%)")
        st.progress(pct / 100)

    st.info("Ya completaste tu Pasaporte. Puedes navegar por el sistema normalmente.")
