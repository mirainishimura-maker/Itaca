"""🏠 Home — Muro en vivo · Dark mode · Auto-refresh cada 30s"""
import streamlit as st
import database as db
from config import get_ola_actual, get_progreso_odisea
from datetime import datetime
import time

REFRESH_INTERVAL = 30
TIPO_FARO_INFO = {
    "Faro de Valor":   {"emoji":"🐿️","color":"#26C6DA"},
    "Faro de Guía":    {"emoji":"🦫","color":"#FFB300"},
    "Faro de Aliento": {"emoji":"🪿","color":"#43A047"},
}


def render():
    email  = st.session_state.get("current_user","")
    nombre = st.session_state.get("user_name","Tripulante")
    rol    = st.session_state.get("user_rol","Colaborador")
    prefs  = db.get_preferencias_ui(email)
    color  = prefs.get("color_favorito","#26C6DA")
    dark   = prefs.get("dark_mode", False)

    _css(color, dark)
    _auto_refresh()

    hora = datetime.now().hour
    saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 18 else "Buenas noches"
    st.markdown(f'<h1 class="home-title">{saludo}, {nombre.split()[0]} <span class="anc">⚓</span></h1>', unsafe_allow_html=True)

    ola = get_ola_actual()
    prog = get_progreso_odisea()
    st.markdown(f'<div class="ola-banner"><span style="font-size:1.3rem;">{ola["emoji"]}</span>&nbsp; Ola {ola["num"]}: <b>{ola["nombre"]}</b> — {ola["tema"]}</div>', unsafe_allow_html=True)
    st.progress(prog/100, text=f"Odisea 2026: {prog}%")
    st.divider()

    _kpis(email)
    st.divider()

    c1,c2,c3 = st.columns(3)
    if c1.button("💬 Check-in", use_container_width=True, type="primary"):
        st.session_state.current_page = "Cultura Ítaca"; st.rerun()
    if c2.button("🔦 Enviar Faro", use_container_width=True):
        st.session_state.current_page = "Cultura Ítaca"; st.rerun()
    if c3.button("🎬 Ítaca Play", use_container_width=True):
        st.session_state.current_page = "🎬 Ítaca Play"; st.rerun()

    st.divider()
    _muro(email)

    if rol in ["Admin","Líder","Coordinador"]:
        st.divider()
        _pulso(email)


def _auto_refresh():
    now  = time.time()
    last = st.session_state.get("_last_refresh", 0)
    remaining = max(0, int(REFRESH_INTERVAL - (now - last)))
    _, col = st.columns([7,1])
    if col.button(f"🔄{remaining}s", key="rfr", help="Actualizar ahora"):
        st.session_state._last_refresh = now; st.rerun()
    if now - last >= REFRESH_INTERVAL:
        st.session_state._last_refresh = now
        time.sleep(0.05); st.rerun()


def _kpis(email):
    puntos  = db.get_total_puntos(email)
    logros  = len(db.get_my_logros(email))
    chk     = db.get_my_checkins(email, 1)
    estres  = chk[0]["nivel_estres"] if chk else 0
    stats   = db.get_feed_stats()
    nivel   = "Almirante 🎖️" if puntos>=500 else "Capitán ⚓" if puntos>=200 else "Navegante 🧭" if puntos>=80 else "Marinero 🚣"
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Nivel", nivel.split()[0], nivel.split()[1])
    c2.metric("⭐ Puntos", puntos)
    c3.metric("🏆 Logros", logros)
    c4.metric("💆 Estrés", f"{estres}/5")
    st.markdown(
        f'<div class="comm-bar">🔦 <b>{stats["faros_hoy"]}</b> faros hoy &nbsp;·&nbsp; '
        f'💬 <b>{stats["checkins_semana"]}</b> check-ins esta semana &nbsp;·&nbsp; '
        f'🎬 <b>{stats["play_hoy"]}</b> cursos hoy &nbsp;·&nbsp; '
        f'👥 <b>{stats["total_activos"]}</b> activos</div>', unsafe_allow_html=True)


