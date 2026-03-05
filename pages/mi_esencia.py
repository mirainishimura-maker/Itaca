"""👤 Mi Esencia — Perfil · DISC · Meta Trascendente · Personalización"""
import streamlit as st
import database as db
from config import DISC_TYPES
import base64

COLORES_PRESET = [
    ("#26C6DA","Turquesa"), ("#FFB300","Dorado"),  ("#43A047","Verde"),
    ("#7E57C2","Púrpura"),  ("#EC407A","Rosa"),     ("#E53935","Rojo"),
    ("#1E88E5","Azul"),     ("#FF7043","Naranja"),  ("#00ACC1","Cian"),
    ("#8D6E63","Tierra"),
]


def render():
    email = st.session_state.get("current_user","")
    ident = db.get_identidad(email)
    if not ident:
        st.warning("No se encontró tu perfil."); return

    st.markdown("## 👤 Mi Esencia")
    tabs = st.tabs(["🪪 Mi Perfil","🧬 Mi DISC","🎯 Meta Trascendente","🎨 Personalizar"])

    with tabs[0]:
        c1,c2 = st.columns(2)
        c1.markdown(f"**Nombre:** {ident['nombre']}")
        c1.markdown(f"**Puesto:** {ident.get('puesto','N/A')}")
        c1.markdown(f"**Unidad:** {ident.get('unidad','N/A')}")
        c2.markdown(f"**Rol:** {ident.get('rol','N/A')}")
        c2.markdown(f"**Ingreso:** {ident.get('fecha_ingreso','N/A')}")
        c2.markdown(f"**Teléfono:** {ident.get('telefono','N/A')}")
        st.divider()
        st.markdown("#### ✏️ Editar mi perfil")
        with st.form("edit_profile"):
            frase      = st.text_input("Frase personal / Mantra",  value=ident.get("frase_personal","") or "")
            fortalezas = st.text_area("Mis fortalezas",            value=ident.get("fortalezas","") or "")
            limitantes = st.text_area("Mis áreas de mejora",       value=ident.get("limitantes","") or "")
            if st.form_submit_button("Guardar cambios"):
                db.update_identidad(email, frase_personal=frase,
                                    fortalezas=fortalezas, limitantes=limitantes)
                st.success("✅ Perfil actualizado."); st.rerun()

    with tabs[1]:
        disc = ident.get("arquetipo_disc")
        sec  = ident.get("arquetipo_secundario","")
        if disc:
            info = DISC_TYPES.get(disc,{})
            st.markdown(f"""<div style="text-align:center;padding:20px;background:{info.get('color','#ccc')}15;border-radius:16px;margin-bottom:18px;">
                <p style="font-size:2.4rem;margin:0;">{info.get('emoji','')}</p>
                <h2 style="color:{info.get('color','#333')};">{info.get('name',disc)}</h2>
                <p>Principal: <b>{disc}</b> | Secundario: <b>{sec}</b></p>
                <p style="color:#666;">{info.get('desc','')}</p>
            </div>""", unsafe_allow_html=True)
            st.markdown("#### Composición DISC:")
            total = max(sum(ident.get(f"disc_{x}",0) for x in ["d","i","s","c"]),1)
            for campo,ck in [("disc_d","Rojo"),("disc_i","Amarillo"),("disc_s","Verde"),("disc_c","Azul")]:
                d = DISC_TYPES[ck]; val = ident.get(campo,0); pct = round((val/total)*100)
                st.markdown(f"{d['emoji']} **{d['name']}** — {val}/20 ({pct}%)")
                st.progress(pct/100)
        else:
            st.info("Aún no completaste tu Test DISC.")
            if st.button("🪪 Ir al Pasaporte"):
                st.session_state.current_page = "Pasaporte"; st.rerun()

    with tabs[2]:
        meta = ident.get("meta_trascendente","") or ""
        prog = ident.get("progreso_meta",0) or 0
        st.markdown("#### 🎯 Mi Meta Trascendente")
        st.caption("¿Cuál es tu propósito más grande en este camino?")
        with st.form("meta_form"):
            nueva_meta = st.text_area("Meta Trascendente", value=meta,
                                       placeholder="Ej: Convertirme en un líder que inspira...")
            nuevo_prog = st.slider("Progreso actual", 0, 100, prog)
            if st.form_submit_button("Guardar meta"):
                db.update_identidad(email, meta_trascendente=nueva_meta, progreso_meta=nuevo_prog)
                st.success("✅ Meta guardada."); st.rerun()
        if meta:
            st.progress(prog/100, text=f"Progreso: {prog}%")

    with tabs[3]:
        _tab_personalizar(email, ident)


