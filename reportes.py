"""
📄 Ítaca OS 2.0 — Generador de Reportes PDF
Usa ReportLab Platypus para reportes profesionales por unidad
Secciones: Clima · Faros · Focos&KRs · Hexágono · 360° · Ítaca Play
"""
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)

# ── Paleta Ítaca ──
TURQ       = colors.HexColor("#26C6DA")
TURQ_DARK  = colors.HexColor("#00ACC1")
TURQ_LIGHT = colors.HexColor("#E0F7FA")
GOLD       = colors.HexColor("#FFB300")
DARK       = colors.HexColor("#212121")
GRAY       = colors.HexColor("#757575")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
WHITE      = colors.white
GREEN      = colors.HexColor("#43A047")
RED        = colors.HexColor("#E53935")
PURPLE     = colors.HexColor("#7E57C2")
PINK       = colors.HexColor("#EC407A")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


# ═══════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════
def _build_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontSize=28, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=8
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", fontSize=14, textColor=TURQ_LIGHT,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=6
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", fontSize=11, textColor=WHITE,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4
    )
    styles["section_title"] = ParagraphStyle(
        "section_title", fontSize=14, textColor=TURQ_DARK,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
        borderPad=4
    )
    styles["subsection"] = ParagraphStyle(
        "subsection", fontSize=11, textColor=DARK,
        fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4
    )
    styles["body"] = ParagraphStyle(
        "body", fontSize=9.5, textColor=DARK,
        fontName="Helvetica", spaceAfter=4, leading=14
    )
    styles["body_gray"] = ParagraphStyle(
        "body_gray", fontSize=9, textColor=GRAY,
        fontName="Helvetica", spaceAfter=3, leading=13
    )
    styles["kpi_val"] = ParagraphStyle(
        "kpi_val", fontSize=22, textColor=TURQ_DARK,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    styles["kpi_label"] = ParagraphStyle(
        "kpi_label", fontSize=8, textColor=GRAY,
        fontName="Helvetica", alignment=TA_CENTER
    )
    styles["tag_green"] = ParagraphStyle(
        "tag_green", fontSize=8.5, textColor=GREEN,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    styles["tag_red"] = ParagraphStyle(
        "tag_red", fontSize=8.5, textColor=RED,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    styles["footer"] = ParagraphStyle(
        "footer", fontSize=7.5, textColor=GRAY,
        fontName="Helvetica", alignment=TA_CENTER
    )
    return styles


# ═══════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════
def _hr(color=TURQ_LIGHT, thickness=1):
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6, spaceBefore=2)


def _kpi_row(items, styles):
    """Fila de KPIs: [(valor, label, color), ...]"""
    cells = []
    for val, label, col in items:
        c = colors.HexColor(col) if isinstance(col, str) else col
        s = ParagraphStyle("kpi_v", fontSize=20, textColor=c,
                           fontName="Helvetica-Bold", alignment=TA_CENTER)
        sl = ParagraphStyle("kpi_l", fontSize=8, textColor=GRAY,
                            fontName="Helvetica", alignment=TA_CENTER)
        cells.append([Paragraph(str(val), s), Paragraph(label, sl)])

    col_w = (PAGE_W - 2 * MARGIN) / len(cells)
    tbl = Table([[c[0] for c in cells], [c[1] for c in cells]],
                colWidths=[col_w] * len(cells))
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _progress_bar_table(label, pct, color=TURQ, width=None):
    """Mini barra de progreso como tabla."""
    W = width or (PAGE_W - 2 * MARGIN - 4 * cm)
    filled = max(int(W * pct / 100), 1)
    empty  = max(int(W - filled), 0)

    bar = Table(
        [[" ", " "]],
        colWidths=[filled, empty],
        rowHeights=[10]
    )
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), color),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#E0E0E0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))

    outer = Table(
        [[Paragraph(f"<b>{label}</b>", ParagraphStyle("bl", fontSize=8.5,
                    textColor=DARK, fontName="Helvetica-Bold")),
          Paragraph(f"<b>{pct}%</b>", ParagraphStyle("pct", fontSize=8.5,
                    textColor=color, fontName="Helvetica-Bold", alignment=TA_RIGHT))],
         [bar, ""]],
        colWidths=[PAGE_W - 2 * MARGIN - 2 * cm, 2 * cm]
    )
    outer.setStyle(TableStyle([
        ("SPAN",          (0, 1), (1, 1)),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    return outer


def _score_table(rows, styles):
    """Tabla de puntajes: [(emoji+nombre, valor, escala), ...]"""
    ESCALA = {1:"Crítico", 2:"En riesgo", 3:"En desarrollo", 4:"Sólido", 5:"Ejemplar"}
    SCORE_COLORS = {1: RED, 2: GOLD, 3: GOLD, 4: GREEN, 5: TURQ_DARK}

    data = [["Dimensión", "Puntaje", "Nivel"]]
    for nombre, val, _ in rows:
        v = round(val or 0, 1)
        sc = ESCALA.get(round(v), "")
        col = SCORE_COLORS.get(round(v), GRAY)
        data.append([
            Paragraph(nombre, ParagraphStyle("td", fontSize=8.5, fontName="Helvetica", textColor=DARK)),
            Paragraph(f"<b>{v}/5</b>", ParagraphStyle("tv", fontSize=9, fontName="Helvetica-Bold",
                      textColor=col, alignment=TA_CENTER)),
            Paragraph(sc, ParagraphStyle("ts", fontSize=8, fontName="Helvetica",
                      textColor=col, alignment=TA_CENTER)),
        ])

    col_w = PAGE_W - 2 * MARGIN
    tbl = Table(data, colWidths=[col_w * 0.6, col_w * 0.2, col_w * 0.2])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  TURQ),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#E0E0E0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return tbl


# ═══════════════════════════════════════════
# PÁGINA DE PORTADA
# ═══════════════════════════════════════════
def _portada(story, unidad, mes, generado_por, styles):
    # Fondo turquesa simulado con tabla
    portada = Table(
        [[Paragraph("⚓ Ítaca OS 2.0", styles["cover_title"])],
         [Paragraph("Reporte Mensual de Unidad", styles["cover_sub"])],
         [Spacer(1, 0.3 * cm)],
         [Paragraph(f"Unidad: {unidad}", ParagraphStyle("cu", fontSize=18,
             textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_CENTER))],
         [Paragraph(f"Periodo: {mes}", styles["cover_meta"])],
         [Spacer(1, 0.5 * cm)],
         [Paragraph(f"Generado por: {generado_por}", styles["cover_meta"])],
         [Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["cover_meta"])],
         ],
        colWidths=[PAGE_W - 2 * MARGIN]
    )
    portada.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), TURQ_DARK),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("ROUNDEDCORNERS", [12, 12, 12, 12]),
    ]))
    story.append(portada)
    story.append(Spacer(1, 0.8 * cm))


