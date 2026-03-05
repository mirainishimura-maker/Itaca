"""
🎯 Mi Estrategia — Réplica exacta del Excel de Planes Estratégicos
Tab 1: Plan Estratégico (Focos → OKR → KR → Actividades → Tareas)
Tab 2: Seguimiento Económico (Meta vs Real × Mes + Proyección Presupuestal)
Tab 3: Seguimiento Sprint (Tareas operativas con avance)
"""
import streamlit as st
import pandas as pd
import database as db
from config import TURQ, TURQ_DARK, GOLD, GREEN, RED


MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _selector_unidad(key_suffix, rol, unidad_propia):
    """Selector de unidad: admin ve todas, líder ve la suya."""
    if rol == "Admin":
        all_u = db.get_units()
        pe_u = sorted(set(r["unidad"] for r in db.get_planes_todas_unidades()))
        combined = sorted(set(all_u + pe_u))
        return st.selectbox("📁 Unidad de Negocio:", combined, key=f"unit_{key_suffix}")
    else:
        st.markdown(f"**Unidad:** {unidad_propia}")
        return unidad_propia


def render():
    email = st.session_state.get("current_user", "")
    rol = st.session_state.get("user_rol", "Colaborador")
    ident = db.get_identidad(email)
    unidad = ident.get("unidad", "") if ident else ""

    st.markdown("## 🎯 Mi Estrategia")

    tabs = st.tabs([
        "📋 Plan Estratégico",
        "💰 Seguimiento Económico",
        "🏃 Sprint Operativo",
    ])

    # ══════════════════════════════════════════════════════
    # TAB 1: PLAN ESTRATÉGICO (El Excel grande: Focos→Tareas)
    # ══════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown("### 📋 Plan Estratégico 2026")
        st.caption("Focos → Objetivos → KR → Actividades — Tal cual tu Excel.")

        unidad_plan = _selector_unidad("plan", rol, unidad)

        if not unidad_plan:
            st.warning("No tienes unidad asignada.")
        else:
            plan_rows = db.get_plan_estrategico(unidad_plan)

            cols = ["foco_estrategico", "objetivo", "kr", "actividad_clave"]

            if plan_rows:
                df = pd.DataFrame(plan_rows)[cols]
            else:
                df = pd.DataFrame([
                    {"foco_estrategico": "", "objetivo": "", "kr": "", "actividad_clave": ""}
                    for _ in range(3)
                ])

            plan_config = {
                "foco_estrategico": st.column_config.TextColumn(
                    "🎯 Foco Estratégico", width="medium",
                    help="Ej: ITACA FAN, Sostenibilidad Económica, LEC",
                ),
                "objetivo": st.column_config.TextColumn(
                    "📌 Objetivo", width="large",
                ),
                "kr": st.column_config.TextColumn(
                    "📏 KR / Indicador", width="medium",
                ),
                "actividad_clave": st.column_config.TextColumn(
                    "⚡ Actividad Clave", width="large",
                ),
            }

            edited_plan = st.data_editor(
                df, column_config=plan_config, num_rows="dynamic",
                use_container_width=True, hide_index=True,
                key=f"pe_{unidad_plan}",
            )

            # Resumen
            st.markdown("---")
            if edited_plan is not None:
                filas_ok = edited_plan[edited_plan["foco_estrategico"].astype(str).str.strip() != ""]
                focos_u = filas_ok["foco_estrategico"].nunique()
                c1, c2, c3 = st.columns(3)
                c1.metric("🎯 Focos", focos_u)
                c2.metric("📌 Objetivos", len(filas_ok))
                c3.metric("⚡ Actividades", filas_ok["actividad_clave"].astype(str).str.strip().ne("").sum())

            if st.button("💾 GUARDAR PLAN", type="primary", use_container_width=True, key="save_pe"):
                valid = edited_plan[
                    edited_plan["foco_estrategico"].astype(str).str.strip() != ""
                ].to_dict("records")
                if valid:
                    db.save_plan_estrategico(valid, unidad_plan, email)
                    st.success(f"✅ Plan de **{unidad_plan}** guardado ({len(valid)} líneas).")
                    st.balloons()
                else:
                    st.warning("No hay filas con datos.")

    # ══════════════════════════════════════════════════════
    # TAB 2: SEGUIMIENTO ECONÓMICO (Meta vs Real × Mes)
    # ══════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown("### 💰 Seguimiento Económico Mensual")
        st.caption("Proyección presupuestal + Meta vs Real por programa, tal cual tu Excel de seguimiento.")

        unidad_eco = _selector_unidad("eco", rol, unidad)

        if not unidad_eco:
            st.warning("No tienes unidad asignada.")
        else:
            metas_rows = db.get_metas_mensuales(unidad_eco)

            # Columnas del editor
            meta_cols = ["programa", "precio_unitario"]
            for m in MESES:
                ml = m.lower()[:3]
                meta_cols.extend([f"meta_{ml}", f"real_{ml}"])

            col_map_month = {
                "Ene": "ene", "Feb": "feb", "Mar": "mar", "Abr": "abr",
                "May": "may", "Jun": "jun", "Jul": "jul", "Ago": "ago",
                "Sep": "sep", "Oct": "oct", "Nov": "nov", "Dic": "dic",
            }

            if metas_rows:
                df_eco = pd.DataFrame(metas_rows)
                # Ensure all columns exist
                for c in meta_cols:
                    if c not in df_eco.columns:
                        df_eco[c] = 0
                df_eco = df_eco[meta_cols]
            else:
                row_template = {"programa": "", "precio_unitario": 0.0}
                for m in MESES:
                    ml = col_map_month[m]
                    row_template[f"meta_{ml}"] = 0
                    row_template[f"real_{ml}"] = 0
                df_eco = pd.DataFrame([row_template.copy() for _ in range(2)])

            # Ensure numeric
            for c in df_eco.columns:
                if c != "programa":
                    df_eco[c] = pd.to_numeric(df_eco[c], errors="coerce").fillna(0)

            # Column config
            eco_config = {
                "programa": st.column_config.TextColumn(
                    "📚 Programa", width="medium",
                    help="Ej: Little Speakers, Oratoria, Verano, etc.",
                ),
                "precio_unitario": st.column_config.NumberColumn(
                    "💵 Precio Unit.", format="S/ %.0f", width="small",
                    help="Precio estándar por inscrito/servicio",
                ),
            }
            for m in MESES:
                ml = col_map_month[m]
                eco_config[f"meta_{ml}"] = st.column_config.NumberColumn(
                    f"🎯 {m}", min_value=0, width="small",
                    help=f"Meta inscritos/clientes {m}",
                )
                eco_config[f"real_{ml}"] = st.column_config.NumberColumn(
                    f"✅ {m}", min_value=0, width="small",
                    help=f"Real logrado {m}",
                )

            st.markdown("##### Metas y Resultados por Mes (inscritos/clientes)")
            edited_eco = st.data_editor(
                df_eco, column_config=eco_config, num_rows="dynamic",
                use_container_width=True, hide_index=True,
                key=f"eco_{unidad_eco}",
            )

            # ── Cálculos automáticos (Pandas) ──
            st.markdown("---")
            if edited_eco is not None and len(edited_eco) > 0:
                for c in edited_eco.columns:
                    if c != "programa":
                        edited_eco[c] = pd.to_numeric(edited_eco[c], errors="coerce").fillna(0)

                progs_validos = edited_eco[edited_eco["programa"].astype(str).str.strip() != ""]

                if len(progs_validos) > 0:
                    # Proyección Presupuestal por programa
                    st.markdown("##### 📊 Proyección Presupuestal Automática")
                    resumen_data = []
                    for _, row in progs_validos.iterrows():
                        prog = row["programa"]
                        precio = row["precio_unitario"]
                        meta_total = sum(row[f"meta_{col_map_month[m]}"] for m in MESES)
                        real_total = sum(row[f"real_{col_map_month[m]}"] for m in MESES)
                        ingreso_esperado = precio * meta_total
                        ingreso_real = precio * real_total
                        cumplimiento = round((real_total / meta_total) * 100, 1) if meta_total > 0 else 0
                        brecha = meta_total - real_total
                        resumen_data.append({
                            "Programa": prog,
                            "Precio Unit.": precio,
                            "Meta Anual": int(meta_total),
                            "Real Acum.": int(real_total),
                            "Brecha": int(brecha),
                            "% Cumplim.": cumplimiento,
                            "Ingreso Esperado": ingreso_esperado,
                            "Ingreso Real": ingreso_real,
                        })

                    df_resumen = pd.DataFrame(resumen_data)

                    st.dataframe(
                        df_resumen.style.format({
                            "Precio Unit.": "S/ {:.0f}",
                            "Ingreso Esperado": "S/ {:,.0f}",
                            "Ingreso Real": "S/ {:,.0f}",
                            "% Cumplim.": "{:.1f}%",
                        }).applymap(
                            lambda v: "color: green" if isinstance(v, (int, float)) and v >= 80 else
                                      "color: orange" if isinstance(v, (int, float)) and v >= 50 else
                                      "color: red" if isinstance(v, (int, float)) and v > 0 else "",
                            subset=["% Cumplim."]
                        ),
                        use_container_width=True, hide_index=True,
                    )

                    # Totales globales
                    total_meta = int(df_resumen["Meta Anual"].sum())
                    total_real = int(df_resumen["Real Acum."].sum())
                    total_ie = df_resumen["Ingreso Esperado"].sum()
                    total_ir = df_resumen["Ingreso Real"].sum()
                    pct_global = round((total_real / total_meta) * 100, 1) if total_meta > 0 else 0

                    st.markdown("##### 🏦 Totales")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("🎯 Meta Total", f"{total_meta:,}")
                    c2.metric("✅ Real Total", f"{total_real:,}")
                    c3.metric("📊 Cumplimiento", f"{pct_global}%")
                    c4.metric("💰 Ing. Esperado", f"S/ {total_ie:,.0f}")
                    c5.metric("💵 Ing. Real", f"S/ {total_ir:,.0f}")

                    if total_meta > 0:
                        st.progress(min(pct_global / 100, 1.0),
                                    text=f"Avance global: {pct_global}%")

            st.markdown("")
            if st.button("💾 GUARDAR SEGUIMIENTO", type="primary", use_container_width=True, key="save_eco"):
                valid_eco = edited_eco[
                    edited_eco["programa"].astype(str).str.strip() != ""
                ].to_dict("records")
                if valid_eco:
                    db.save_metas_mensuales(valid_eco, unidad_eco)
                    st.success(f"✅ Seguimiento de **{unidad_eco}** guardado ({len(valid_eco)} programas).")
                    st.balloons()
                else:
                    st.warning("No hay programas con datos.")

    # ══════════════════════════════════════════════════════
    # TAB 3: SPRINT OPERATIVO (Tareas con avance)
    # ══════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown("### 🏃 Sprint Operativo")
        st.caption("Gestión de tareas con responsable, estatus y barra de avance.")

        unidad_sprint = _selector_unidad("sprint", rol, unidad)

        if not unidad_sprint:
            st.warning("No tienes unidad asignada.")
        else:
            focos_opciones = db.get_focos_unicos(unidad_sprint)
            if not focos_opciones:
                focos_opciones = ["General"]

            sprint_rows = db.get_sprints(unidad_sprint)
            cols_sprint = ["foco_relacionado", "tarea", "responsable",
                           "fecha_limite", "estatus", "avance"]

            if sprint_rows:
                df_sp = pd.DataFrame(sprint_rows)[cols_sprint]
            else:
                df_sp = pd.DataFrame([{
                    "foco_relacionado": focos_opciones[0],
                    "tarea": "", "responsable": "",
                    "fecha_limite": "", "estatus": "Pendiente", "avance": 0
                } for _ in range(3)])

            df_sp["avance"] = pd.to_numeric(df_sp["avance"], errors="coerce").fillna(0).astype(int)

            sprint_config = {
                "foco_relacionado": st.column_config.SelectboxColumn(
                    "🎯 Foco", options=focos_opciones + ["General"], width="medium",
                ),
                "tarea": st.column_config.TextColumn("📋 Tarea", width="large"),
                "responsable": st.column_config.TextColumn("👤 Responsable", width="small"),
                "fecha_limite": st.column_config.TextColumn("📅 Fecha Límite", width="small"),
                "estatus": st.column_config.SelectboxColumn(
                    "📌 Estatus", options=["Pendiente", "En Proceso", "Terminado"],
                    width="small",
                ),
                "avance": st.column_config.ProgressColumn(
                    "📊 Avance", min_value=0, max_value=100, format="%d%%",
                ),
            }

            edited_sp = st.data_editor(
                df_sp, column_config=sprint_config, num_rows="dynamic",
                use_container_width=True, hide_index=True,
                key=f"sp_{unidad_sprint}",
            )

            # Resumen
            st.markdown("---")
            if edited_sp is not None and len(edited_sp) > 0:
                tareas_ok = edited_sp[edited_sp["tarea"].astype(str).str.strip() != ""]
                total = len(tareas_ok)
                term = len(tareas_ok[tareas_ok["estatus"] == "Terminado"])
                proc = len(tareas_ok[tareas_ok["estatus"] == "En Proceso"])
                pend = len(tareas_ok[tareas_ok["estatus"] == "Pendiente"])
                avance_prom = int(tareas_ok["avance"].mean()) if total > 0 else 0

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("📋 Total", total)
                c2.metric("✅ Terminadas", term)
                c3.metric("🟡 En Proceso", proc)
                c4.metric("⬜ Pendientes", pend)
                c5.metric("📊 Avance", f"{avance_prom}%")

                if total > 0:
                    st.progress(term / total, text=f"{term}/{total} completadas")

            st.markdown("")
            if st.button("💾 ACTUALIZAR SPRINT", type="primary", use_container_width=True, key="save_sp"):
                valid_sp = edited_sp[
                    edited_sp["tarea"].astype(str).str.strip() != ""
                ].to_dict("records")
                if not valid_sp:
                    st.warning("No hay tareas para guardar.")
                else:
                    old_map = {s["tarea"]: s["estatus"] for s in sprint_rows} if sprint_rows else {}
                    nuevas_completadas = 0
                    for s in valid_sp:
                        if int(s.get("avance", 0)) >= 100:
                            s["estatus"] = "Terminado"
                        old_st = old_map.get(s.get("tarea", ""), "Pendiente")
                        if s["estatus"] == "Terminado" and old_st != "Terminado":
                            nuevas_completadas += 1

                    db.save_sprints(valid_sp, unidad_sprint)

                    if nuevas_completadas > 0:
                        st.balloons()
                        pts = nuevas_completadas * 15
                        st.success(
                            f"🎉 ¡{nuevas_completadas} tarea{'s' if nuevas_completadas > 1 else ''} "
                            f"completada{'s' if nuevas_completadas > 1 else ''}! +{pts} puntos."
                        )
                        try:
                            db.add_puntos(email, pts, "Sprint",
                                          f"{nuevas_completadas} tarea(s) en {unidad_sprint}")
                        except:
                            pass
                    else:
                        st.success(f"✅ Sprint de **{unidad_sprint}** actualizado ({len(valid_sp)} tareas).")
