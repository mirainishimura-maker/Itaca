"""
Ítaca OS 2.0 - Configuración Global
Colores, constantes, pilares, competencias, ejercicios, badges
"""
from datetime import datetime, date

# ── MARCA ──
APP_NAME = "Ítaca OS 2.0"
APP_ICON = "⚓"
APP_TAGLINE = "Plataforma de Gestión y Desarrollo Humano"
YEAR = 2026

# ── COLORES ──
TURQ = "#26C6DA"
TURQ_DARK = "#00ACC1"
TURQ_LIGHT = "#E0F7FA"
TURQ_BG = "#F0FDFE"
GOLD = "#FFB300"
GOLD_DARK = "#E6A100"
BLACK = "#212121"
GRAY = "#757575"
WHITE = "#FFFFFF"
RED = "#E53935"
GREEN = "#43A047"
YELLOW = "#FDD835"
ORANGE = "#E65100"
BG_GRAY = "#F5F5F5"

# ── ROLES ──
ROLES = ["Admin", "Líder", "Coordinador", "Colaborador"]

# ── DISC ──
DISC_TYPES = {
    "Rojo": {"name": "Dominante", "emoji": "🔴", "color": "#E53935", "desc": "Directo, decidido, orientado a resultados"},
    "Amarillo": {"name": "Influyente", "emoji": "🟡", "color": "#FDD835", "desc": "Entusiasta, optimista, sociable"},
    "Verde": {"name": "Estable", "emoji": "🟢", "color": "#43A047", "desc": "Paciente, confiable, buen escuchador"},
    "Azul": {"name": "Concienzudo", "emoji": "🔵", "color": "#1E88E5", "desc": "Analítico, preciso, orientado a calidad"},
}

# ── ODISEA 2026 ──
OLAS = [
    {"num": 1, "meses": "Ene-Feb", "nombre": "Zarpe", "tema": "Onboarding, identidad, propósito", "emoji": "🚢"},
    {"num": 2, "meses": "Mar-Abr", "nombre": "Primeras Aguas", "tema": "Estrategia, OKR Q1", "emoji": "🌊"},
    {"num": 3, "meses": "May-Jun", "nombre": "Mar Abierto", "tema": "Liderazgo, cultura activa", "emoji": "⛵"},
    {"num": 4, "meses": "Jul-Ago", "nombre": "Tormenta", "tema": "Resiliencia, IE", "emoji": "⛈️"},
    {"num": 5, "meses": "Sep-Oct", "nombre": "Tierra a la Vista", "tema": "Evaluación 360, feedback", "emoji": "🏝️"},
    {"num": 6, "meses": "Nov-Dic", "nombre": "Llegada a Ítaca", "tema": "Cierre, celebración", "emoji": "🏆"},
]