# ═══════════════════════════════════════════
# SECCIÓN: CLIMA
# ═══════════════════════════════════════════
def _seccion_clima(story, clima_data, styles):
    story.append(Paragraph("💬 Clima del Equipo", styles["section_title"]))
    story.append(_hr())

    if not clima_data or clima_data.get("total", 0) == 0:
        story.append(Paragraph("Sin check-ins en el periodo.", styles["body_gray"]))
        story.append(Spacer(1, 0.4 * cm))
        return

    avg_e = clima_data.get("avg_estres", 0)
    total = clima_data.get("total", 0)
    alertas = clima_data.get("alertas", 0)
    por_estado = clima_data.get("por_estado", {})

    genial = por_estado.get("GENIAL", 0)
    normal = por_estado.get("NORMAL", 0)
    dificil = por_estado.get("DIFICIL", 0)

    kpis = [
        (total,       "Check-ins",       "#26C6DA"),
        (f"{avg_e}/5","Estrés promedio",  "#E53935" if avg_e >= 4 else "#FFB300" if avg_e >= 3 else "#43A047"),
        (alertas,     "Alertas (>=4)",   "#E53935"),
        (f"{genial}/{total}", "😊 GENIAL", "#43A047"),
    ]
    story.append(_kpi_row(kpis, styles))
    story.append(Spacer(1, 0.3 * cm))

    # Distribución
    if total > 0:
        story.append(Paragraph("Distribución de estados:", styles["subsection"]))
        for estado, cnt, col in [
            ("😊 GENIAL",  genial,  "#43A047"),
            ("😐 NORMAL",  normal,  "#FFB300"),
            ("😔 DIFÍCIL", dificil, "#E53935"),
        ]:
            pct = round((cnt / total) * 100) if total else 0
            story.append(_progress_bar_table(f"{estado}  ({cnt})", pct,
                                              colors.HexColor(col)))
            story.append(Spacer(1, 0.15 * cm))

    story.append(Spacer(1, 0.4 * cm))