def _tab_personalizar(email, ident):
    st.markdown("#### 🎨 Personaliza tu experiencia")
    st.caption("Tu foto y color aparecen en el Muro de Faros y en tu tarjeta.")
    prefs   = db.get_preferencias_ui(email)
    color   = prefs.get("color_favorito","#26C6DA")
    dark    = prefs.get("dark_mode", False)
    foto    = prefs.get("foto_url","")
    nombre  = ident.get("nombre","")
    ini     = "".join(p[0].upper() for p in nombre.split()[:2])

    # ── Foto ──
    st.markdown("##### 📸 Foto de perfil")
    cu, cp = st.columns([2,1])
    with cu:
        up = st.file_uploader("JPG / PNG / WebP — máx 2MB", type=["jpg","jpeg","png","webp"])
        if up:
            if up.size > 2*1024*1024:
                st.error("⚠️ Foto muy grande. Máximo 2MB.")
            else:
                if st.button("💾 Guardar foto", type="primary"):
                    db.save_foto_perfil(email, up.read(), up.type or "image/jpeg")
                    st.success("✅ Foto guardada."); st.rerun()
    with cp:
        st.markdown("**Vista previa:**")
        show = foto
        if up and up.size <= 2*1024*1024:
            up.seek(0); show = f"data:{up.type};base64,{base64.b64encode(up.read()).decode()}"
        if show and show.startswith("data:"):
            st.markdown(f'<img src="{show}" style="width:72px;height:72px;border-radius:50%;object-fit:cover;border:3px solid {color};" />', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="width:72px;height:72px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:700;color:white;">{ini}</div>', unsafe_allow_html=True)
    if foto:
        if st.button("🗑️ Eliminar foto"):
            db.update_identidad(email, foto_url=""); st.success("Foto eliminada."); st.rerun()

    st.divider()

    # ── Color ──
    st.markdown("##### 🎨 Color favorito")
    cols = st.columns(5)
    for i,(hx,nm) in enumerate(COLORES_PRESET):
        with cols[i%5]:
            sel = hx == color
            st.markdown(f'<div style="width:34px;height:34px;border-radius:50%;background:{hx};border:{"3px solid #212121" if sel else "2px solid #E0E0E0"};margin:0 auto 2px;display:flex;align-items:center;justify-content:center;font-size:13px;color:white;font-weight:700;">{"✓" if sel else ""}</div>', unsafe_allow_html=True)
            if st.button(nm, key=f"c_{hx}", use_container_width=True):
                db.save_preferencias_ui(email, hx, dark); st.rerun()
    cust = st.color_picker("Color personalizado:", value=color)
    if cust != color:
        if st.button("Aplicar color personalizado"):
            db.save_preferencias_ui(email, cust, dark); st.rerun()

    st.divider()

    # ── Modo ──
    st.markdown("##### 🌙 Modo de visualización")
    m1,m2 = st.columns(2)
    with m1:
        brd = "3px solid #212121" if not dark else "2px solid #E0E0E0"
        st.markdown(f'<div style="border:{brd};border-radius:11px;padding:13px;text-align:center;background:#F8FAFC;">☀️<br><b>Modo Claro</b></div>', unsafe_allow_html=True)
        if st.button("☀️ Activar", key="bl", use_container_width=True, type="primary" if not dark else "secondary"):
            db.save_preferencias_ui(email, color, False); st.rerun()
    with m2:
        brd2 = "3px solid #26C6DA" if dark else "2px solid #E0E0E0"
        st.markdown(f'<div style="border:{brd2};border-radius:11px;padding:13px;text-align:center;background:#1E2130;">🌙<br><b style="color:#E8EAF0;">Modo Oscuro</b></div>', unsafe_allow_html=True)
        if st.button("🌙 Activar", key="bd", use_container_width=True, type="primary" if dark else "secondary"):
            db.save_preferencias_ui(email, color, True); st.rerun()

    st.divider()

    # ── Preview tarjeta ──
    st.markdown("##### 👁️ Así te ven en el Muro")
    av = (f'<img src="{foto}" style="width:44px;height:44px;border-radius:50%;object-fit:cover;border:2px solid {color};" />'
          if foto and foto.startswith("data:")
          else f'<div style="width:44px;height:44px;border-radius:50%;background:{color};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:white;">{ini}</div>')
    bg  = "#1E2130" if dark else "#FFFFFF"
    tx  = "#E8EAF0" if dark else "#1A1D2E"
    brd3= "#2E3450" if dark else "#E2E8F0"
    st.markdown(f'<div style="background:{bg};border:1px solid {brd3};border-left:4px solid {color};border-radius:13px;padding:13px;"><div style="display:flex;align-items:center;gap:10px;">{av}<div><div style="font-weight:700;color:{tx};">{nombre}</div><div style="font-size:0.77rem;color:#888;">→ Compañero/a · hace 2m</div></div><span style="margin-left:auto;background:{color}22;color:{color};border-radius:18px;padding:2px 9px;font-size:0.72rem;font-weight:600;">🔦 Faro</span></div><p style="font-size:0.83rem;color:#888;font-style:italic;margin:7px 0 0 54px;">"Ejemplo de mensaje de faro..."</p></div>', unsafe_allow_html=True)