def get_ola_actual():
    m = datetime.now().month
    idx = min((m - 1) // 2, 5)
    return OLAS[idx]

def get_progreso_odisea():
    m = datetime.now().month
    return round((m / 12) * 100)

# ── PILARES I+M ──
PILARES = [
    {
        "nombre": "ITACTIVIDAD",
        "animal": "🐿️ Ardilla",
        "gungho": "Espíritu de la Ardilla",
        "faro": "Faro de Valor",
        "color": TURQ,
        "desc": "Nuestro equipo no trae problemas, trae soluciones. Actuamos con proactividad. No esperamos que las cosas sucedan; nosotros las hacemos suceder.",
        "frase": "No nos quejamos de los problemas, los solucionamos.",
        "principio": "El trabajo es VALIOSO",
    },
    {
        "nombre": "+1 Sí Importa",
        "animal": "🦫 Castor",
        "gungho": "Estilo del Castor",
        "faro": "Faro de Guía",
        "color": GOLD,
        "desc": "Cada esfuerzo extra tiene un impacto significativo. +1 cliente satisfecho, +1 venta realizada. Nuestro compromiso con el +1 significa que siempre damos la milla extra.",
        "frase": "No nos conformamos nunca, siempre buscamos más y mejores resultados.",
        "principio": "Control del DESTINO",
    },
    {
        "nombre": "Muro de Confianza",
        "animal": "🪿 Ganso",
        "gungho": "Don del Ganso",
        "faro": "Faro de Aliento",
        "color": GREEN,
        "desc": "Somos directos y transparentes en la comunicación; cuidamos a cada miembro del equipo. La confianza es el motor que impulsa a nuestro equipo.",
        "frase": "¡No suponemos nunca, preguntamos siempre!",
        "principio": "Celebrar MUTUAMENTE",
    },
]

# ── TIPOS DE FARO ──
TIPOS_FARO = {
    "Faro de Valor": {"emoji": "🐿️", "pilar": "ITACTIVIDAD", "animal": "Ardilla", "color": TURQ, "desc": "Reconoce proactividad y soluciones"},
    "Faro de Guía": {"emoji": "🦫", "pilar": "+1 Sí Importa", "animal": "Castor", "color": GOLD, "desc": "Agradece mentoría y la milla extra"},
    "Faro de Aliento": {"emoji": "🪿", "pilar": "Muro de Confianza", "animal": "Ganso", "color": GREEN, "desc": "Apoya en momentos difíciles"},
}

# ── CHECK-IN ──
ESTADOS_CHECKIN = {"GENIAL": "😊", "NORMAL": "😐", "DIFICIL": "😔"}
AREAS_PREOCUPACION = ["Trabajo", "Personal", "Ambas"]
ETIQUETAS_EMOCIONALES = {
    "positivas": ["Energizado", "Motivado", "Tranquilo", "Inspirado", "Agradecido", "Optimista"],
    "neutras": ["Concentrado", "Pensativo", "Determinado", "Reflexivo", "Cauteloso"],
    "negativas": ["Presionado", "Cansado", "Abrumado", "Ansioso", "Frustrado", "Triste", "Desmotivado"],
}
ALL_ETIQUETAS = ETIQUETAS_EMOCIONALES["positivas"] + ETIQUETAS_EMOCIONALES["neutras"] + ETIQUETAS_EMOCIONALES["negativas"]

# ── HEXÁGONO (6 dimensiones) ──
DIMENSIONES_HEXAGONO = [
    {"nombre": "Visión Corporativa", "emoji": "🎯", "pregunta": "¿Mi equipo conoce la misión y el propósito?"},
    {"nombre": "Planificación", "emoji": "🗓️", "pregunta": "¿Tengo GANTT actualizado y prioridades claras?"},
    {"nombre": "Encaje de Talento", "emoji": "🧩", "pregunta": "¿Cada persona en el rol correcto?"},
    {"nombre": "Entrenamiento", "emoji": "🎓", "pregunta": "¿Dedico tiempo a desarrollar al equipo?"},
    {"nombre": "Evaluación y Mejora", "emoji": "🔄", "pregunta": "¿Doy feedback y mejoramos procesos?"},
    {"nombre": "Reconocimiento", "emoji": "🏆", "pregunta": "¿Celebro los logros regularmente?"},
]

# ── BRÚJULA EMOCIONAL (5 competencias Goleman) ──
COMPETENCIAS_IE = [
    {"nombre": "Autoconocimiento", "emoji": "📝", "pregunta": "¿Qué siento y por qué?", "color": "#7E57C2"},
    {"nombre": "Autorregulación", "emoji": "🎯", "pregunta": "¿Cómo gestiono lo que siento?", "color": "#26A69A"},
    {"nombre": "Motivación", "emoji": "🔥", "pregunta": "¿Para qué hago lo que hago?", "color": "#EF5350"},
    {"nombre": "Empatía", "emoji": "❤️", "pregunta": "¿Cómo están los demás?", "color": "#EC407A"},
    {"nombre": "Habilidades Sociales", "emoji": "🤝", "pregunta": "¿Cómo me relaciono?", "color": "#42A5F5"},
]

# ── ESCALA DE EVALUACIÓN ──
ESCALA = {1: "Crítico", 2: "En riesgo", 3: "En desarrollo", 4: "Sólido", 5: "Ejemplar"}

# ═══════════════════════════════════════════
# NUEVAS CONSTANTES v2.0
# ═══════════════════════════════════════════

# CRM — El Puerto
CRM_ESTADOS = ["Nuevo", "Contactado", "Inscrito", "Perdido"]
CRM_ORIGENES = ["Pauta", "Orgánico", "Referido", "Evento", "Redes"]
CRM_PRECALIFICACION = ["Alta", "Media", "Baja"]

# Finanzas — La Bóveda
FINANZAS_TIPOS = ["Ingreso", "Egreso"]
FINANZAS_CATEGORIAS_INGRESO = ["Cuota", "Matrícula", "Taller", "Evento", "Consultoría", "Otro"]
FINANZAS_CATEGORIAS_EGRESO = ["Materiales", "Planilla", "Alquiler", "Marketing", "Servicios", "Otro"]

# Escudo de Esparta (umbrales)
ESCUDO_ESTRES_LIMITE = 5
ESCUDO_TAREAS_VENCIDAS_LIMITE = 3

# Oráculo de Fugas (umbrales)
ORACULO_ESTRES_AVG = 4
ORACULO_FAROS_MIN = 0
ORACULO_TAREAS_VENCIDAS = 2

# Matriz 9-Box
NINEBOX_LABELS = {
    "Alto/Alto": "⭐ Estrella", "Alto/Medio": "📈 Alto Potencial", "Alto/Bajo": "🧩 Enigma",
    "Medio/Alto": "💪 Profesional Clave", "Medio/Medio": "✅ Contribuidor", "Medio/Bajo": "📋 Mantener",
    "Bajo/Alto": "🎯 Especialista", "Bajo/Medio": "⚠️ En Desarrollo", "Bajo/Bajo": "🔴 Acción Urgente",
}

# ── CSS GLOBAL ──
GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    .block-container { padding-top: 1rem; max-width: 900px; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; }
    /* Sidebar */
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #00ACC1 0%, #00838F 100%); }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stSelectbox label { color: rgba(255,255,255,0.8) !important; }
    /* Metric cards */
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        border-radius: 8px; padding: 8px 16px; font-weight: 600;
        background-color: #F5F5F5; border: none;
    }
    .stTabs [aria-selected="true"] { background-color: #26C6DA !important; color: white !important; }
    /* Buttons */
    .stButton > button { border-radius: 12px; font-weight: 600; padding: 0.5rem 1.5rem; transition: all 0.2s; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
    /* Cards */
    div[data-testid="stExpander"] { border-radius: 12px; border: 1px solid #E0E0E0; }
    /* Progress bars */
    .stProgress > div > div > div { background-color: #26C6DA; }
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);}
</style>
"""