# ═══════════════════════════════════════════
# SECCIÓN: FAROS
# ═══════════════════════════════════════════
def _seccion_faros(story, cultura_data, unidad, styles):
    story.append(Paragraph("🔦 Faros de Reconocimiento", styles["section_title"]))
    story.append(_hr())

    total_f = cultura_data.get("total_faros", 0)
    if total_f == 0:
        story.append(Paragraph("Sin faros en el periodo.", styles["body_gray"]))
        story.append(Spacer(1, 0.4 * cm))
        return

    celebraciones = cultura_data.get("celebraciones", 0)
    por_tipo = cultura_data.get("por_tipo", {})

    kpis = [
        (total_f,      "Faros enviados",  "#26C6DA"),
        (celebraciones,"Celebraciones",   "#FFB300"),
        (len(por_tipo),"Tipos usados",    "#7E57C2"),
    ]
    story.append(_kpi_row(kpis, styles))
    story.append(Spacer(1, 0.3 * cm))

    # Por tipo
    if por_tipo:
        story.append(Paragraph("Por tipo de faro:", styles["subsection"]))
        TIPO_INFO = {
            "Faro de Valor":  "🐿️",
            "Faro de Guía":   "🦫",
            "Faro de Aliento":"🪿",
        }
        for tipo, cnt in sorted(por_tipo.items(), key=lambda x: -x[1]):
            pct = round((cnt / total_f) * 100) if total_f else 0
            emoji = TIPO_INFO.get(tipo, "🔦")
            story.append(_progress_bar_table(f"{emoji} {tipo}  ({cnt})", pct))
            story.append(Spacer(1, 0.1 * cm))

    # Top receptores
    top_r = cultura_data.get("top_receptores", [])
    if top_r:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("Top receptores de faros:", styles["subsection"]))
        data = [["#", "Colaborador", "Faros recibidos"]]
        for i, (nombre, cnt) in enumerate(top_r[:5], 1):
            medal = ["🥇","🥈","🥉","4°","5°"][i-1]
            data.append([medal, nombre, str(cnt)])
        W = PAGE_W - 2 * MARGIN
        t = Table(data, colWidths=[W*0.1, W*0.65, W*0.25])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), TURQ),
            ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1),9),
            ("ALIGN",         (2,0),(-1,-1),"CENTER"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_GRAY]),
            ("GRID",          (0,0),(-1,-1),0.3, colors.HexColor("#E0E0E0")),
            ("TOPPADDING",    (0,0),(-1,-1),5),
            ("BOTTOMPADDING", (0,0),(-1,-1),5),
            ("LEFTPADDING",   (0,0),(-1,-1),6),
        ]))
        story.append(t)

    story.append(Spacer(1, 0.4 * cm))