def _muro(email_actual):
    st.markdown('<h3 class="sec-title">🌊 Muro en Vivo</h3>', unsafe_allow_html=True)
    filtro = st.selectbox("", ["Todo","🔦 Faros","🏆 Logros","🎬 Play"],
                          label_visibility="collapsed", key="muro_f")
    eventos = db.get_feed_vivo(25)
    tipo_map = {"🔦 Faros":"faro","🏆 Logros":"logro","🎬 Play":"play"}
    if filtro != "Todo":
        eventos = [e for e in eventos if e.get("tipo_evento") == tipo_map.get(filtro)]
    if not eventos:
        st.markdown('<div class="empty">🌊 El muro está tranquilo…<br><small>¡Sé el primero en encender un faro!</small></div>', unsafe_allow_html=True)
        return
    for ev in eventos:
        t = ev.get("tipo_evento")
        if t == "faro":   _card_faro(ev)
        elif t == "logro": _card_logro(ev)
        elif t == "play":  _card_play(ev)


def _av(nombre, foto, color, sz=42):
    ini = "".join(p[0].upper() for p in (nombre or "?").split()[:2])
    if foto and foto.startswith("data:"):
        return f'<img src="{foto}" style="width:{sz}px;height:{sz}px;border-radius:50%;object-fit:cover;border:2px solid {color};flex-shrink:0;" />'
    return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:{sz//3}px;color:white;flex-shrink:0;">{ini}</div>'

def _rel(fecha_str):
    if not fecha_str: return ""
    try:
        s = int((datetime.now() - datetime.fromisoformat(fecha_str[:19])).total_seconds())
        if s<60: return "ahora"
        if s<3600: return f"hace {s//60}m"
        if s<86400: return f"hace {s//3600}h"
        return f"hace {s//86400}d"
    except: return ""

def _card_faro(ev):
    info  = TIPO_FARO_INFO.get(ev.get("tipo_faro",""), {"emoji":"🔦","color":"#26C6DA"})
    color = ev.get("color_emisor") or info["color"]
    av    = _av(ev.get("nombre_emisor",""), ev.get("foto_emisor",""), color)
    t     = _rel(ev.get("fecha"))
    msg   = (ev.get("mensaje","") or "")[:120]
    fid   = ev.get("id","")
    cel   = ev.get("celebraciones",0)
    st.markdown(f'''<div class="ecard" style="border-left:4px solid {color};">
        <div class="ch">{av}
        <div class="cm"><span class="ca"><b>{ev.get("nombre_emisor","")}</b> <span style="color:#999;">→</span> <b>{ev.get("nombre_receptor","")}</b></span>
        <span class="ct">{t}</span></div>
        <span class="tb" style="background:{color}22;color:{color};">{info["emoji"]} {ev.get("tipo_faro","")}</span></div>
        <p class="msg">"{msg}"</p>
        <div style="margin-left:52px;font-size:0.78rem;color:#999;">👏 {cel}</div>
    </div>''', unsafe_allow_html=True)
    if st.button("👏 Celebrar", key=f"c_{fid}_{ev.get('nombre_emisor','')}"):
        db.celebrar_faro(fid); st.rerun()

def _card_logro(ev):
    color = ev.get("color_favorito") or "#FFB300"
    av    = _av(ev.get("nombre_usuario",""), ev.get("foto_url",""), color)
    t     = _rel(ev.get("fecha"))
    st.markdown(f'''<div class="ecard" style="border-left:4px solid #FFB300;">
        <div class="ch">{av}
        <div class="cm"><span class="ca"><b>{ev.get("nombre_usuario","")}</b> desbloqueó un logro</span>
        <span class="ct">{t}</span></div>
        <span class="tb" style="background:#FFF8E1;color:#F9A825;">🏆 Logro</span></div>
        <div class="br"><span style="font-size:1.7rem;">{ev.get("icono","🏆")}</span>
        <div><div class="bn">{ev.get("nombre_badge","")}</div><div class="bd">{ev.get("descripcion","")}</div></div>
        <span class="bp">+{ev.get("puntos",0)} pts</span></div>
    </div>''', unsafe_allow_html=True)

def _card_play(ev):
    color = ev.get("color_favorito") or "#7E57C2"
    av    = _av(ev.get("nombre_usuario",""), ev.get("foto_url",""), color)
    t     = _rel(ev.get("fecha"))
    st.markdown(f'''<div class="ecard" style="border-left:4px solid #7E57C2;">
        <div class="ch">{av}
        <div class="cm"><span class="ca"><b>{ev.get("nombre_usuario","")}</b> completó un curso</span>
        <span class="ct">{t}</span></div>
        <span class="tb" style="background:#EDE7F6;color:#7E57C2;">🎬 Play</span></div>
        <div class="br"><span style="font-size:1.7rem;">{ev.get("badge_icono","🎬")}</span>
        <div><div class="bn">{ev.get("curso_titulo","")}</div><div class="bd">{ev.get("categoria","")}</div></div>
        <span class="bp" style="color:#7E57C2;">+{ev.get("puntos_ganados",0)} pts</span></div>
    </div>''', unsafe_allow_html=True)

def _pulso(email):
    st.markdown('<h3 class="sec-title">📊 Pulso de tu Equipo</h3>', unsafe_allow_html=True)
    chks = db.get_team_checkins(email)
    if not chks:
        st.info("No hay check-ins recientes de tu equipo."); return
    for c in chks[:6]:
        emoji = {"GENIAL":"😊","NORMAL":"😐","DIFICIL":"😔"}.get(c["estado_general"],"❓")
        e = c["nivel_estres"]
        col = "#E53935" if e>=4 else "#FFB300" if e==3 else "#43A047"
        st.markdown(f'<div style="padding:7px 12px;border-radius:9px;background:#F8FAFC;border:1px solid #E2E8F0;margin-bottom:5px;">{emoji} <b>{c.get("nombre",c["email"])}</b> <span style="color:{col};margin-left:8px;">Estrés: {e}/5</span></div>', unsafe_allow_html=True)


def _css(color, dark):
    bg   = "#0F1117" if dark else "#F8FAFC"
    card = "#1E2130" if dark else "#FFFFFF"
    txt  = "#E8EAF0" if dark else "#1A1D2E"
    dim  = "#8B92A8" if dark else "#6B7280"
    brd  = "#2E3450" if dark else "#E2E8F0"
    shd  = "rgba(0,0,0,0.4)" if dark else "rgba(0,0,0,0.07)"
    sidebar_dark = '[data-testid="stSidebar"]{background:linear-gradient(180deg,#1A1D2E 0%,#0F1117 100%)!important;}' if dark else ""
    st.markdown(f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap');
    .stApp{{background:{bg}!important;font-family:'DM Sans',sans-serif;}}
    .block-container{{padding-top:1.2rem!important;}}
    .home-title{{font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;color:{txt};margin-bottom:2px;}}
    .anc{{background:linear-gradient(135deg,{color},{color}99);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
    .ola-banner{{display:flex;align-items:center;gap:8px;background:{color}12;border:1px solid {color}30;border-radius:10px;padding:9px 14px;margin-bottom:8px;color:{txt};font-size:0.9rem;}}
    .comm-bar{{background:{card};border:1px solid {brd};border-radius:9px;padding:9px 14px;font-size:0.83rem;color:{dim};margin-top:7px;text-align:center;}}
    .comm-bar b{{color:{color};}}
    .sec-title{{font-family:'Syne',sans-serif;font-size:1.18rem;font-weight:700;color:{txt};margin:0 0 10px;}}
    .ecard{{background:{card};border-radius:13px;border:1px solid {brd};padding:13px 15px;margin-bottom:9px;box-shadow:0 2px 8px {shd};animation:sIn .35s ease both;transition:transform .15s,box-shadow .15s;}}
    .ecard:hover{{transform:translateY(-2px);box-shadow:0 6px 18px {shd};}}
    @keyframes sIn{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
    .ecard:nth-child(1){{animation-delay:.00s}}.ecard:nth-child(2){{animation-delay:.05s}}.ecard:nth-child(3){{animation-delay:.10s}}.ecard:nth-child(4){{animation-delay:.15s}}.ecard:nth-child(n+5){{animation-delay:.20s}}
    .ch{{display:flex;align-items:center;gap:9px;margin-bottom:7px;}}
    .cm{{flex:1;display:flex;flex-direction:column;gap:1px;}}
    .ca{{font-size:0.86rem;font-weight:600;color:{txt};}}
    .ct{{font-size:0.72rem;color:{dim};}}
    .tb{{border-radius:18px;padding:2px 9px;font-size:0.72rem;font-weight:600;white-space:nowrap;}}
    .msg{{font-size:0.85rem;color:{dim};font-style:italic;margin:2px 0 6px 51px;line-height:1.5;}}
    .br{{display:flex;align-items:center;gap:10px;margin-left:51px;margin-top:3px;}}
    .bn{{font-weight:600;font-size:0.88rem;color:{txt};}}
    .bd{{font-size:0.76rem;color:{dim};}}
    .bp{{margin-left:auto;font-weight:700;font-size:0.88rem;color:#FFB300;white-space:nowrap;}}
    .empty{{text-align:center;padding:36px 20px;color:{dim};font-size:.95rem;line-height:1.8;}}
    {sidebar_dark}
    </style>""", unsafe_allow_html=True)