# ═══════════════════════════════════════════
# SECCIÓN: FOCOS & KRs
# ═══════════════════════════════════════════
def _seccion_focos(story, focos_data, styles):
    story.append(Paragraph("🎯 Focos Estratégicos & KRs", styles["section_title"]))
    story.append(_hr())

    if not focos_data:
        story.append(Paragraph("Sin focos estratégicos registrados.", styles["body_gray"]))
        story.append(Spacer(1, 0.4 * cm))
        return

    activos   = [f for f in focos_data if f.get("estado") != "Completado"]
    completos = [f for f in focos_data if f.get("estado") == "Completado"]
    avg_prog  = round(sum(f.get("progreso", 0) for f in focos_data) / len(focos_data)) if focos_data else 0

    kpis = [
        (len(focos_data), "Focos totales",   "#26C6DA"),
        (len(activos),    "En progreso",      "#FFB300"),
        (len(completos),  "Completados",      "#43A047"),
        (f"{avg_prog}%",  "Progreso promedio","#7E57C2"),
    ]
    story.append(_kpi_row(kpis, styles))
    story.append(Spacer(1, 0.3 * cm))

    for f in focos_data[:8]:  # máx 8 focos
        prog = f.get("progreso", 0)
        col_prog = GREEN if prog >= 80 else GOLD if prog >= 50 else RED
        block = [
            _progress_bar_table(
                f"🎯 {f['nombre']}  |  {f.get('periodo','')}  |  Estado: {f.get('estado','')}",
                prog, col_prog
            ),
        ]
        # KRs
        krs = f.get("krs", [])
        if krs:
            for kr in krs[:4]:
                kp = kr.get("progreso", 0)
                block.append(Spacer(1, 0.05 * cm))
                block.append(_progress_bar_table(
                    f"    📌 {kr['nombre']}",
                    kp,
                    TURQ if kp >= 70 else GOLD,
                ))
        block.append(Spacer(1, 0.25 * cm))
        story.append(KeepTogether(block))

    story.append(Spacer(1, 0.2 * cm))


# ═══════════════════════════════════════════
# SECCIÓN: HEXÁGONO
# ═══════════════════════════════════════════
def _seccion_hexagono(story, hex_data, styles):
    story.append(Paragraph("🧭 Hexágono de Liderazgo", styles["section_title"]))
    story.append(_hr())

    if not hex_data:
        story.append(Paragraph("Sin evaluaciones de Hexágono en el periodo.", styles["body_gray"]))
        story.append(Spacer(1, 0.4 * cm))
        return

    # Última evaluación
    ultima = hex_data[0]
    story.append(Paragraph(
        f"Última evaluación: <b>{ultima.get('periodo','')}</b>  |  "
        f"Promedio: <b>{ultima.get('promedio','')}/5</b>",
        styles["body"]
    ))
    story.append(Spacer(1, 0.2 * cm))

    DIMS = [
        ("🎯 Visión Corporativa",   "vision"),
        ("🗓️ Planificación",       "planificacion"),
        ("🧩 Encaje de Talento",    "encaje"),
        ("🎓 Entrenamiento",        "entrenamiento"),
        ("🔄 Evaluación y Mejora",  "evaluacion_mejora"),
        ("🏆 Reconocimiento",       "reconocimiento"),
    ]
    rows = [(d[0], ultima.get(d[1], 0), "") for d in DIMS]
    story.append(_score_table(rows, styles))

    if ultima.get("reflexion"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"<i>Reflexión: {ultima['reflexion']}</i>", styles["body_gray"]))

    story.append(Spacer(1, 0.4 * cm))


# ═══════════════════════════════════════════
# SECCIÓN: EVALUACIÓN 360°
# ═══════════════════════════════════════════
def _seccion_360(story, data_360, styles):
    story.append(Paragraph("🔄 Evaluación 360°", styles["section_title"]))
    story.append(_hr())

    if not data_360 or data_360.get("total_evaluados", 0) == 0:
        story.append(Paragraph("Sin evaluaciones 360° en el periodo.", styles["body_gray"]))
        story.append(Spacer(1, 0.4 * cm))
        return

    story.append(Paragraph(
        f"Evaluadores participantes: <b>{data_360.get('total_evaluadores',0)}</b>  |  "
        f"Colaboradores evaluados: <b>{data_360.get('total_evaluados',0)}</b>",
        styles["body"]
    ))
    story.append(Spacer(1, 0.2 * cm))

    top = data_360.get("top_colaboradores", [])
    if top:
        story.append(Paragraph("Top colaboradores por promedio 360°:", styles["subsection"]))
        data = [["#", "Colaborador", "Unidad", "Promedio 360°"]]
        for i, t in enumerate(top, 1):
            medal = ["🥇","🥈","🥉","4°","5°"][i-1] if i <= 5 else f"{i}°"
            data.append([medal, t.get("nombre",""), t.get("unidad",""),
                         f"{round(t.get('prom',0),2)}/5"])
        W = PAGE_W - 2 * MARGIN
        tbl = Table(data, colWidths=[W*0.08, W*0.42, W*0.3, W*0.2])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), PURPLE),
            ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1),9),
            ("ALIGN",         (3,0),(-1,-1),"CENTER"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_GRAY]),
            ("GRID",          (0,0),(-1,-1),0.3, colors.HexColor("#E0E0E0")),
            ("TOPPADDING",    (0,0),(-1,-1),5),
            ("BOTTOMPADDING", (0,0),(-1,-1),5),
            ("LEFTPADDING",   (0,0),(-1,-1),6),
        ]))
        story.append(tbl)

    story.append(Spacer(1, 0.4 * cm))


# ═══════════════════════════════════════════
# SECCIÓN: ÍTACA PLAY
# ═══════════════════════════════════════════
def _seccion_play(story, play_data, styles):
    story.append(Paragraph("🎬 Ítaca Play — Capacitaciones", styles["section_title"]))
    story.append(_hr())

    if not play_data or play_data.get("total_aprobados", 0) == 0:
        story.append(Paragraph("Sin cursos completados en el periodo.", styles["body_gray"]))
        story.append(Spacer(1, 0.4 * cm))
        return

    kpis = [
        (play_data.get("total_cursos", 0),    "Cursos activos",  "#26C6DA"),
        (play_data.get("total_aprobados", 0),  "Aprobaciones",   "#43A047"),
        (play_data.get("total_intentos", 0),   "Intentos totales","#FFB300"),
    ]
    story.append(_kpi_row(kpis, styles))
    story.append(Spacer(1, 0.3 * cm))

    ranking = play_data.get("ranking", [])
    if ranking:
        story.append(Paragraph("Ranking Ítaca Play de la unidad:", styles["subsection"]))
        data = [["#", "Colaborador", "Cursos", "Pts Play"]]
        for i, r in enumerate(ranking[:8], 1):
            medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"{i}°"
            data.append([medal, r.get("nombre",""),
                         str(r.get("cursos_completados",0)),
                         str(r.get("puntos_play",0))])
        W = PAGE_W - 2 * MARGIN
        tbl = Table(data, colWidths=[W*0.08, W*0.52, W*0.2, W*0.2])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), TURQ_DARK),
            ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1),9),
            ("ALIGN",         (2,0),(-1,-1),"CENTER"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_GRAY]),
            ("GRID",          (0,0),(-1,-1),0.3, colors.HexColor("#E0E0E0")),
            ("TOPPADDING",    (0,0),(-1,-1),5),
            ("BOTTOMPADDING", (0,0),(-1,-1),5),
            ("LEFTPADDING",   (0,0),(-1,-1),6),
        ]))
        story.append(tbl)

    story.append(Spacer(1, 0.4 * cm))


# ═══════════════════════════════════════════
# FOOTER en cada página
# ═══════════════════════════════════════════
def _make_footer(unidad, mes):
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GRAY)
        canvas.drawString(MARGIN, 1.2 * cm,
            f"⚓ Ítaca OS 2.0  |  {unidad}  |  {mes}")
        canvas.drawRightString(PAGE_W - MARGIN, 1.2 * cm,
            f"Página {doc.page}")
        canvas.setStrokeColor(TURQ_LIGHT)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 1.5 * cm, PAGE_W - MARGIN, 1.5 * cm)
        canvas.restoreState()
    return _footer


# ═══════════════════════════════════════════
# FUNCIÓN PRINCIPAL — GENERAR PDF
# ═══════════════════════════════════════════
def generar_reporte_pdf(
    unidad: str,
    mes: str,
    generado_por: str,
    clima_data: dict,
    cultura_data: dict,
    focos_data: list,
    hex_data: list,
    data_360: dict,
    play_data: dict,
) -> bytes:
    """
    Genera el PDF completo y retorna bytes para descarga con st.download_button.

    Parámetros:
        unidad        — nombre de la unidad
        mes           — ej: "Febrero 2026"
        generado_por  — nombre del usuario que genera
        clima_data    — resultado de db.get_reporte_clima(unidad)
        cultura_data  — resultado de db.get_reporte_cultura() filtrado por unidad
        focos_data    — resultado de db.get_reporte_estrategico(unidad)
        hex_data      — resultado de db.get_my_hexagono(email_lider)
        data_360      — resultado de db.get_stats_360_admin(periodo_id)
        play_data     — resultado de db.get_play_stats_admin()
    """
    buffer = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=2.5 * cm,
        title=f"Reporte {unidad} — {mes}",
        author="Ítaca OS 2.0",
    )

    story = []

    # ── PORTADA ──
    _portada(story, unidad, mes, generado_por, styles)
    story.append(PageBreak())

    # ── ÍNDICE rápido ──
    story.append(Paragraph("📋 Contenido del Reporte", styles["section_title"]))
    story.append(_hr())
    secciones = [
        "1. Clima del Equipo (Check-ins & Estrés)",
        "2. Faros de Reconocimiento",
        "3. Focos Estratégicos & KRs",
        "4. Hexágono de Liderazgo",
        "5. Evaluación 360°",
        "6. Ítaca Play — Capacitaciones",
    ]
    for s in secciones:
        story.append(Paragraph(s, styles["body"]))
    story.append(PageBreak())

    # ── SECCIONES ──
    _seccion_clima(story, clima_data, styles)
    story.append(_hr(LIGHT_GRAY, 0.5))
    _seccion_faros(story, cultura_data, unidad, styles)
    story.append(PageBreak())

    _seccion_focos(story, focos_data, styles)
    story.append(PageBreak())

    _seccion_hexagono(story, hex_data, styles)
    story.append(_hr(LIGHT_GRAY, 0.5))
    _seccion_360(story, data_360, styles)
    story.append(PageBreak())

    _seccion_play(story, play_data, styles)

    # ── CIERRE ──
    story.append(Spacer(1, 1 * cm))
    cierre = Table(
        [[Paragraph(
            f"Reporte generado automáticamente por Ítaca OS 2.0<br/>"
            f"{datetime.now().strftime('%d/%m/%Y a las %H:%M')} — {generado_por}",
            ParagraphStyle("cierre", fontSize=8, textColor=WHITE,
                          fontName="Helvetica", alignment=TA_CENTER)
        )]],
        colWidths=[PAGE_W - 2 * MARGIN]
    )
    cierre.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), TURQ_DARK),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("ROUNDEDCORNERS",[8,8,8,8]),
    ]))
    story.append(cierre)

    # Build
    footer_fn = _make_footer(unidad, mes)
    doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)

    buffer.seek(0)
    return buffer.read()
