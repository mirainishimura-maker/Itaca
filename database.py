"""
Ítaca OS 2.0 - Base de Datos (Turso / SQLite)
Todas las tablas, seed data, y operaciones CRUD

Conexión:
  - Si TURSO_DATABASE_URL está definida → conecta a Turso Cloud
  - Si no → usa SQLite local (data/itaca.db) como fallback para desarrollo

Optimización:
  - Conexión singleton (no se reconecta en cada operación)
  - sync() solo después de escrituras, no en cada lectura
"""
import json, os, threading
from datetime import datetime, timedelta, date
from contextlib import contextmanager

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_THIS_DIR, "data", "itaca.db")

# ── Detectar si usamos Turso o SQLite local ──
TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")
USE_TURSO = bool(TURSO_URL)

if USE_TURSO:
    import libsql_experimental as libsql
else:
    import sqlite3

# ── Conexión singleton (se reutiliza en toda la app) ──
_conn = None
_lock = threading.Lock()

# ── IMPORTACIÓN DE SEGURIDAD PARA CONTRASEÑAS ──
from werkzeug.security import generate_password_hash, check_password_hash

def _get_connection():
    """Obtiene o crea la conexión singleton."""
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is not None:
            return _conn
        if USE_TURSO:
            _conn = libsql.connect("itaca-replica.db", sync_url=TURSO_URL, auth_token=TURSO_TOKEN)
            _conn.sync()
        else:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _conn


class _Row(dict):
    """
    Dict que también soporta acceso por índice numérico: row[0], row[1], etc.
    Esto mantiene compatibilidad con código existente que usa fetchone()[0]
    para queries como SELECT COUNT(*).
    """
    def __init__(self, cols, values):
        super().__init__(zip(cols, values))
        self._values = list(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class _DictCursor:
    """
    Wrapper que convierte las filas de cualquier cursor (sqlite3 o libsql)
    en _Row — accesible por nombre de columna Y por índice numérico.
    """
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        if params:
            self._cursor = self._conn.execute(sql, params)
        else:
            self._cursor = self._conn.execute(sql)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cursor.description]
        return _Row(cols, row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cursor.description]
        return [_Row(cols, r) for r in rows]


class _DbWrapper:
    """
    Proxy alrededor de la conexión raw que:
    - Para SELECT → usa _DictCursor y devuelve dicts (sin sync)
    - Para INSERT/UPDATE/DELETE → delega directo + marca escritura
    - sync() solo al hacer commit después de escrituras
    """
    def __init__(self, conn):
        self._conn = conn
        self._dict = _DictCursor(conn)
        self._has_writes = False

    def execute(self, sql, params=None):
        sql_upper = sql.strip().upper()
        is_read = sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")
        if is_read:
            return self._dict.execute(sql, params)
        self._has_writes = True
        if params:
            return self._conn.execute(sql, params)
        return self._conn.execute(sql)

    def executescript(self, sql):
        """Ejecutar múltiples sentencias."""
        self._has_writes = True
        if USE_TURSO:
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._conn.execute(stmt)
        else:
            self._conn.executescript(sql)

    def commit(self):
        self._conn.commit()
        # Solo sincronizar con Turso si hubo escrituras (gran ahorro de tiempo)
        if USE_TURSO and self._has_writes:
            self._conn.sync()
            self._has_writes = False


@contextmanager
def get_db():
    conn = _get_connection()
    wrapper = _DbWrapper(conn)
    try:
        yield wrapper
        wrapper.commit()
    except Exception:
        raise


def dict_row(row):
    """Compatibilidad — ahora las filas ya son dicts, pero por seguridad."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)

def dict_rows(rows):
    if not rows:
        return []
    if rows and isinstance(rows[0], dict):
        return rows
    return [dict(r) for r in rows]

# ═══════════════════════════════════════════
# CREAR TABLAS
# ═══════════════════════════════════════════
_db_initialized = False

def init_db():
    global _db_initialized
    if _db_initialized:
        return
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            email TEXT PRIMARY KEY, nombre TEXT, rol TEXT DEFAULT 'Colaborador',
            estado TEXT DEFAULT 'Activo', unidad TEXT, email_lider TEXT,
            fecha_registro TEXT, ultimo_acceso TEXT,
            password TEXT DEFAULT 'Itaca2026!'
        );
        CREATE TABLE IF NOT EXISTS identidad (
            email TEXT PRIMARY KEY, nombre TEXT, foto_url TEXT, puesto TEXT,
            fecha_ingreso TEXT, rol TEXT, unidad TEXT, estado TEXT DEFAULT 'Activo',
            arquetipo_disc TEXT, arquetipo_secundario TEXT,
            disc_d INTEGER DEFAULT 0, disc_i INTEGER DEFAULT 0,
            disc_s INTEGER DEFAULT 0, disc_c INTEGER DEFAULT 0,
            meta_trascendente TEXT, frase_personal TEXT, limitantes TEXT,
            fortalezas TEXT, progreso_meta INTEGER DEFAULT 0, telefono TEXT,
            email_lider TEXT, fecha_actualizacion TEXT,
            color_favorito TEXT DEFAULT '#26C6DA',
            dark_mode INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS metas (
            meta_id TEXT PRIMARY KEY, email TEXT, tipo TEXT, periodo TEXT,
            objetivo TEXT, kr1 TEXT, kr2 TEXT, kr3 TEXT,
            progreso INTEGER DEFAULT 0, estado TEXT DEFAULT 'Pendiente',
            fecha_creacion TEXT, fecha_limite TEXT
        );
        CREATE TABLE IF NOT EXISTS checkins (
            checkin_id TEXT PRIMARY KEY, email TEXT, estado_general TEXT,
            nivel_estres INTEGER, area_preocupacion TEXT, etiquetas TEXT,
            comentario TEXT, fecha TEXT, semana TEXT, alerta_enviada INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS faros (
            faro_id TEXT PRIMARY KEY, email_emisor TEXT, nombre_emisor TEXT,
            email_receptor TEXT, nombre_receptor TEXT, tipo_faro TEXT,
            pilar TEXT, animal TEXT, mensaje TEXT, foto_url TEXT,
            fecha_envio TEXT, estado TEXT DEFAULT 'Pendiente',
            email_aprobador TEXT, fecha_aprobacion TEXT,
            celebraciones INTEGER DEFAULT 0, visible INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS notificaciones (
            notif_id TEXT PRIMARY KEY, email_dest TEXT, tipo TEXT,
            titulo TEXT, mensaje TEXT, fecha TEXT,
            leida INTEGER DEFAULT 0, prioridad TEXT DEFAULT 'Media'
        );
        CREATE TABLE IF NOT EXISTS logros (
            logro_id TEXT PRIMARY KEY, email TEXT, badge_id TEXT,
            nombre_badge TEXT, descripcion TEXT, puntos INTEGER,
            categoria TEXT, fecha TEXT, icono TEXT
        );
        CREATE TABLE IF NOT EXISTS hexagono (
            eval_id TEXT PRIMARY KEY, email TEXT, periodo TEXT, fecha TEXT,
            vision INTEGER, planificacion INTEGER, encaje INTEGER,
            entrenamiento INTEGER, evaluacion_mejora INTEGER, reconocimiento INTEGER,
            promedio REAL, reflexion TEXT, dim_baja TEXT, dim_alta TEXT
        );
        CREATE TABLE IF NOT EXISTS journal (
            journal_id TEXT PRIMARY KEY, email TEXT, fecha TEXT,
            emociones TEXT, intensidad INTEGER, trigger_text TEXT,
            pensamiento TEXT, reflexion TEXT, estrategia TEXT,
            efectividad INTEGER, contexto TEXT, dia_semana TEXT, hora_dia TEXT
        );
        CREATE TABLE IF NOT EXISTS brujula_eval (
            brujula_id TEXT PRIMARY KEY, email TEXT, periodo TEXT, fecha TEXT,
            autoconocimiento INTEGER, autorregulacion INTEGER, motivacion INTEGER,
            empatia INTEGER, habilidades_sociales INTEGER,
            promedio REAL, comp_baja TEXT, comp_alta TEXT, reflexion TEXT,
            ejercicios_mes INTEGER DEFAULT 0, journal_mes INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS ejercicios_log (
            log_id TEXT PRIMARY KEY, email TEXT, ejercicio_id TEXT,
            fecha TEXT, duracion_real INTEGER, efectividad INTEGER,
            estado_antes TEXT, estado_despues TEXT, notas TEXT, competencia TEXT
        );
        CREATE TABLE IF NOT EXISTS planes_accion (
            plan_id TEXT PRIMARY KEY, email TEXT, periodo TEXT, dimension TEXT,
            puntaje_actual INTEGER, puntaje_meta INTEGER,
            accion1 TEXT, accion2 TEXT, accion3 TEXT,
            fecha_creacion TEXT, fecha_limite TEXT, estado TEXT DEFAULT 'Pendiente'
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            log_id TEXT PRIMARY KEY, email TEXT, accion TEXT,
            detalle TEXT, fecha TEXT, modulo TEXT
        );
        CREATE TABLE IF NOT EXISTS focos (
            foco_id TEXT PRIMARY KEY, email_creador TEXT, unidad TEXT,
            nombre TEXT, descripcion TEXT, periodo TEXT,
            progreso INTEGER DEFAULT 0, estado TEXT DEFAULT 'En Progreso',
            fecha_creacion TEXT, fecha_limite TEXT, orden INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS krs (
            kr_id TEXT PRIMARY KEY, foco_id TEXT, nombre TEXT,
            meta_valor REAL, valor_actual REAL DEFAULT 0, unidad_medida TEXT,
            progreso INTEGER DEFAULT 0, estado TEXT DEFAULT 'En Progreso',
            periodicidad TEXT DEFAULT 'Mensual',
            fecha_creacion TEXT, fecha_limite TEXT,
            FOREIGN KEY (foco_id) REFERENCES focos(foco_id)
        );
        CREATE TABLE IF NOT EXISTS tareas (
            tarea_id TEXT PRIMARY KEY, kr_id TEXT, foco_id TEXT,
            titulo TEXT, descripcion TEXT,
            email_responsable TEXT, nombre_responsable TEXT,
            fecha_inicio TEXT, fecha_limite TEXT, fecha_completada TEXT,
            estado TEXT DEFAULT 'Pendiente', prioridad TEXT DEFAULT 'Media',
            progreso INTEGER DEFAULT 0, notas TEXT,
            fecha_creacion TEXT, ultimo_cambio TEXT, cambiado_por TEXT,
            FOREIGN KEY (kr_id) REFERENCES krs(kr_id),
            FOREIGN KEY (foco_id) REFERENCES focos(foco_id)
        );
        CREATE TABLE IF NOT EXISTS historial_cambios (
            cambio_id TEXT PRIMARY KEY, entidad TEXT, entidad_id TEXT,
            campo TEXT, valor_anterior TEXT, valor_nuevo TEXT,
            email_autor TEXT, nombre_autor TEXT, fecha TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_360 (
            eval_id TEXT PRIMARY KEY, email_evaluado TEXT, email_evaluador TEXT,
            periodo TEXT, fecha TEXT, anonimo INTEGER DEFAULT 1,
            vision INTEGER, planificacion INTEGER, encaje INTEGER,
            entrenamiento INTEGER, evaluacion_mejora INTEGER, reconocimiento INTEGER,
            promedio REAL, comentario TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_desempeno (
            eval_id TEXT PRIMARY KEY, email TEXT, periodo TEXT, fecha TEXT,
            evaluador_email TEXT, evaluador_nombre TEXT,
            cumplimiento_metas INTEGER, calidad_trabajo INTEGER,
            trabajo_equipo INTEGER, comunicacion INTEGER, iniciativa INTEGER,
            promedio REAL, fortalezas TEXT, areas_mejora TEXT,
            plan_desarrollo TEXT, comentario_general TEXT
        );
        CREATE TABLE IF NOT EXISTS capacitaciones (
            cap_id TEXT PRIMARY KEY, email TEXT, nombre_cap TEXT,
            tipo TEXT, horas INTEGER, fecha TEXT, certificado INTEGER DEFAULT 0,
            institucion TEXT, notas TEXT
        );

        -- ═══════════════════════════════════════════
        -- NUEVAS TABLAS v2.0 (HRIS + CRM + Finanzas)
        -- ═══════════════════════════════════════════

        -- Perfiles DISC ideales por puesto (semáforo de encaje)
        CREATE TABLE IF NOT EXISTS puestos_perfiles (
            puesto_id TEXT PRIMARY KEY,
            nombre_puesto TEXT,
            disc_ideal_principal TEXT,
            disc_ideal_secundario TEXT,
            unidad TEXT,
            descripcion TEXT
        );

        -- Flujo financiero (La Bóveda)
        CREATE TABLE IF NOT EXISTS finanzas_flujo (
            flujo_id TEXT PRIMARY KEY,
            unidad TEXT,
            tipo TEXT,
            categoria TEXT,
            monto REAL,
            fecha TEXT,
            campana TEXT,
            descripcion TEXT,
            registrado_por TEXT,
            fecha_registro TEXT
        );

        -- CRM Leads (El Puerto)
        CREATE TABLE IF NOT EXISTS crm_leads (
            lead_id TEXT PRIMARY KEY,
            telefono TEXT,
            nombre_apoderado TEXT,
            nombre_nino TEXT,
            edad INTEGER,
            ciudad TEXT,
            origen TEXT,
            precalificacion TEXT,
            estado TEXT DEFAULT 'Nuevo',
            unidad TEXT,
            notas TEXT,
            email_asesor TEXT,
            fecha_creacion TEXT,
            fecha_actualizacion TEXT
        );

        -- Cuotas de venta (auto-generadas al inscribir lead)
        CREATE TABLE IF NOT EXISTS ventas_cuotas (
            cuota_id TEXT PRIMARY KEY,
            lead_id TEXT,
            numero_cuota INTEGER,
            monto_esperado REAL,
            monto_pagado REAL DEFAULT 0,
            fecha_vencimiento TEXT,
            fecha_pago TEXT,
            estado TEXT DEFAULT 'Pendiente',
            FOREIGN KEY (lead_id) REFERENCES crm_leads(lead_id)
        );

        -- Plan Estratégico por Unidad (estructura real de los PE Excel)
        CREATE TABLE IF NOT EXISTS planes_estrategicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidad TEXT,
            foco_estrategico TEXT,
            objetivo TEXT,
            kr TEXT,
            actividad_clave TEXT,
            fecha_creacion TEXT,
            creado_por TEXT
        );

        -- Seguimiento Mensual de Metas Económicas por Unidad
        CREATE TABLE IF NOT EXISTS metas_mensuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidad TEXT,
            programa TEXT,
            precio_unitario REAL DEFAULT 0,
            meta_ene INTEGER DEFAULT 0, real_ene INTEGER DEFAULT 0,
            meta_feb INTEGER DEFAULT 0, real_feb INTEGER DEFAULT 0,
            meta_mar INTEGER DEFAULT 0, real_mar INTEGER DEFAULT 0,
            meta_abr INTEGER DEFAULT 0, real_abr INTEGER DEFAULT 0,
            meta_may INTEGER DEFAULT 0, real_may INTEGER DEFAULT 0,
            meta_jun INTEGER DEFAULT 0, real_jun INTEGER DEFAULT 0,
            meta_jul INTEGER DEFAULT 0, real_jul INTEGER DEFAULT 0,
            meta_ago INTEGER DEFAULT 0, real_ago INTEGER DEFAULT 0,
            meta_sep INTEGER DEFAULT 0, real_sep INTEGER DEFAULT 0,
            meta_oct INTEGER DEFAULT 0, real_oct INTEGER DEFAULT 0,
            meta_nov INTEGER DEFAULT 0, real_nov INTEGER DEFAULT 0,
            meta_dic INTEGER DEFAULT 0, real_dic INTEGER DEFAULT 0
        );

        -- Seguimiento de Sprints (Tareas operativas por unidad)
        CREATE TABLE IF NOT EXISTS seguimiento_sprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidad TEXT, foco_relacionado TEXT, tarea TEXT,
            responsable TEXT, fecha_limite TEXT,
            estatus TEXT DEFAULT 'Pendiente', avance INTEGER DEFAULT 0
        );

        -- ── ÍTACA PLAY ──
        CREATE TABLE IF NOT EXISTS itaca_play_cursos (
            curso_id TEXT PRIMARY KEY, titulo TEXT NOT NULL,
            descripcion TEXT, youtube_url TEXT NOT NULL, youtube_id TEXT,
            categoria TEXT DEFAULT 'General', dificultad TEXT DEFAULT 'Básico',
            puntos INTEGER DEFAULT 50, badge_nombre TEXT, badge_icono TEXT DEFAULT '🎬',
            palabra_clave TEXT NOT NULL, pregunta TEXT NOT NULL,
            opcion_a TEXT NOT NULL, opcion_b TEXT NOT NULL,
            opcion_c TEXT NOT NULL, opcion_d TEXT NOT NULL,
            respuesta_correcta TEXT NOT NULL,
            activo INTEGER DEFAULT 1, orden INTEGER DEFAULT 0,
            creado_por TEXT, fecha_creacion TEXT, vistas INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS itaca_play_intentos (
            intento_id TEXT PRIMARY KEY, email TEXT NOT NULL, curso_id TEXT NOT NULL,
            palabra_ingresada TEXT, palabra_correcta INTEGER DEFAULT 0,
            respuesta_dada TEXT, respuesta_correcta INTEGER DEFAULT 0,
            aprobado INTEGER DEFAULT 0, puntos_ganados INTEGER DEFAULT 0,
            fecha TEXT, intento_num INTEGER DEFAULT 1
        );

        -- ── EVALUACIÓN 360° v2 ──
        CREATE TABLE IF NOT EXISTS periodos_360 (
            periodo_id TEXT PRIMARY KEY, nombre TEXT NOT NULL,
            trimestre TEXT, fecha_inicio TEXT, fecha_fin TEXT,
            activo INTEGER DEFAULT 1, creado_por TEXT, fecha_creacion TEXT
        );
        CREATE TABLE IF NOT EXISTS eval_360_v2 (
            eval_id TEXT PRIMARY KEY, periodo_id TEXT,
            email_evaluado TEXT, email_evaluador TEXT, unidad TEXT, fecha TEXT,
            pilar_itactividad INTEGER DEFAULT 0, pilar_mas1 INTEGER DEFAULT 0,
            pilar_confianza INTEGER DEFAULT 0,
            hex_vision INTEGER DEFAULT 0, hex_planificacion INTEGER DEFAULT 0,
            hex_encaje INTEGER DEFAULT 0, hex_entrenamiento INTEGER DEFAULT 0,
            hex_evaluacion INTEGER DEFAULT 0, hex_reconocimiento INTEGER DEFAULT 0,
            ie_autoconocimiento INTEGER DEFAULT 0, ie_autorregulacion INTEGER DEFAULT 0,
            ie_motivacion INTEGER DEFAULT 0, ie_empatia INTEGER DEFAULT 0,
            ie_habilidades_sociales INTEGER DEFAULT 0,
            fortaleza_principal TEXT, area_mejora TEXT, comentario TEXT,
            prom_pilares REAL DEFAULT 0, prom_hexagono REAL DEFAULT 0,
            prom_ie REAL DEFAULT 0, prom_total REAL DEFAULT 0,
            es_autoevaluacion INTEGER DEFAULT 0
        );

        -- ── CAPACITACIONES EXTERNAS ──
        CREATE TABLE IF NOT EXISTS capacitaciones_ext (
            cap_id TEXT PRIMARY KEY, email TEXT NOT NULL,
            nombre_cap TEXT NOT NULL, tipo TEXT, institucion TEXT,
            horas INTEGER DEFAULT 0, fecha TEXT,
            certificado INTEGER DEFAULT 0, costo_empresa INTEGER DEFAULT 0,
            notas TEXT, estado TEXT DEFAULT 'Pendiente',
            email_aprobador TEXT, fecha_aprobacion TEXT,
            motivo_rechazo TEXT, puntos_otorgados INTEGER DEFAULT 0,
            fecha_registro TEXT
        );

        """)
    seed_data()
    _db_initialized = True

# ═══════════════════════════════════════════
# SEED DATA
# ═══════════════════════════════════════════
def seed_data():
    with get_db() as db:
        c = db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if c > 0:
            return
        now = datetime.now().isoformat()
        
        # Generamos el hash para la contraseña por defecto de los usuarios semilla
        default_hash = generate_password_hash('Itaca2026!')

        # ═══════════════════════════════════════════════════════
        # 90 COLABORADORES REALES DE ÍTACA HUB
        # ═══════════════════════════════════════════════════════
        users = [
            ("oscar.bereche@itaca.com","Oscar Sebastián García Bereche","Colaborador","Activo","321 SHOW","francisco.orellano@itaca.com","Videógrafo","974585296","2021-03-15"),
            ("francisco.orellano@itaca.com","Francisco Javier Muñoz Orellano","Líder","Activo","321 SHOW",None,"Socio","969680096","2021-09-10"),
            ("max.jimenez@itaca.com","Max Angel Chero Jiménez","Líder","Activo","ARTAMAX",None,"Socio / Gerente","973355562","2025-04-01"),
            ("esther.ortiz@itaca.com","Esther Abigail Ayala Ortiz","Colaborador","Activo","ARTAMAX","max.jimenez@itaca.com","Docente","917827155","2025-08-01"),
            ("anthonella.ojeda@itaca.com","Anthonella Abigail Ojeda Ojeda","Colaborador","Activo","ARTAMAX","max.jimenez@itaca.com","Asistente Gerencial","929596616","2025-10-13"),
            ("jorge.romero@itaca.com","Jorge Augusto Lazarte Romero","Líder","Activo","B&J ASESORES",None,"Socio / Director","959300115","2022-01-01"),
            ("keiko.cordova@itaca.com","Keiko Danitza Ramos Córdova","Colaborador","Activo","B&J ASESORES","jorge.romero@itaca.com","Asistente Contable","962807609","2023-01-01"),
            ("sara.miranda@itaca.com","Sara Belen Romero Miranda","Colaborador","Activo","B&J ASESORES","jorge.romero@itaca.com","Auxiliar Contable","933673617","2024-10-01"),
            ("nestor.hernandez@itaca.com","Néstor Javier Chanduvi Hernández","Colaborador","Activo","CLUB DE ARTE","luis.sosa@itaca.com","Docente","913069605","2020-01-06"),
            ("emma.mendoza@itaca.com","Emma Elizabeth Curipuma Mendoza","Colaborador","Activo","CLUB DE ARTE","luis.sosa@itaca.com","Docente","999138246","2023-01-01"),
            ("ana.sacchetti@itaca.com","Ana Luz López Sacchetti","Colaborador","Activo","CLUB DE ARTE","luis.sosa@itaca.com","Docente","940176075","2023-12-15"),
            ("melani.oscco@itaca.com","Melani Ramirez Oscco","Colaborador","Activo","CLUB DE ARTE","luis.sosa@itaca.com","Docente","969533354","2025-04-01"),
            ("pamela.silvera@itaca.com","Pamela Victoria Revilla Silvera","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","980715859","2023-08-31"),
            ("ayvi.huaman@itaca.com","Ayvi Yamillette Reyes Huamán","Coordinador","Activo","CONVER LIMA",None,"Coordinadora","960711603","2024-10-21"),
            ("katia.avila@itaca.com","Katia Gianelly Briones Avila","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","989018532","2025-03-15"),
            ("meriveth.garcia@itaca.com","Meriveth Ay-Ling Rojas García","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","978361147","2025-04-01"),
            ("arlette.mestanza@itaca.com","Arlette Solange Santibañez Mestanza","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","998732273","2025-04-01"),
            ("paolo.camacho@itaca.com","Paolo Fabio Ronceros Camacho","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","936809795","2025-05-05"),
            ("camila.gamarra@itaca.com","Camila Fiorella Alvarez Gamarra","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","961891335","2025-06-01"),
            ("cristel.motta@itaca.com","Cristel Fiorella Ríos Motta","Colaborador","Activo","CONVER LIMA","ayvi.huaman@itaca.com","Psicólogo","937091962","2025-06-01"),
            ("grecia.elera@itaca.com","Grecia Palacios Elera","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicóloga","962686617","2023-10-11"),
            ("alejandro.ortiz@itaca.com","Alejandro Chung Ortiz","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicólogo","968824862","2024-08-28"),
            ("joyce.mendoza@itaca.com","Joyce Calle Mendoza","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicóloga","995047598","2024-09-06"),
            ("yazmin.alvarado@itaca.com","Yazmin Fiorella Castillo Alvarado","Coordinador","Activo","CONVER PIURA",None,"Coordinadora","962840126","2025-01-02"),
            ("andrea.chirito@itaca.com","Andrea Elizabeth Cabellos Chirito","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicóloga","969214648","2025-01-30"),
            ("angi.vilela@itaca.com","Angi Lizeth Requena Vilela","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicóloga","958174225","2025-01-30"),
            ("maximo.espinoza@itaca.com","Maximo Jr. Aldana Espinoza","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicólogo","955667968","2025-06-16"),
            ("sofia.godinez@itaca.com","Sofía Isabel Ferreyra Godinez","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicóloga","991130790","2025-06-18"),
            ("inori.coronado@itaca.com","Inori Nishimura Coronado","Colaborador","Activo","CONVER PIURA","yazmin.alvarado@itaca.com","Psicóloga","970632478","2025-09-01"),
            ("maria.garcia@itaca.com","María Fernanda Vásquez García","Líder","Activo","ECO",None,"Directora y entrenadora","999642183","2025-04-02"),
            ("johana.sanchez@itaca.com","Johana Andrea Díaz Sanchez","Colaborador","Activo","ECO","maria.garcia@itaca.com","Docente","991403599","2025-08-01"),
            ("alvaro.gallo@itaca.com","Alvaro Alonso Gallo","Colaborador","Activo","ECO","maria.garcia@itaca.com","Docente","965788767","2025-08-01"),
            ("harold.arevalo@itaca.com","Harold Serhio Quinde Arévalo","Líder","Activo","ITACA EDUCACIÓN",None,"Entrenador / Director","901791803","2024-01-01"),
            ("maria.arechaga@itaca.com","María Carla Roxany Arrese Arechaga","Colaborador","Activo","ITACA EDUCACIÓN","harold.arevalo@itaca.com","Entrenadora","963777646","2024-01-01"),
            ("jadek.renteria@itaca.com","Jadek Renteria","Colaborador","Activo","ITACA EDUCACIÓN","harold.arevalo@itaca.com","Practicante","967384002","2025-07-14"),
            ("brandon.cordova@itaca.com","Brandon Skiev Soto Cordova","Líder","Activo","ITACA HUB",None,"Socio Ítaca Hub","951657082","2014-09-01"),
            ("brian.olaya@itaca.com","Brian Stefano Savitzky Olaya","Líder","Activo","ITACA HUB","brandon.cordova@itaca.com","Socio Ítaca Hub","944438905","2014-09-01"),
            ("mattias.savitzky@itaca.com","Mattias Mattos Savitzky","Coordinador","Activo","ITACA HUB","brandon.cordova@itaca.com","Coordinador administrativo","951201565","2022-01-06"),
            ("gabriel.savitzky@itaca.com","Gabriel Mattos Savitzky","Líder","Activo","ITACA HUB","brandon.cordova@itaca.com","Director comercial","922215252","2022-04-16"),
            ("astrid.vivas@itaca.com","Astrid Adanai Ramos Vivas","Colaborador","Activo","ITACA HUB","brandon.cordova@itaca.com","Asistente Gerencial","957552519","2023-04-13"),
            ("jose.chuquicondor@itaca.com","José Piero Alexandro Zapata Chuquicondor","Colaborador","Activo","ITACA HUB","brandon.cordova@itaca.com","Procesos administrativos","920129548","2023-12-11"),
            ("piero.garcia@itaca.com","Piero Huertas García","Colaborador","Activo","ITACA HUB","brandon.cordova@itaca.com","Marketing","976216997","2024-03-01"),
            ("virginia.rabanal@itaca.com","Virginia Anaís Robledo Rabanal","Colaborador","Activo","ITACA HUB","brandon.cordova@itaca.com","Asistente Gerencial","918406473","2024-09-01"),
            ("brando.juarez@itaca.com","Brando Augusto Franco Juárez","Colaborador","Activo","ITACA HUB","brandon.cordova@itaca.com","Marketing","947057325","2024-09-01"),
            ("mirai.coronado@itaca.com","Mirai Nishimura Coronado","Admin","Activo","ITACA HUB","brandon.cordova@itaca.com","Gestora de Talento Humano","977668497","2025-01-01"),
            ("monica.rolando@itaca.com","Mónica Alejandra Rodríguez Rolando","Colaborador","Activo","KIDS AREQUIPA","gabriel.savitzky@itaca.com","Entrenadora Kids Arequipa","953850222","2024-08-31"),
            ("axlen.barra@itaca.com","Axlen Nicole Fernández Barra","Colaborador","Activo","KIDS AREQUIPA","gabriel.savitzky@itaca.com","Entrenadora Kids Arequipa","983754707","2024-08-31"),
            ("gabriela.juarez@itaca.com","Gabriela Lucía Rentería Juárez","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Psicóloga","961350844","2019-01-02"),
            ("maria.ramirez@itaca.com","María de los Ángeles Espinoza Ramirez","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenadora Kids","912550185","2024-01-01"),
            ("luana.camacho@itaca.com","Luana Marialé Gallesi Camacho","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Co-entrenadora Kids Lima","913718440","2024-01-12"),
            ("gianela.lopez@itaca.com","Gianela Esther Loardo Lopez","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenadora Kids Lima","964240154","2024-04-12"),
            ("fernanda.cabrera@itaca.com","Fernanda Elizabeth Vizcarra Cabrera","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenadora Kids Lima","980732705","2024-08-30"),
            ("giresse.castillo@itaca.com","Giresse Alexander Bernuy Castillo","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenador Kids Lima","947725759","2024-08-30"),
            ("adriana.alvarado@itaca.com","Adriana Ximena Harumy Díaz Alvarado","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Psicóloga","992837265","2024-08-30"),
            ("jesus.martinez@itaca.com","Jesús Israel Montellanos Martinez","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenador Kids Lima","906837369","2024-08-31"),
            ("diana.aliaga@itaca.com","Diana Susana Cornejo Aliaga","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenadora Kids","963781075","2024-12-13"),
            ("lucia.huambachano@itaca.com","Lucía Alessandra Meza Huambachano","Colaborador","Activo","KIDS LIMA","brando.camacho@itaca.com","Entrenadora Kids Lima","",""),
            ("fransheska.atoche@itaca.com","Fransheska Teresa Saldarriaga Atoche","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids Piura","921988904","2020-07-01"),
            ("taiz.saucedo@itaca.com","Taiz Kasandra Ivonne Martinez Saucedo","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids","994191006","2022-05-14"),
            ("candy.vera@itaca.com","Candy Alisson Huertas Vera","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids","907851180","2023-09-01"),
            ("tatiana.cruz@itaca.com","Tatiana Milene Lachira Cruz","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids Piura","951933777","2024-04-11"),
            ("kristel.chunga@itaca.com","Kristel Rosa Saavedra Chunga","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids","977195668","2024-04-27"),
            ("ana.iman@itaca.com","Ana Lucía Gallardo Imán","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids","938310093","2024-09-01"),
            ("angie.morocho@itaca.com","Angie de los Milagros Salvador Morocho","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids Piura","953348766",""),
            ("victoria.valencia@itaca.com","Victoria María Rodríguez Valencia","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Psicóloga Kids","934637679",""),
            ("luisa.dolly@itaca.com","Luisa María Castillo Dolly","Colaborador","Activo","KIDS PIURA","mattias.savitzky@itaca.com","Entrenadora Kids","903003595",""),
            ("santiago.zambrano@itaca.com","Santiago Sánchez Zambrano","Líder","Activo","MARKETING",None,"Socio Ítaca Marketing","997754433","2020-01-11"),
            ("daniela.collantes@itaca.com","Daniela Fernanda Tocto Collantes","Colaborador","Activo","MARKETING","santiago.zambrano@itaca.com","Project Manager","944822543","2021-04-12"),
            ("edson.pena@itaca.com","Edson Martín Domínguez Peña","Colaborador","Activo","MARKETING","santiago.zambrano@itaca.com","Diseñador gráfico","978379477","2021-06-21"),
            ("jose.lecca@itaca.com","José Joaquín Murillo Lecca","Colaborador","Activo","MARKETING","santiago.zambrano@itaca.com","Entrenador Kids Lima","921168570","2024-01-08"),
            ("maickol.ayala@itaca.com","Maickol Yorvn Saavedra Ayala","Colaborador","Activo","MARKETING","santiago.zambrano@itaca.com","Creador de contenido","986982339","2024-01-12"),
            ("gabriel.querevalu@itaca.com","Gabriel Efraín Chavez Querevalu","Colaborador","Activo","MARKETING","santiago.zambrano@itaca.com","Analista de pauta","962082320","2024-11-04"),
            ("damaris.lupuche@itaca.com","Damaris Nicol Aguilar Lupuche","Colaborador","Activo","MARKETING","santiago.zambrano@itaca.com","Practicante CC","918135940","2024-11-04"),
            ("milagros.socola@itaca.com","Milagros Stephany Espinoza Socola","Colaborador","Activo","PRACTICANTES","mirai.coronado@itaca.com","Practicante Hub","959247793","2025-08-28"),
            ("rodrigo.hurtado@itaca.com","Rodrigo Joaquín Cruz Hurtado","Colaborador","Activo","PRACTICANTES","mirai.coronado@itaca.com","Practicante Marco Legal","961861390","2025-09-22"),
            ("jocelyn.vivas@itaca.com","Jocelyn Aradiel Ramos Vivas","Colaborador","Activo","PRACTICANTES","mirai.coronado@itaca.com","Practicante Editora","920862467","2025-10-01"),
            ("claudia.chuquicondor@itaca.com","Claudia Belén Zapata Chuquicondor","Colaborador","Activo","PRACTICANTES","mirai.coronado@itaca.com","Practicante RH","959143022","2025-12-15"),
            ("luis.sosa@itaca.com","Luis Alberto Chiroque Sosa","Líder","Activo","SOCIOS",None,"Socio Club de Arte y Cultura","943742516","2019-01-01"),
            ("nadia.olaya@itaca.com","Nadia Lissett Savitzky Olaya","Líder","Activo","SOCIOS",None,"Socia Ítaca Hub","978661349","2016-01-01"),
            ("eddie.cespedes@itaca.com","Eddie Raúl Valdiviezo Céspedes","Líder","Activo","SOCIOS",None,"Socio Ítaca Hub","958928102","2017-01-02"),
            ("keila.zegarra@itaca.com","Keila Cornejo Zegarra","Líder","Activo","SOCIOS",None,"Socia Club de Arte","929966010","2019-08-01"),
            ("luciana.calderon@itaca.com","Luciana Rubí Portilla Calderón","Líder","Activo","SOCIOS",None,"Socia Inversionista Kids Piura","991570706","2023-04-01"),
            ("brando.camacho@itaca.com","Brando Alonso Gallesi Camacho","Líder","Activo","SOCIOS",None,"Socio Ítaca Kids Lima","913066690","2023-12-31"),
            ("jesus.andrade@itaca.com","Jesús Andrade","Líder","Activo","SOCIOS",None,"Socio Ítaca Conversemos","954044292",""),
            ("nadia.echevarria@itaca.com","Nadia Susiré Herrera Echevarría","Líder","Activo","SOCIOS",None,"Socia Ítaca Kids Lima","964589249",""),
        ]
        for u in users:
            email, nombre, rol, estado, unidad, email_lider, cargo, cel, ingreso = u
            db.execute("INSERT OR IGNORE INTO usuarios VALUES (?,?,?,?,?,?,?,?,?)",
                (email, nombre, rol, estado, unidad, email_lider, now, now, default_hash))
            db.execute("""INSERT OR IGNORE INTO identidad
                (email,nombre,puesto,rol,unidad,estado,email_lider,telefono,fecha_ingreso,fecha_actualizacion)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (email, nombre, cargo, rol, unidad, estado, email_lider, cel, ingreso, now))
        
        # Algunos check-ins de ejemplo
        for i, email in enumerate(["astrid.vivas@itaca.com","grecia.elera@itaca.com","daniela.collantes@itaca.com"]):
            for w in range(4):
                d = datetime.now() - timedelta(weeks=w)
                estados = ["GENIAL","NORMAL","DIFICIL","NORMAL"]
                estres = [2, 3, 4, 2]
                cid = f"{email}_{d.strftime('%Y-%m-%d')}"
                sem = f"{d.year}-S{d.isocalendar()[1]:02d}"
                db.execute("INSERT OR IGNORE INTO checkins VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (cid, email, estados[w], estres[w], "Trabajo", "Concentrado,Determinado",
                     "", d.isoformat(), sem, 1 if estres[w]>=4 else 0))
        
        # Faros de ejemplo con colaboradores reales
        faros_data = [
            ("astrid.vivas@itaca.com","Astrid Adanai Ramos Vivas","mirai.coronado@itaca.com","Mirai Nishimura Coronado","Faro de Valor","ITACTIVIDAD","Ardilla","Gracias por resolver el tema de contratos sin que nadie te lo pidiera. Eso es ITACTIVIDAD pura."),
            ("grecia.elera@itaca.com","Grecia Palacios Elera","yazmin.alvarado@itaca.com","Yazmin Fiorella Castillo Alvarado","Faro de Aliento","Muro de Confianza","Ganso","Sé que esta semana fue intensa con las consultas. Quiero que sepas que cuentas con todo el equipo."),
            ("daniela.collantes@itaca.com","Daniela Fernanda Tocto Collantes","santiago.zambrano@itaca.com","Santiago Sánchez Zambrano","Faro de Guía","+1 Sí Importa","Castor","Gracias por enseñarme a usar las métricas de pauta. Siempre das la milla extra."),
        ]
        for i, f in enumerate(faros_data):
            fid = f"FARO_{int(datetime.now().timestamp())}{i}"
            d = datetime.now() - timedelta(days=i*3)
            db.execute("INSERT OR IGNORE INTO faros VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fid, f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7], "",
                 d.isoformat(), "Aprobado", "mirai@itaca.com", d.isoformat(), 0, 1))
        
        # Badge de ejemplo
        db.execute("INSERT OR IGNORE INTO logros VALUES (?,?,?,?,?,?,?,?,?)",
            ("LOGRO_pedro_firstfaro", "pedro@itaca.com", "FIRST_FARO", "🔦 Primer Faro",
             "Encendiste tu primer faro", 10, "Cultura", now, "🔦"))

        # Puestos con DISC ideal (para semáforo de encaje Torre de Control)
        puestos_seed = [
            ("PU001","Entrenador Kids","Amarillo","Verde","KIDS","Facilitador de talleres infantiles"),
            ("PU002","Psicólogo","Verde","Azul","CONVER","Atención psicológica"),
            ("PU003","Psicóloga","Verde","Azul","CONVER","Atención psicológica"),
            ("PU004","Socio / Gerente","Rojo","Amarillo","GENERAL","Líder de unidad de negocio"),
            ("PU005","Socio","Rojo","Amarillo","GENERAL","Socio fundador / líder"),
            ("PU006","Diseñador gráfico","Azul","Amarillo","MARKETING","Diseño de piezas gráficas"),
            ("PU007","Asistente Gerencial","Azul","Verde","GENERAL","Soporte administrativo"),
            ("PU008","Project Manager","Rojo","Azul","MARKETING","Gestión de proyectos"),
            ("PU009","Docente","Amarillo","Verde","EDUCACION","Facilitador educativo"),
            ("PU010","Asistente Contable","Azul","Rojo","B&J","Contabilidad"),
            ("PU011","Auxiliar Contable","Azul","Verde","B&J","Soporte contable"),
            ("PU012","Coordinadora","Rojo","Verde","GENERAL","Coordinación de equipo"),
            ("PU013","Creador de contenido","Amarillo","Azul","MARKETING","Contenido digital"),
            ("PU014","Analista de pauta","Azul","Rojo","MARKETING","Análisis de pauta digital"),
            ("PU015","Videógrafo","Amarillo","Azul","321 SHOW","Producción audiovisual"),
            ("PU016","Gestora de Talento Humano","Verde","Rojo","ITACA HUB","GTH / Admin"),
            ("PU017","Practicante","Verde","Amarillo","GENERAL","Prácticas pre-profesionales"),
            ("PU018","Marketing","Amarillo","Rojo","MARKETING","Estrategia de marketing"),
            ("PU019","Entrenadora Kids","Amarillo","Verde","KIDS","Facilitadora de talleres infantiles"),
            ("PU020","Entrenadora Kids Arequipa","Amarillo","Verde","KIDS","Facilitadora Kids Arequipa"),
            ("PU021","Entrenadora Kids Piura","Amarillo","Verde","KIDS","Facilitadora Kids Piura"),
            ("PU022","Entrenador Kids Lima","Amarillo","Verde","KIDS","Facilitador Kids Lima"),
            ("PU023","Entrenadora Kids Lima","Amarillo","Verde","KIDS","Facilitadora Kids Lima"),
            ("PU024","Co-entrenadora Kids Lima","Amarillo","Verde","KIDS","Co-facilitadora Kids Lima"),
            ("PU025","Psicóloga Kids","Verde","Amarillo","KIDS","Atención psicológica infantil"),
            ("PU026","Socio Ítaca Hub","Rojo","Amarillo","ITACA HUB","Socio principal"),
            ("PU027","Director comercial","Rojo","Amarillo","ITACA HUB","Dirección comercial"),
            ("PU028","Coordinador administrativo","Azul","Rojo","ITACA HUB","Coordinación admin"),
            ("PU029","Directora y entrenadora","Rojo","Amarillo","ECO","Dirección + facilitación"),
            ("PU030","Entrenador / Director","Rojo","Amarillo","EDUCACION","Director educativo"),
            ("PU031","Socio / Director","Rojo","Azul","B&J","Dirección B&J"),
            ("PU032","Practicante Hub","Verde","Amarillo","ITACA HUB","Prácticas Hub"),
            ("PU033","Practicante Marco Legal","Azul","Verde","ITACA HUB","Prácticas legales"),
            ("PU034","Practicante Editora","Amarillo","Azul","ITACA HUB","Prácticas edición"),
            ("PU035","Practicante RH","Verde","Azul","ITACA HUB","Prácticas RH"),
            ("PU036","Practicante CC","Amarillo","Verde","MARKETING","Prácticas CC"),
            ("PU037","Procesos administrativos","Azul","Verde","ITACA HUB","Gestión de procesos"),
        ]
        for p in puestos_seed:
            db.execute("INSERT OR IGNORE INTO puestos_perfiles VALUES (?,?,?,?,?,?)", p)


        # ── SEED: Planes Estratégicos (extraídos de Excel reales) ──
        existing_plans = db.execute('SELECT COUNT(*) FROM planes_estrategicos').fetchone()[0]
        if existing_plans == 0:
            plan_seed = [
                ("321 SHOW","ITACA FAN","Convertir a nuestro cliente en FAN de nuestro servicio","NPS Global ≥ 70","Diseño del viaje del fan 3,2,1"),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Convertir a nuestro cliente en FAN de nuestro servicio","Nivel de alineación y claridad del equipo (encuesta interna 1–5) ≥ 4.5","Comunicación y alineación cultural del equipo 3,2,1"),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Garantizar que 3,2,1 SHOW crezca de forma ordenada, rentable y segura, cuidando la legalidad, el valor del trabajo creat","% de shows realizados con contrato firmado Meta: 100%","Ordenar la estructura legal y contractual de 321"),
                ("ITACA EDUCACIÓN","ITACA FAN","Generar confianza desde el primer contacto","tasa de conversión","Estandarizar primer contacto"),
                ("ITACA EDUCACIÓN","ITACA FAN","Enamoramiento durante el Servicio - Confirmar decisión","NPS","Diseño / Re diseño del plan de capacitación por unidad (niños / adulto)"),
                ("ITACA EDUCACIÓN","ITACA FAN","Experiencia WOW","% Asistencia","Clausura"),
                ("ITACA EDUCACIÓN","ITACA FAN","Recomendación","% de completion","Elaboración de formulario NPS"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Alinear al equipo con ADN de Educación","% de completion","Comunicación corporativa"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Instalar planificación estratégica real","% de completion","Planificación y control"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Mejorar desempeño y claridad de roles","% de productividad","Gestión del desempeño"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Equipo TOP Talent","% de completion","Detección de Brechas y habilidades en el equipo"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Identificar áreas de oportunidad y optimizar procesos hacia los resultados.","% de completion","Evaluación de competencias y habilidades"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reconozco y valoro los logros individuales y colectivos","% de completion","Celebro pequeños y grandes logros del equipo"),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Desarrollar y consolidar un equipo de entrenadores autónomos, alineados al ADN y metodología de la Ítaca Educación, que ","% de completion","Formación de Entrenadores"),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Diversificar ingresos","Ingresos no core","Diseño portafolio de productos"),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Incrementar ticket promedio","Recompra","Productos premium y PRO"),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Monetizar experiencia WOW","Margen por evento","Eventos y experiencias"),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Reducir riesgos legales","% Incidentes legales","Marco legal y contractual"),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Establecer comunicación segura","% equipo capacitado","Lenguaje seguro"),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Alinear al equipo docente con el ADN ArtaMax y el propósito de formar FANS","% de docentes alineados a los no negociables ArtaMax","Sistema de ADN ArtaMax (No Negociables de Experiencia)"),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Fortalecer la competencia emocional y relacional del equipo docente","% de docentes con evaluaciones positivas en trato emocional","Formación en Liderazgo Emocional Aplicado"),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Instalar una cultura de seguimiento, feedback y mejora continua","% de docentes con 1:1 realizados según frecuencia","Sistema de Reuniones 1:1 con Docentes"),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Cuidar al equipo para sostener la experiencia FAN en el tiempo","Nivel de satisfacción del equipo (encuesta interna)","Sistema de Cuidado y Contención del Equipo"),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Incrementar el ingreso promedio por cliente sin afectar la experiencia FAN","Ticket promedio por programa","Optimización de Productos y Experiencias Complementarias"),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Aumentar la recurrencia y permanencia del cliente en el tiempo","Tasa de reinscripción por programa","Sistema de Continuidad y Fidelización"),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Optimizar la gestión financiera y el control operativo","Margen por programa","Control Financiero por Programa"),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Garantizar cumplimiento legal, contractual y reputacional","% de contratos/documentos actualizados","Gestión Legal y Contractual"),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Convertir al espectador en fan recurrente de las obras del CAC.","Lograr que al menos el 30% del público asistente repita asistencia a otra obra del CAC durante el año.","Experiencia integral del espectador"),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reducir fricción y desgaste en la operación por obra","Mantener relaciones profesionales sanas con los equipos de producción, logrando que al menos el 80% de los roles clave f","Onboarding claro y humano por obra"),
                ("CLUB ARTE Y CULTURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Asegurar la viabilidad económica de las producciones del CAC.","Lograr que al menos el 70% de las obras producidas en 2026 alcancen la utilidad operativa mínima definida previamente pa","Definición previa de viabilidad por obra"),
                ("CLUB ARTE Y CULTURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Sostener y rentabilizar los equipos técnicos del CAC como activos estratégicos.","Cubrir al menos el 100% de los costos anuales de mantenimiento y reposición de equipos mediante su uso en producciones y","Gestión activa de activos técnicos"),
                ("CLUB ARTE Y CULTURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Reducir riesgos legales y contractuales en la operación de la Productora.","Formalizar acuerdos contractuales básicos para el 100% de directores, productores y proveedores críticos involucrados en","Estandarización contractual mínima"),
                ("CONVERSEMOS","ITACA FAN","Brindar una experiencia terapéutica humana y de calidad (NPS, RESEÑAS)","NPS","NPS alta terapeutica"),
                ("CONVERSEMOS","LIDERAZGO EMOCIONALMENTE COMPETENTE","Brindar una experiencia terapéutica humana y de calidad (NPS, RESEÑAS)","Elevar la satisfacción y el bienestar emocional del equipo clínico","Medir satisfacción de psicólogo"),
                ("CONVERSEMOS","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Brindar una experiencia terapéutica humana y de calidad (NPS, RESEÑAS)","Mejorar % de cierre y ocupación","Estandarización del guion de primer contacto (humano + claro)"),
                ("MARKETING","ITACA FAN","INCREMENTAR LA RETENCIÓN Y LTV DEL CLIENTE","LTV","Estandarización del Reporte de Valor (Informe Detallado)"),
                ("MARKETING","ITACA FAN","CONVERTIR A NUESTROS CLIENTES EN EMBAJADORES","CANTIDAD DE REFERIDOS","Estrategia de Referidos Activa (\"Member get Member\")"),
                ("MARKETING","LIDERAZGO EMOCIONALMENTE COMPETENTE","AUMENTAR LA PRODUCTIVIDAD DE CADA TRABAJADOR","CANTIDAD MENSUAL DE ENTREGAS","Seguimiento y actualización de las herramientas de Tracking (Excel de entregas y Notion)"),
                ("MARKETING","LIDERAZGO EMOCIONALMENTE COMPETENTE","MEJORAR LA SATISFACCIÓN DE CADA TRABAJADOR EN LA EMPRESA","NPS","Integraciones Itaca Marketing"),
                ("MARKETING","LIDERAZGO EMOCIONALMENTE COMPETENTE","CONVERTIR A LOS TRABAJADORES EN MARKETERS 360°","EVALUACIONES","Itaca Academy (Formación Técnica 360°)"),
                ("MARKETING","SOSTENIBILIDAD ECONÓMICA Y LEGAL","BLINDAJE LEGAL OPERATIVO (Cero Fugas)","% de Cobertura Contractual","Auditoría Contractual"),
                ("MARKETING","SOSTENIBILIDAD ECONÓMICA Y LEGAL","SALUD FINANCIERA Y FLUJO DE CAJA","DSO (Days Sales Outstanding)","Sistema de Cobranza Preventiva"),
                ("MARKETING","SOSTENIBILIDAD ECONÓMICA Y LEGAL","ESCALABILIDAD COMERCIAL","MRR (Monthly Recurring Revenue)","Estrategia de \"High Ticket\""),
                ("KIDS PIURA","ITACA FAN","INCREMENTAR LA TASA DE SATISFACCIÓN DEL CLIENTE externo","NPS","Medición de satisfacción del cliente en Ítaca Kids"),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aumentar la satisfacción y compromiso del equipo","NPS","Cultura de pertenencia y motivación"),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Asegurar alineación y claridad de rol","Nivel de alineación conductual y visual del equipo","Comunicación, alineación y feedback"),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Garantizar la excelencia y desarrollo del trainer","Nivel de Desempeño","Liderazgo y desarrollo del trainer"),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Cuidar la salud emocional del equipo","eNPS","Bienestar y cuidado integral"),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Incrementar la facturación y asegurar crecimiento","Ingresos Extra (Fuera de mensualidad)","Estrategia de crecimiento comercial"),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Blindar la operación legal y normativa","Cumplimiento Legal (Compliance)","Marco normativo y roles operativos"),
                ("ECO","ITACA FAN","Venta Futura","+10% Nuevos Inscritos","Diseño de Campaña Referidos"),
                ("ECO","ITACA FAN","Clausura","> 30% de Rentabilidad","Definición Financiera Clausura"),
                ("ECO","ITACA FAN","Padres Defensores","Grupos Activos (Sin silencio)","Envío de Contenido Semanal"),
                ("ECO","ITACA FAN","Comunidad","5 Testimonios de Calidad","Scouting de Testimonios"),
                ("ECO","ITACA FAN","Calidad Académica","100% Listo 48h antes","Planificación Semana 5"),
                ("ECO","LEC","Claridad de Rol","0 Reportes de \"No sabía\"","Definición del Rol ÍTACA"),
                ("ECO","LEC","Marca Personal","1 Idea implementada / quincena","Desarrollo Marca Docente"),
                ("ECO","LEC","Gestión Crisis","100% Staff Capacitado","Comunicación Consciente"),
                ("ECO","LEC","Regulación","100% Mapeado","Autoregulación (DISC)"),
                ("ECO","LEC","Clima Laboral","> 8 Puntos","Evaluación Satisfacción"),
                ("ECO","LEC","Feedback","100% Cumplimiento Semanal","Normalización Feedback"),
                ("ECO","DINERO yLEGAL","Control Financiero","Detectar Fugas de Dinero","Cierre de Caja Enero"),
                ("ECO","DINERO yLEGAL","Diversificación","50SOLES MÁS por alumno","Venta Productos Premium (Video/Merch)"),
                ("ECO","DINERO yLEGAL","Rentabilidad Clausura","Presupuesto Aprobado","Estructura Costos Clausura"),
                ("ECO","DINERO yLEGAL","Orden Legal","100% Contratos Firmados","Regularización Contractual"),
                ("ECO","DINERO yLEGAL","Mitigación Riesgo","0 Contingencias","Educación Legal"),
            ]
            for ps in plan_seed:
                db.execute("INSERT INTO planes_estrategicos (unidad,foco_estrategico,objetivo,kr,actividad_clave) VALUES (?,?,?,?,?)", ps)

        # ── SEED: Sprints/Tareas (extraídos de Excel reales) ──
        existing_sprints = db.execute('SELECT COUNT(*) FROM seguimiento_sprints').fetchone()[0]
        if existing_sprints == 0:
            sprint_seed = [
                ("321 SHOW","ITACA FAN","Tener reunión con entrenadores para preparar el programa NO IMPROVISAR","FRANCS","","Terminado",100),
                ("321 SHOW","ITACA FAN","Ejecutar el show de acuerdo a lo que se prepara","FRANCS","","Terminado",100),
                ("321 SHOW","ITACA FAN","Enviar encuesta de satisfacción a cliente","SHEBA","","Terminado",100),
                ("321 SHOW","ITACA FAN","Entregar invitación especial de 321 a su propio evento (tarjeta física o video)","ENTRENADORES","","Terminado",100),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir el precio base mínimo del show (no negociable)","SHEBA, FRANCS","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Guion de llamada empática","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Protocolo tiempos respuesta","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Capacitar al equipo en llamadas de primer contacto","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseñar/Documentar/Revisar brochure completo por fase LS","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseñar/Documentar/Revisar guía completa por fase LS","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseñar/Documentar/Revisar brochure completo por fase Oratoria Adultos","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseñar/Documentar/Revisar guía completa por fase Oratoria Adultos","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Validar planes con equipo de entrenadores","CARLA, JADEK","","Terminado",100),
                ("ITACA EDUCACIÓN","ITACA FAN","Elaborar y revisar formularios NPS","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Elaboración Calendario y Agenda Semanal","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reuniones Semanales =Alinear las tareas de la unidad con la misión de ÍTACA","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Elaboración de infografía/ppt con ADN de Ítaca Educación","CARLA","","Terminado",100),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Socializar GANTT","CARLA","","Terminado",100),
                ("ARTAMAX","General","Implementar Pasaporte Creativo ArtaMax","ANTHO","","Terminado",100),
                ("ARTAMAX","General","Definir Treasure Points por programa","MAX","","Terminado",100),
                ("ARTAMAX","General","Diseñar WOW de inicio (bienvenida simbólica)","MAX","","Terminado",100),
                ("ARTAMAX","General","Diseñar WOW de desarrollo (material/formato sorpresa)","MAX","","Terminado",100),
                ("ARTAMAX","General","Protocolo logístico y de seguridad","MAX","","Terminado",100),
                ("ARTAMAX","General","Día de museo con misión creativa","MAX","","Terminado",100),
                ("ARTAMAX","General","Kit artístico ArtaMax  (sgt programa)","MAX","","Terminado",100),
                ("ARTAMAX","General","Tote Bag ArtaMax","MAX","","Terminado",100),
                ("ARTAMAX","General","Niño como protagonista del cierre","MAX","","Terminado",100),
                ("ARTAMAX","General","Caja de recuerdo ArtaMax","MAX","","Terminado",100),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Diseño de inducción centrada en experiencia y vínculo (no procesos).","MAX","","Terminado",100),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Role play de situaciones reales (niño frustrado, padre ansioso, conflicto).","MAX","","Terminado",100),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Guía práctica de frases permitidas / no permitidas.","MAX","","Terminado",100),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Evaluación post-formación (observación en aula).","MAX","","Terminado",100),
                ("MARKETING","ITACA FAN","Implementación del Protocolo de Respuesta Regla 2/10","SERHIO","","Terminado",100),
                ("MARKETING","ITACA FAN","Actualizar reportes de pauta (resultados: CAC, CPL, Inversión, Ventas) en base al CRM y a Meta.","SERHIO, SANTIAGO, FERNANDA","","Terminado",100),
                ("MARKETING","LIDERAZGO EMOCIONALMENTE COMPETENTE","Estandarizar guías de contenido (Objetivos, Requerimientos, Copy, Escena por escena, Visual, Diálogos y Textual, Complejidad).","SANTIAGO, SERHIO, HUB","","Terminado",100),
                ("MARKETING","LIDERAZGO EMOCIONALMENTE COMPETENTE","Explicar y Capacitar en la ejecución de las guías de contenido.","SERHIO","","Terminado",100),
                ("MARKETING","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Confirmar continuidad de cartera actual","SANTIAGO, SERHIO, FERNANDA","","Terminado",100),
                ("KIDS PIURA","ITACA FAN","Revisión de formulario de NPS","MATTIAS, NADIA","","Terminado",100),
                ("KIDS PIURA","ITACA FAN","Realizar y actualizar diploma de Embajador","ASTRID, NADIA","","Terminado",100),
                ("KIDS PIURA","ITACA FAN","Realizar texto \"Susurros de Ítaca Kids\"","MATTIAS","","Terminado",100),
                ("KIDS PIURA","ITACA FAN","Comunicar reunión para agendar","MATTIAS","","Terminado",100),
                ("KIDS PIURA","ITACA FAN","Estandarizar la ruta de \"Huellas Familiares\"","MATTIAS","","Terminado",100),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Entrega de polos a entrenadores","MATTIAS, ASTRID","","Terminado",100),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Establecer los \"Do y Dont's\" con el equipo","MATTIAS, NADIA, ASTRID","","Terminado",100),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Crear el programa de Capacitación","MATTIAS, NADIA","","Terminado",100),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Comunicar al equipo la agenda de capas","MATTIAS","","Terminado",100),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Preparar presentación institucional o propuesta de valor","ASTRID, NADIA","","Terminado",100),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Revisión y modificaciones de contrato","MATTIAS","","Terminado",100),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Revisión y modif. manual de funciones (locadores)","MATTIAS","","Terminado",100),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Carta de autorización de imagen del menor","MATTIAS","","Terminado",100),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Revisión y actualización de guías","ASTRID, NADIA","","Terminado",100),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Sesión bienvenida potente ( estandarizar la bienvenida- convertilo en una experiencia)","BRIAN, Stef","","Terminado",100),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Entrega de polo CAC ( LOGO + FRASE CLUB)","KEILA, Stef","","Terminado",100),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Difundir y reforzar el mapa visual de cursos por niveles (via wpp)","Stef","","Terminado",100),
                ("321 SHOW","ITACA FAN","Agendar reunión con mi cliente","FRANCS","","En Proceso",50),
                ("321 SHOW","ITACA FAN","Logistica de misiones 321","FRANCS","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Medir el tiempo de respuesta de lead","CARLA","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseñar/Documentar/Revisar brochure completo por fase IE","CARLA","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseñar/Documentar/Revisar guía completa por fase IE","CARLA","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Video de despedida alumno/familia","JADEK","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Insignias semanales Little Speakers","CARLA, JADEK","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Reunión feedback final","CARLA","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Continuidad programa de Adultos","CARLA, JADEK","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Videos progreso semanal","JADEK","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Envío NPS semanal y final Little Speakers","JADEK","","En Proceso",50),
                ("ITACA EDUCACIÓN","ITACA FAN","Envío NPS semanal y final Adultos","JADEK","","En Proceso",50),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Definir líneas de producto","CARLA","","En Proceso",50),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Análisis de rentabilidad por producto","CARLA","","En Proceso",50),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Solicitar autorización a papás","JADEK","","En Proceso",50),
                ("ARTAMAX","General","Ritual de validación del proceso (no del resultado)","MAX","","En Proceso",50),
                ("ARTAMAX","General","Espacios donde el niño explica su obra","MAX","","En Proceso",50),
                ("ARTAMAX","General","Producto de registro visual del proceso creativo (bitacora)","MAX, ANTHO","","En Proceso",50),
                ("ARTAMAX","General","Diseñar WOW de cierre (presentación + aplauso consciente)","MAX, ANTHO","","En Proceso",50),
                ("ARTAMAX","General","Checklist de experiencia WOW por sesión","MAX","","En Proceso",50),
                ("ARTAMAX","General","Mural Padre–Hijo con tema emocional","MAX","","En Proceso",50),
                ("ARTAMAX","General","Clase de arte compartido (padre + niño)","MAX","","En Proceso",50),
                ("ARTAMAX","General","Actividad creativa colaborativa sin jerarquías","MAX","","En Proceso",50),
                ("ARTAMAX","General","Registro fotográfico y testimonial (mktg)","MAX, ANTHO","","En Proceso",50),
                ("ARTAMAX","General","Conversatorios con padres de familia","MAX","","En Proceso",50),
                ("ARTAMAX","General","Diseño de temática creativa por salida","MAX","","En Proceso",50),
                ("ARTAMAX","General","Cierre tipo galería abierta","MAX","","En Proceso",50),
                ("ARTAMAX","General","Intervención artística ArtaMax","MAX","","En Proceso",50),
                ("ARTAMAX","General","Registro audiovisual de la experiencia","MAX","","En Proceso",50),
                ("ARTAMAX","General","Conversación post-visita con los niños","MAX","","En Proceso",50),
                ("ARTAMAX","General","Mandil personalizado con nombre","MAX","","En Proceso",50),
                ("ARTAMAX","General","Talleres especiales \"edición limitada de ArtaMax Studio\" - talleres de un dia (Pintura nocturna con luz, escultura con musica en vivo, acuarelas, pi","MAX","","En Proceso",50),
                ("ARTAMAX","General","Cumpleaños Artístico ArtaMax con 3,2,1 show","MAX, ANTHO","","En Proceso",50),
                ("ARTAMAX","General","Diseño de clausura con varias disciplinas artísticas","MAX","","En Proceso",50),
                ("ARTAMAX","General","Obra significativa + foto del proceso","MAX","","En Proceso",50),
                ("ARTAMAX","General","Frase del niño","MAX","","En Proceso",50),
                ("ARTAMAX","General","Certificado simbólico de crecimiento","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Definir y documentar los No Negociables ArtaMax (trato, vínculo, puntualidad, ausencia, lenguaje).","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Dinámica vivencial: “cómo se siente un niño en ArtaMax”.","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Casos reales (historias de niños y padres).","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Taller interno: Validación emocional del niño","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Observaciones breves y planificadas de sesiones.","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Registro de fortalezas emocionales del docente.","MAX","","En Proceso",50),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Plan de mejora individual (1 o 2 acciones máximo).","MAX","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Aplicación creativa de 2 NPS por programa","","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Análisis de resultados \"NPS\"","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Elaborar informes de hallazgos","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Diseño y ejecución de plan post-NPS","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Reconocer a niños (Embajador de Alegría)","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Mensaje e imagen de cumpleañeros al wsp","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Realizar bitácora","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Enviar bitácora al final del programa","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Generar/compartir Evidencias Mágicas","MATTIAS, TAIZ","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Enviar audios \"Susurros de Ítaca Kids\"","MATTIAS, TAIZ","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Seguimiento comunicación Entrenador-Padres","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Decorar y adecuar la sala de espera","MATTIAS, TAIZ","","En Proceso",50),
                ("KIDS PIURA","ITACA FAN","Realizar espacio \"Huellas Familiares\"","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Momento de confraternidad","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Sistema de motivación (rec. emocional/económico)","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Celebración de Cumpleaños Entrenadores","MATTIAS, TAIZ","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Generar espacios de feedback grupales","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Realizar 4 reuniones por temporada","MATTIAS, NADIA, ASTRID","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aplicar DISC","MIRAI, MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Espacios One to One (Líder Coach)","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Realizar la capacitación","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Realizar modelo de certificado post-capa","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aplicación de Matriz de 9 cajas","MIRAI, MATTIAS","","En Proceso",50),
                ("KIDS PIURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Tener lugar de descanso adaptado","MATTIAS","","En Proceso",50),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Ofrecer sesiones de adaptabilidad en ventas","ASTRID, NADIA","","En Proceso",50),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Realizar mercha: polo, tomatodo.","ASTRID","","En Proceso",50),
                ("KIDS PIURA","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Magic Day Ítaca Kids (día de integración familiar)","NADIA, ASTRID, MATTIAS, TAIZ","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Identificar alumnos en riesgo (monitoreo de asistencia) Contactar ante 2 faltas seguidas","KEILA, Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Aplicar tamizaje emocional breve a los alumnos","","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Para PROFAIC, enviar a los padres un video de como se han vivido las clases, y qué se vienen los próximos meses","BRIAN, KEILA","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Realizar reunión con papás para profaic","BRIAN, KEILA","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Alinear al docente con la ruta de continuidad Pedir que refuerce el “siguiente paso” en clase Detectar señales tempranas de no continuidad","BRIAN, Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Prepar encuesta 2026  ( revisar y ajustar de ser necesario ) y enviarlas por grupos de whastapp a cada nivel  ( en el caso de PROFAIC, encuestar padre","Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Comunicar y vaciar información a reporte de seguimiento","Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","• Tomar feedbacks de encuestas, priorizar puntos críticos • Definir acciones correctivas y ejecutar","","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","- Coordinar reunión  ( espacio, actividades) - Invitación y confirmación de participantes","Stef, BRIAN","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","- Coordinar con aliados","","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","- Invitación y confirmación de participantes","LUIS, BRIAN","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Diseñar programa de referidos (beneficios) (descuento con aliados, experiencia o pases para la obra)","Stef, BRIAN","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Levantamiento de información  (Identificar tipo de vínculo contractual de cada colaborador)","","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reuniones 1 a 1 y registro de cada colaborador","KEILA","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","- Diseñar encuesta breve (5 preguntas claras).","Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","- Aplicarla al fin de cada ciclo","Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","- Analizar resultados y detectar patrones, no personas.","KEILA, Stef","","En Proceso",50),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aplicar tamizaje de Bienestar Emocional","Stef, MIRAI","","En Proceso",50),
                ("321 SHOW","ITACA FAN","Un reel resumen estándar de 40 segundos de lo que fue el show","SHEBA","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Entregar diploma emocional al cliente que nos contrata","ENTRENADORES","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Enviar mensaje de cierre personalizado \"Fue un lindo momento que vivimos, esperamos verlos nunca jamás\"","SHEBA","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Grabar el testimonio del cliente para reel","VIDEOGRÁFO","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Crear canciones de entrada y despedida 321","ASTRID, FRANCS","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Diseñar vestuario de 321","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Historias destacadas de cada evento","SHEBA","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Publicar reel de testimonios de la experiencia vivida de familia","SHEBA","","Pendiente",0),
                ("321 SHOW","ITACA FAN","Realizar pauta publicitaria","BRANDO","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Liderar reunión breve semanal (o mensaje de voz/WhatsApp)","FRANCS","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Modelar con el ejemplo la cultura 3,2,1","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reforzar objetivos clave antes de cada show","ENTRENADORES, FRANCS","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Revisar avances semanalmente","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Asegurar que cada entrenador sepa que show tiene, que rol cumple y que se espera de él.","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aplicar evaluación DISC (rojo, azul, verde, amarillo)","ASTRID, FRANCS","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Revisar manual de funciones de entrenador","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Evaluar mensualmente si las tareas están alineadas al talento","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Facilitar espacios de coaching grupal e individual","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Medir la capacitación (verificar si lo aprendido se aplica en los shows)","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Diseñar plan de desarrollo personal por entrenador","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Evaluación del gerente a sus colaboradores","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","LIDERAZGO EMOCIONALMENTE COMPETENTE","Identificar fortalezas y oportunidades de mejora","FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir el tipo de formalización del negocio (persona natural con negocio / empresa).","BRANDO, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Elaborar un contrato base para clientes (shows, cancelaciones, cambios).","BRANDO, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Elaborar un acuerdo interno con entrenadores (roles, uso de marca, imagen, pagos)","BRANDO, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir politicas claras (reservas, adelantos, reprogramaciones, uso de nombre de 321 y vestimenta)","BRANDO, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Registrar o avanzar el uso formal del nombre 321 SHOW","BRANDO, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Crear 3 niveles de experiencias (esencial, experiencia 321, momento único)","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir precios de servicios extra.","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Establecer política de decuentos (cuando sí/ cuando no)","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Eventos teatrales (día del niño y halloween)","SHEBA, FRANCS, BRANDO","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Albúm MOMENTOS MÁGICOS 321","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Registrar ingresos y egresos por evento","SHEBA","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir pago estándar por rol (entrenador, líder y apoyo)","SHEBA, FRANCS","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Identificar posibles aliados (colegios, clubes, instituciones, centros comerciales y programas educativos)","SHEBA, FRANCS, ASTRID","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Leads de Itaca Kids","FRANCS, ASTRID, ENTRENADORES","","Pendiente",0),
                ("321 SHOW","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Documentar el método 321 (viaje, filosofía, frases, canciones)","SHEBA, FRANCS, ASTRID","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Hacer análisis final de la tasa de conversión","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Elaborar el calendario y agenda de reuniones","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Avisos","JADEK","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Meetings 1:1 iniciales","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Diseño Clausura = ritual emocional","CARLA, JADEK","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Logística + Zona fotos + testimonios","JADEK, MKT","","Pendiente",0),
                ("ITACA EDUCACIÓN","ITACA FAN","Activar referidos","VENTAS","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Revisión mensual de objetivos","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Ajuste del plan","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Perfil de colaboradores","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reasignación o Capacitación","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aplicar DISC","CARLA, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Matriz de 9 cajas","CARLA, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Identifico brechas de talento","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Aplicación de Plan de Desarrollo Personal","CARLA, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Estructuración de plan de capacitación Mensual","CARLA, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Socializar Plan de Capacitación Trimestral","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Sesiones de Coaching/Mentoring","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Realizar evaluación 360°","CARLA, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Sesiones de Feedback individual","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Sesiones de Feedback grupal","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Identificación de logros","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Celebración de resultados","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Rediseñar y documentar el programa de Formación de Entrenadores.","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Certificar entrenadores","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","LIDERAZGO EMOCIONALMENTE COMPETENTE","Talleres dictados por entrenadores que no sean Carla","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Diseño Programa PRO Oratoria","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Lanzar la primera versión","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Diseño eventos debate y WOW","CARLA, JADEK","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Ejecución eventos","CARLA, JADEK","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Formalizar contratos base","LEGAL, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Consentimientos informados - Acuerdos verbales","LEGAL, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Auditoría legal semestral","LEGAL","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Elaborar y revisar autorización de uso de imagen menores","CARLA, LEGAL","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Elaboración de JD voluntario","CARLA, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Armar plan de voluntariado","LEGAL, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Elaboración de declaración jurada de Voluntarios","LEGAL","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Manual Do & Don’ts","CARLA","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Capacitación legal del equipo","LEGAL, MIRAI","","Pendiente",0),
                ("ITACA EDUCACIÓN","SOSTENIBILIDAD ECONOMICA Y LEGAL","Capacitación antihostigamiento","LEGAL, MIRAI","","Pendiente",0),
                ("ARTAMAX","General","Aplicar Nps a mitad y final de programa","","","Pendiente",0),
                ("ARTAMAX","General","Analizar Nps a mitad y final de programa","","","Pendiente",0),
                ("ARTAMAX","General","Feedback emocional personalizado (audios o textos)","MAX, ANTHO","","Pendiente",0),
                ("ARTAMAX","General","Mensajes de observación del proceso (no académico)","MAX","","Pendiente",0),
                ("ARTAMAX","General","Registro de respuestas y retroalimentación","MAX","","Pendiente",0),
                ("ARTAMAX","General","Pintura al aire libre","MAX","","Pendiente",0),
                ("ARTAMAX","General","Gestión de convenios con centros campestres/parques","MAX","","Pendiente",0),
                ("ARTAMAX","General","Productos simbólicos del programa- Funkos coleccionables de los entrenadores por temporada","MAX","","Pendiente",0),
                ("ARTAMAX","General","Palabras personalizadas al niño","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Socializar los no negociables con ejemplos reales (qué sí / qué no).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Colocar los no negociables visibles en sala de docentes. (prox temporada)","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Checklist de cumplimiento por sesión.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Registro de quiebres y acciones correctivas.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Validación final de comprensión del rol como agente de experiencia.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Taller interno: Educación con mirada inclusiva: acompañando a niños neurodivergentes\"","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Taller interno: Liderazgo emocional aplicado al aula artistica","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Feedback inmediato (qué se mantiene / qué se ajusta).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Definir frecuencia (quincenal o mensual).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Guía base para 1:1 (estado emocional, desempeño, ideas WOW).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Registro de acuerdos en formato simple.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Seguimiento del cumplimiento de acuerdos.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Revisión de indicadores del programa.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Análisis de casos relevantes (niños, padres, quiebres).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Alineación de mensajes y criterios.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Ajustes metodológicos cuando sea necesario.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Espacios de escucha y descarga emocional.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Conversaciones preventivas (antes del desgaste).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Ajustes de carga cuando sea necesario.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Canal claro para expresar incomodidades.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Reconocer públicamente buenas prácticas.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Compartir historias de impacto (niños/familias).","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Cerre por programa también para el equipo.","MAX","","Pendiente",0),
                ("ARTAMAX","LIDERAZGO EMOCIONALMENTE COMPETENTE","Mensajes de agradecimiento personalizados.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir portafolio activo de productos FAN (kits, mandiles, tote, cajas recuerdo).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir qué producto se activa en qué momento del journey (inicio, mitad, cierre).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Establecer precios alineados al valor emocional (no solo costo).","MAX, BRANDON, ANTHO","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Capacitar al equipo en activación emocional del producto (no venta directa).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Control de stock y rotación.","MAX, ANTHO","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Diseñar experiencias premium (padres, adultos, familia).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir aforo, costo, margen objetivo.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Alianzas con espacios externos (cafés, galerías, centros culturales).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Registro de asistencia y conversión posterior.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Diseñar rutas de continuidad por edad/programa.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Ofrecer continuidad como evolución natural (no como venta).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Activar preventa exclusiva para familias FAN.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Seguimiento a intención de reinscripción post-clausura.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir beneficios reales (prioridad, experiencias exclusivas, descuentos cruzados).","MAX, BRANDON","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir precio anual y condiciones.","MAX, BRANDON","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Onboarding de membresía (ritual de bienvenida).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Seguimiento de uso de beneficios.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Definir presupuesto estándar por programa.","MAX, BRANDON","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Registrar costos reales vs proyectados.","MAX, BRANDON","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Análisis de rentabilidad por programa.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Ajustes operativos cuando sea necesario.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Evaluar proveedores de materiales y servicios.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Negociar convenios y compras por volumen.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Reducir mermas y desperdicios.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Planificar compras según calendario GANTT.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Actualizar contratos de docentes y proveedores.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Revisar políticas de consentimiento (niños, imágenes, salidas).","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Asegurar cumplimiento de seguros y permisos.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Archivo y control documental.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Registro y uso correcto de marca ArtaMax.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Lineamientos de uso de imagen en redes.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Protocolo de manejo de reclamos.","MAX","","Pendiente",0),
                ("ARTAMAX","SOSTENIBILIDAD ECONÓMICA Y LEGAL","Seguimiento a reputación digital.","MAX","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Diseñar experiencia antes, durante y después de la obra  Activar saludo del elenco  Activar momentos memorables (fotos, mensajes, etc.)","LUIS, BRIAN","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","ITACA FAN","- Invitación a próximas obras - Activación de beneficios por repetición","LUIS, BRIAN","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Encuesta post-función Recolección de feedback cualitativo","STEF","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","ITACA FAN","Identificar puntos críticos  Ajustes de según feedbacks recibidos","KEILA, STEF","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","- Reunión inicial con visión, reglas y expectativas - Definción simple de roles y tiempos - Canal único de comunicación","LUIS, BRIAN","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Check-in intermedio por obra - Conversaciones directas ante tensiones - Registro interno de incidencias","LUIS, BRIAN","","Pendiente",0),
                ("CLUB ARTE Y CULTURA","LIDERAZGO EMOCIONALMENTE COMPETENTE","Mensaje o reunión de cierre - Pago oportuno  - Agradecimiento + puerta abierta explícita","KEILA, LUIS, BRIAN","","Pendiente",0),
            ]
            for ss in sprint_seed:
                db.execute("INSERT INTO seguimiento_sprints (unidad,foco_relacionado,tarea,responsable,fecha_limite,estatus,avance) VALUES (?,?,?,?,?,?,?)", ss)

        # ── SEED: Metas Mensuales (extraídas de hojas Seguimiento de los Excel reales) ──
        existing_metas = db.execute('SELECT COUNT(*) FROM metas_mensuales').fetchone()[0]
        if existing_metas == 0:
            metas_seed = [
                # (unidad, programa, precio_std, meta_ene, real_ene, meta_feb, real_feb, ...)
                ("ITACA EDUCACIÓN", "Little Speakers", 600, 40, 23, 40, 0, 40, 0, 40, 0, 40, 0, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                ("ITACA EDUCACIÓN", "Oratoria Adultos", 350, 16, 15, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                ("321 SHOW", "Shows Corporativos", 1000, 8, 4, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0),
                ("ARTAMAX", "Programa Verano", 0, 72, 64, 72, 62, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                ("ARTAMAX", "Programa Regular", 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0),
                ("KIDS PIURA", "Talleres Kids", 0, 420, 316, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0, 420, 0),
                ("CONVERSEMOS", "Conver Piura", 0, 30, 0, 30, 0, 30, 0, 40, 0, 40, 0, 40, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0),
                ("CONVERSEMOS", "Conver Lima", 0, 28, 0, 28, 0, 28, 0, 40, 0, 40, 0, 40, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0, 50, 0),
                ("MARKETING", "Revenue MKT", 9000, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0),
                ("CLUB ARTE Y CULTURA", "Escuela CAC", 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0, 60, 0),
                ("CLUB ARTE Y CULTURA", "Productora CAC", 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0, 4, 0),
                ("ECO", "Programas ECO", 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0, 30, 0),
            ]
            for m in metas_seed:
                db.execute("""INSERT INTO metas_mensuales
                    (unidad, programa, precio_unitario,
                     meta_ene, real_ene, meta_feb, real_feb, meta_mar, real_mar,
                     meta_abr, real_abr, meta_may, real_may, meta_jun, real_jun,
                     meta_jul, real_jul, meta_ago, real_ago, meta_sep, real_sep,
                     meta_oct, real_oct, meta_nov, real_nov, meta_dic, real_dic)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", m)

# ═══════════════════════════════════════════
# CRUD OPERATIONS
# ═══════════════════════════════════════════

# ── USUARIOS ──
def get_user(email):
    with get_db() as db:
        return dict_row(db.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone())

def get_all_users():
    with get_db() as db:
        return dict_rows(db.execute("SELECT * FROM usuarios WHERE estado='Activo' ORDER BY nombre").fetchall())

def get_identidad(email):
    with get_db() as db:
        return dict_row(db.execute("SELECT * FROM identidad WHERE email=?", (email,)).fetchone())

def update_identidad(email, **kwargs):
    with get_db() as db:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [email]
        db.execute(f"UPDATE identidad SET {sets}, fecha_actualizacion=? WHERE email=?",
                   (*kwargs.values(), datetime.now().isoformat(), email))

def get_team_members(email_lider):
    with get_db() as db:
        user = dict_row(db.execute("SELECT unidad FROM identidad WHERE email=?", (email_lider,)).fetchone())
        if not user: return []
        return dict_rows(db.execute(
            "SELECT * FROM identidad WHERE unidad=? AND email!=? AND estado='Activo'",
            (user["unidad"], email_lider)).fetchall())

# ── CHECK-INS ──
def save_checkin(email, estado, estres, area, etiquetas, comentario):
    now = datetime.now()
    cid = f"{email}_{now.strftime('%Y-%m-%d')}"
    sem = f"{now.year}-S{now.isocalendar()[1]:02d}"
    with get_db() as db:
        existing = db.execute("SELECT 1 FROM checkins WHERE email=? AND semana=?", (email, sem)).fetchone()
        if existing:
            return False, "Ya hiciste tu check-in esta semana."
        db.execute("INSERT INTO checkins VALUES (?,?,?,?,?,?,?,?,?,?)",
            (cid, email, estado, estres, area, ",".join(etiquetas) if etiquetas else "",
             comentario, now.isoformat(), sem, 1 if estres >= 4 else 0))
    return True, "Check-in registrado. ¡Gracias por compartir!"

def get_my_checkins(email, limit=20):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM checkins WHERE email=? ORDER BY fecha DESC LIMIT ?",
            (email, limit)).fetchall())

def get_team_checkins(email_lider):
    members = get_team_members(email_lider)
    if not members: return []
    emails = [m["email"] for m in members]
    ph = ",".join("?" * len(emails))
    with get_db() as db:
        return dict_rows(db.execute(f"""
            SELECT c.*, i.nombre FROM checkins c
            JOIN identidad i ON c.email = i.email
            WHERE c.email IN ({ph})
            ORDER BY c.fecha DESC LIMIT 50""", emails).fetchall())

def checkin_done_this_week(email):
    now = datetime.now()
    sem = f"{now.year}-S{now.isocalendar()[1]:02d}"
    with get_db() as db:
        return db.execute("SELECT 1 FROM checkins WHERE email=? AND semana=?", (email, sem)).fetchone() is not None

# ── FAROS ──
def save_faro(email_emisor, email_receptor, tipo_faro, mensaje):
    from config import TIPOS_FARO
    info = TIPOS_FARO[tipo_faro]
    now = datetime.now()
    fid = f"FARO_{int(now.timestamp())}"
    with get_db() as db:
        em = db.execute("SELECT nombre FROM identidad WHERE email=?", (email_emisor,)).fetchone()
        rc = db.execute("SELECT nombre FROM identidad WHERE email=?", (email_receptor,)).fetchone()
        nombre_e = em["nombre"] if em else email_emisor
        nombre_r = rc["nombre"] if rc else email_receptor
        db.execute("INSERT INTO faros VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, email_emisor, nombre_e, email_receptor, nombre_r, tipo_faro,
             info["pilar"], info["animal"], mensaje, "", now.isoformat(),
             "Aprobado", "", now.isoformat(), 0, 1))
    return True, f"¡Faro enviado a {nombre_r}!"

def get_faros_recibidos(email, limit=20):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM faros WHERE email_receptor=? AND visible=1 ORDER BY fecha_envio DESC LIMIT ?",
            (email, limit)).fetchall())

def get_faros_enviados(email, limit=20):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM faros WHERE email_emisor=? ORDER BY fecha_envio DESC LIMIT ?",
            (email, limit)).fetchall())

def get_faros_publicos(limit=20):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM faros WHERE visible=1 ORDER BY fecha_envio DESC LIMIT ?",
            (limit,)).fetchall())

def celebrar_faro(faro_id):
    with get_db() as db:
        db.execute("UPDATE faros SET celebraciones = celebraciones + 1 WHERE faro_id=?", (faro_id,))

# ── HEXÁGONO ──
def save_hexagono(email, puntajes, reflexion):
    now = datetime.now()
    periodo = now.strftime("%Y-%m")
    eid = f"{email}_{periodo}"
    vals = list(puntajes.values())
    prom = round(sum(vals) / 6, 2)
    nombres = ["Visión Corporativa","Planificación","Encaje de Talento","Entrenamiento","Evaluación y Mejora","Reconocimiento"]
    dim_baja = nombres[vals.index(min(vals))]
    dim_alta = nombres[vals.index(max(vals))]
    with get_db() as db:
        existing = db.execute("SELECT 1 FROM hexagono WHERE eval_id=?", (eid,)).fetchone()
        if existing:
            return False, "Ya evaluaste este mes."
        db.execute("INSERT INTO hexagono VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, email, periodo, now.isoformat(), *vals, prom, reflexion, dim_baja, dim_alta))
    return True, f"Evaluación guardada. Promedio: {prom}"

def get_my_hexagono(email, limit=12):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM hexagono WHERE email=? ORDER BY periodo DESC LIMIT ?",
            (email, limit)).fetchall())

# ── JOURNAL ──
def save_journal(email, emociones, intensidad, trigger, pensamiento, reflexion, estrategia, efectividad, contexto):
    now = datetime.now()
    jid = f"{email}_{now.strftime('%Y-%m-%d_%H%M')}"
    dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    dia = dias[now.weekday()]
    hora = "Mañana" if now.hour < 12 else "Tarde" if now.hour < 18 else "Noche"
    with get_db() as db:
        db.execute("INSERT INTO journal VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (jid, email, now.isoformat(), ",".join(emociones), intensidad,
             trigger, pensamiento, reflexion, estrategia or "", efectividad or 0,
             contexto, dia, hora))
    return True, "Entrada de journal guardada."

def get_my_journal(email, limit=30):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM journal WHERE email=? ORDER BY fecha DESC LIMIT ?",
            (email, limit)).fetchall())

# ── BRÚJULA IE ──
def save_brujula(email, puntajes, reflexion):
    now = datetime.now()
    periodo = now.strftime("%Y-%m")
    bid = f"{email}_{periodo}"
    vals = list(puntajes.values())
    prom = round(sum(vals) / 5, 2)
    nombres = ["Autoconocimiento","Autorregulación","Motivación","Empatía","Habilidades Sociales"]
    comp_baja = nombres[vals.index(min(vals))]
    comp_alta = nombres[vals.index(max(vals))]
    with get_db() as db:
        existing = db.execute("SELECT 1 FROM brujula_eval WHERE brujula_id=?", (bid,)).fetchone()
        if existing:
            return False, "Ya evaluaste este mes."
        ej_count = db.execute("SELECT COUNT(*) FROM ejercicios_log WHERE email=? AND fecha LIKE ?",
            (email, f"{periodo}%")).fetchone()[0]
        j_count = db.execute("SELECT COUNT(*) FROM journal WHERE email=? AND fecha LIKE ?",
            (email, f"{periodo}%")).fetchone()[0]
        db.execute("INSERT INTO brujula_eval VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bid, email, periodo, now.isoformat(), *vals, prom, comp_baja, comp_alta,
             reflexion, ej_count, j_count))
    return True, f"Evaluación IE guardada. Promedio: {prom}"

def get_my_brujula(email, limit=12):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM brujula_eval WHERE email=? ORDER BY periodo DESC LIMIT ?",
            (email, limit)).fetchall())

# ── LOGROS ──
def get_my_logros(email):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM logros WHERE email=? ORDER BY fecha DESC", (email,)).fetchall())

def get_total_puntos(email):
    with get_db() as db:
        r = db.execute("SELECT COALESCE(SUM(puntos),0) FROM logros WHERE email=?", (email,)).fetchone()
        return r[0]

def otorgar_badge(email, badge_id, nombre, desc, puntos, categoria, icono):
    lid = f"LOGRO_{email.split('@')[0]}_{badge_id}"
    with get_db() as db:
        existing = db.execute("SELECT 1 FROM logros WHERE logro_id=?", (lid,)).fetchone()
        if existing: return False
        db.execute("INSERT INTO logros VALUES (?,?,?,?,?,?,?,?,?)",
            (lid, email, badge_id, nombre, desc, puntos, categoria, datetime.now().isoformat(), icono))
    return True

# ── NOTIFICACIONES ──
def get_notificaciones(email, limit=20):
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM notificaciones WHERE email_dest=? ORDER BY fecha DESC LIMIT ?",
            (email, limit)).fetchall())

def count_unread(email):
    with get_db() as db:
        return db.execute("SELECT COUNT(*) FROM notificaciones WHERE email_dest=? AND leida=0",
            (email,)).fetchone()[0]

# ═══════════════════════════════════════════
# EVALUACIÓN 360 DE LIDERAZGO
# ═══════════════════════════════════════════

def save_eval_360(email_evaluado, email_evaluador, periodo, v1, v2, v3, v4, v5, v6, promedio, comentario):
    eid = f"E360_{int(datetime.now().timestamp()*1000)}"
    with get_db() as conn:
        conn.execute("INSERT INTO eval_360 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, email_evaluado, email_evaluador, periodo, datetime.now().isoformat(),
             1, v1, v2, v3, v4, v5, v6, promedio, comentario))

def get_eval_360_results(email_evaluado, periodo=None):
    with get_db() as conn:
        if periodo:
            rows = conn.execute("SELECT * FROM eval_360 WHERE email_evaluado=? AND periodo=?",
                (email_evaluado, periodo)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM eval_360 WHERE email_evaluado=? ORDER BY fecha DESC",
                (email_evaluado,)).fetchall()
        return dict_rows(rows)

def get_360_avg(email_evaluado, periodo):
    with get_db() as conn:
        row = conn.execute("""SELECT AVG(vision) as vision, AVG(planificacion) as planificacion,
            AVG(encaje) as encaje, AVG(entrenamiento) as entrenamiento,
            AVG(evaluacion_mejora) as evaluacion_mejora, AVG(reconocimiento) as reconocimiento,
            AVG(promedio) as promedio, COUNT(*) as total
            FROM eval_360 WHERE email_evaluado=? AND periodo=?""",
            (email_evaluado, periodo)).fetchone()
        return dict_row(row)

def has_evaluated_360(email_evaluador, email_evaluado, periodo):
    with get_db() as conn:
        return conn.execute("SELECT 1 FROM eval_360 WHERE email_evaluador=? AND email_evaluado=? AND periodo=?",
            (email_evaluador, email_evaluado, periodo)).fetchone() is not None

# ═══════════════════════════════════════════
# EVALUACIÓN DE DESEMPEÑO
# ═══════════════════════════════════════════

def save_eval_desempeno(email, periodo, evaluador_email, evaluador_nombre,
    cumplimiento, calidad, equipo, comunicacion, iniciativa, promedio,
    fortalezas, areas_mejora, plan, comentario):
    eid = f"ED_{int(datetime.now().timestamp()*1000)}"
    with get_db() as conn:
        conn.execute("INSERT INTO eval_desempeno VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, email, periodo, datetime.now().isoformat(), evaluador_email, evaluador_nombre,
             cumplimiento, calidad, equipo, comunicacion, iniciativa, promedio,
             fortalezas, areas_mejora, plan, comentario))

def get_eval_desempeno(email):
    with get_db() as conn:
        return dict_rows(conn.execute("SELECT * FROM eval_desempeno WHERE email=? ORDER BY fecha DESC",
            (email,)).fetchall())

# ═══════════════════════════════════════════
# CAPACITACIONES
# ═══════════════════════════════════════════

def add_capacitacion(email, nombre, tipo, horas, fecha, certificado, institucion, notas):
    cid = f"CAP_{int(datetime.now().timestamp()*1000)}"
    with get_db() as conn:
        conn.execute("INSERT INTO capacitaciones VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, email, nombre, tipo, horas, fecha, 1 if certificado else 0, institucion, notas))

def get_capacitaciones(email):
    with get_db() as conn:
        return dict_rows(conn.execute("SELECT * FROM capacitaciones WHERE email=? ORDER BY fecha DESC",
            (email,)).fetchall())

# ═══════════════════════════════════════════
# GENERADOR DE REPORTES (DATA)
# ═══════════════════════════════════════════

def get_reporte_estrategico(unidad):
    with get_db() as conn:
        focos = dict_rows(conn.execute("SELECT * FROM focos WHERE unidad=? AND estado!='Eliminado'", (unidad,)).fetchall())
        for f in focos:
            f["krs"] = dict_rows(conn.execute("SELECT * FROM krs WHERE foco_id=? AND estado!='Eliminado'", (f["foco_id"],)).fetchall())
            f["tareas"] = dict_rows(conn.execute("SELECT * FROM tareas WHERE foco_id=? AND estado!='Eliminado'", (f["foco_id"],)).fetchall())
            total_t = len(f["tareas"])
            comp_t = len([t for t in f["tareas"] if t["estado"] == "Completado"])
            venc_t = len([t for t in f["tareas"] if t.get("fecha_limite") and t["fecha_limite"] < datetime.now().strftime("%Y-%m-%d") and t["estado"] != "Completado"])
            f["tareas_total"] = total_t
            f["tareas_completadas"] = comp_t
            f["tareas_vencidas"] = venc_t
        return focos

def get_reporte_clima(unidad=None, dias=30):
    with get_db() as conn:
        fecha_desde = (datetime.now() - timedelta(days=dias)).isoformat()
        if unidad:
            checkins = dict_rows(conn.execute("""
                SELECT c.*, i.nombre, i.unidad FROM checkins c
                JOIN identidad i ON c.email = i.email
                WHERE i.unidad=? AND c.fecha > ? ORDER BY c.fecha DESC""",
                (unidad, fecha_desde)).fetchall())
        else:
            checkins = dict_rows(conn.execute("""
                SELECT c.*, i.nombre, i.unidad FROM checkins c
                JOIN identidad i ON c.email = i.email
                WHERE c.fecha > ? ORDER BY c.fecha DESC""",
                (fecha_desde,)).fetchall())
        if not checkins:
            return {"total": 0, "avg_estres": 0, "alertas": 0, "por_estado": {}, "por_unidad": {}}
        avg_estres = sum(c["nivel_estres"] for c in checkins) / len(checkins)
        alertas = len([c for c in checkins if c["nivel_estres"] >= 4])
        por_estado = {}
        for c in checkins:
            e = c["estado_general"]
            por_estado[e] = por_estado.get(e, 0) + 1
        por_unidad = {}
        for c in checkins:
            u = c.get("unidad", "")
            if u not in por_unidad:
                por_unidad[u] = {"total": 0, "sum_estres": 0}
            por_unidad[u]["total"] += 1
            por_unidad[u]["sum_estres"] += c["nivel_estres"]
        for u in por_unidad:
            por_unidad[u]["avg_estres"] = round(por_unidad[u]["sum_estres"] / por_unidad[u]["total"], 1)
        return {
            "total": len(checkins), "avg_estres": round(avg_estres, 1),
            "alertas": alertas, "por_estado": por_estado, "por_unidad": por_unidad
        }

def get_reporte_cultura(dias=30):
    with get_db() as conn:
        fecha_desde = (datetime.now() - timedelta(days=dias)).isoformat()
        faros = dict_rows(conn.execute("SELECT * FROM faros WHERE fecha_envio > ?", (fecha_desde,)).fetchall())
        por_tipo = {}
        for f in faros:
            t = f["tipo_faro"]
            por_tipo[t] = por_tipo.get(t, 0) + 1
        top_emisores = {}
        for f in faros:
            n = f["nombre_emisor"]
            top_emisores[n] = top_emisores.get(n, 0) + 1
        top_receptores = {}
        for f in faros:
            n = f["nombre_receptor"]
            top_receptores[n] = top_receptores.get(n, 0) + 1
        return {
            "total_faros": len(faros), "por_tipo": por_tipo,
            "top_emisores": sorted(top_emisores.items(), key=lambda x: -x[1])[:5],
            "top_receptores": sorted(top_receptores.items(), key=lambda x: -x[1])[:5],
            "celebraciones": sum(f.get("celebraciones", 0) for f in faros)
        }

def get_reporte_ejecutivo():
    with get_db() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM usuarios WHERE estado='Activo'").fetchone()[0]
        por_unidad = dict_rows(conn.execute("""
            SELECT unidad, COUNT(*) as total FROM usuarios
            WHERE estado='Activo' AND unidad IS NOT NULL GROUP BY unidad ORDER BY unidad""").fetchall())
        por_rol = dict_rows(conn.execute("""
            SELECT rol, COUNT(*) as total FROM usuarios
            WHERE estado='Activo' GROUP BY rol""").fetchall())
    clima = get_reporte_clima()
    cultura = get_reporte_cultura()
    return {
        "total_users": total_users, "por_unidad": por_unidad, "por_rol": por_rol,
        "clima": clima, "cultura": cultura, "fecha": datetime.now().strftime("%d/%m/%Y")
    }

# ═══════════════════════════════════════════
# TABLERO ESTRATÉGICO: FOCOS + KR + TAREAS
# ═══════════════════════════════════════════

def _log_cambio(entidad, entidad_id, campo, anterior, nuevo, email_autor):
    """Registrar cambio en historial (audit trail)"""
    with get_db() as conn:
        cid = f"CHG_{int(datetime.now().timestamp()*1000)}"
        nombre = ""
        row = conn.execute("SELECT nombre FROM identidad WHERE email=?", (email_autor,)).fetchone()
        if row:
            nombre = row[0]
        conn.execute("INSERT INTO historial_cambios VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, entidad, entidad_id, campo, str(anterior), str(nuevo), email_autor, nombre, datetime.now().isoformat()))

# ── FOCOS ──
def create_foco(email_creador, unidad, nombre, descripcion, periodo, fecha_limite):
    fid = f"FOCO_{int(datetime.now().timestamp()*1000)}"
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("INSERT INTO focos VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (fid, email_creador, unidad, nombre, descripcion, periodo, 0, "En Progreso", now, fecha_limite, 0))
    return fid

def get_focos_by_unidad(unidad):
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM focos WHERE unidad=? AND estado!='Eliminado' ORDER BY orden, fecha_creacion DESC",
            (unidad,)).fetchall())

def get_focos_by_email(email):
    """Focos de la unidad del usuario"""
    with get_db() as conn:
        row = conn.execute("SELECT unidad FROM identidad WHERE email=?", (email,)).fetchone()
        if not row:
            return []
        return dict_rows(conn.execute(
            "SELECT * FROM focos WHERE unidad=? AND estado!='Eliminado' ORDER BY orden, fecha_creacion DESC",
            (row[0],)).fetchall())

def update_foco(foco_id, email_autor, **kwargs):
    with get_db() as conn:
        old = dict_row(conn.execute("SELECT * FROM focos WHERE foco_id=?", (foco_id,)).fetchone())
        if old:
            for k, v in kwargs.items():
                if str(old.get(k)) != str(v):
                    _log_cambio("foco", foco_id, k, old.get(k), v, email_autor)
        sets = ", ".join(f"{k}=?" for k in kwargs)
        conn.execute(f"UPDATE focos SET {sets} WHERE foco_id=?", (*kwargs.values(), foco_id))

def delete_foco(foco_id, email_autor):
    _log_cambio("foco", foco_id, "estado", "Activo", "Eliminado", email_autor)
    with get_db() as conn:
        conn.execute("UPDATE focos SET estado='Eliminado' WHERE foco_id=?", (foco_id,))

def recalc_foco_progreso(foco_id):
    """Recalcula progreso del foco basado en promedio de KRs"""
    with get_db() as conn:
        krs = conn.execute("SELECT progreso FROM krs WHERE foco_id=? AND estado!='Eliminado'", (foco_id,)).fetchall()
        if krs:
            avg = round(sum(r[0] for r in krs) / len(krs))
            conn.execute("UPDATE focos SET progreso=? WHERE foco_id=?", (avg, foco_id))
            return avg
    return 0

# ── KEY RESULTS ──
def create_kr(foco_id, nombre, meta_valor, unidad_medida, periodicidad, fecha_limite):
    kid = f"KR_{int(datetime.now().timestamp()*1000)}"
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("INSERT INTO krs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (kid, foco_id, nombre, meta_valor, 0, unidad_medida, 0, "En Progreso", periodicidad, now, fecha_limite))
    return kid

def get_krs_by_foco(foco_id):
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM krs WHERE foco_id=? AND estado!='Eliminado' ORDER BY fecha_creacion",
            (foco_id,)).fetchall())

def update_kr(kr_id, email_autor, **kwargs):
    foco_to_recalc = None
    with get_db() as conn:
        old = dict_row(conn.execute("SELECT * FROM krs WHERE kr_id=?", (kr_id,)).fetchone())
        if old:
            for k, v in kwargs.items():
                if str(old.get(k)) != str(v):
                    _log_cambio("kr", kr_id, k, old.get(k), v, email_autor)
            foco_to_recalc = old["foco_id"]
        sets = ", ".join(f"{k}=?" for k in kwargs)
        conn.execute(f"UPDATE krs SET {sets} WHERE kr_id=?", (*kwargs.values(), kr_id))
    if foco_to_recalc:
        recalc_foco_progreso(foco_to_recalc)

def delete_kr(kr_id, email_autor):
    _log_cambio("kr", kr_id, "estado", "Activo", "Eliminado", email_autor)
    foco_to_recalc = None
    with get_db() as conn:
        row = conn.execute("SELECT foco_id FROM krs WHERE kr_id=?", (kr_id,)).fetchone()
        conn.execute("UPDATE krs SET estado='Eliminado' WHERE kr_id=?", (kr_id,))
        if row:
            foco_to_recalc = row[0]
    if foco_to_recalc:
        recalc_foco_progreso(foco_to_recalc)

def recalc_kr_progreso(kr_id):
    """Recalcula progreso del KR basado en promedio de tareas"""
    with get_db() as conn:
        tareas = conn.execute("SELECT progreso FROM tareas WHERE kr_id=? AND estado!='Eliminado'", (kr_id,)).fetchall()
        if tareas:
            avg = round(sum(r[0] for r in tareas) / len(tareas))
            conn.execute("UPDATE krs SET progreso=? WHERE kr_id=?", (avg, kr_id))
            row = conn.execute("SELECT foco_id FROM krs WHERE kr_id=?", (kr_id,)).fetchone()
            if row:
                # Inline recalc foco to avoid nested connection
                foco_id = row[0]
                krs = conn.execute("SELECT progreso FROM krs WHERE foco_id=? AND estado!='Eliminado'", (foco_id,)).fetchall()
                if krs:
                    favg = round(sum(r[0] for r in krs) / len(krs))
                    conn.execute("UPDATE focos SET progreso=? WHERE foco_id=?", (favg, foco_id))
            return avg
    return 0

# ── TAREAS ──
def create_tarea(kr_id, foco_id, titulo, descripcion, email_responsable, fecha_inicio, fecha_limite, prioridad, email_creador):
    tid = f"TAR_{int(datetime.now().timestamp()*1000)}"
    now = datetime.now().isoformat()
    with get_db() as conn:
        nombre_resp = ""
        row = conn.execute("SELECT nombre FROM identidad WHERE email=?", (email_responsable,)).fetchone()
        if row:
            nombre_resp = row[0]
        conn.execute("INSERT INTO tareas VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, kr_id, foco_id, titulo, descripcion, email_responsable, nombre_resp,
             fecha_inicio, fecha_limite, None, "Pendiente", prioridad, 0, "",
             now, now, email_creador))
    return tid

def get_tareas_by_kr(kr_id):
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM tareas WHERE kr_id=? AND estado!='Eliminado' ORDER BY fecha_limite",
            (kr_id,)).fetchall())

def get_tareas_by_foco(foco_id):
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM tareas WHERE foco_id=? AND estado!='Eliminado' ORDER BY fecha_limite",
            (foco_id,)).fetchall())

def get_mis_tareas(email):
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT t.*, f.nombre as foco_nombre, k.nombre as kr_nombre FROM tareas t "
            "LEFT JOIN focos f ON t.foco_id = f.foco_id "
            "LEFT JOIN krs k ON t.kr_id = k.kr_id "
            "WHERE t.email_responsable=? AND t.estado NOT IN ('Eliminado','Completado') "
            "ORDER BY t.fecha_limite", (email,)).fetchall())

def update_tarea(tarea_id, email_autor, **kwargs):
    kr_to_recalc = None
    with get_db() as conn:
        old = dict_row(conn.execute("SELECT * FROM tareas WHERE tarea_id=?", (tarea_id,)).fetchone())
        if old:
            for k, v in kwargs.items():
                if str(old.get(k)) != str(v):
                    _log_cambio("tarea", tarea_id, k, old.get(k), v, email_autor)
            kr_to_recalc = old["kr_id"]
        kwargs["ultimo_cambio"] = datetime.now().isoformat()
        kwargs["cambiado_por"] = email_autor
        if kwargs.get("estado") == "Completado" and (not old or old.get("estado") != "Completado"):
            kwargs["fecha_completada"] = datetime.now().isoformat()
            kwargs["progreso"] = 100
        sets = ", ".join(f"{k}=?" for k in kwargs)
        conn.execute(f"UPDATE tareas SET {sets} WHERE tarea_id=?", (*kwargs.values(), tarea_id))
    if kr_to_recalc:
        recalc_kr_progreso(kr_to_recalc)

def delete_tarea(tarea_id, email_autor):
    _log_cambio("tarea", tarea_id, "estado", "Activo", "Eliminado", email_autor)
    kr_to_recalc = None
    with get_db() as conn:
        row = conn.execute("SELECT kr_id FROM tareas WHERE tarea_id=?", (tarea_id,)).fetchone()
        conn.execute("UPDATE tareas SET estado='Eliminado' WHERE tarea_id=?", (tarea_id,))
        if row:
            kr_to_recalc = row[0]
    if kr_to_recalc:
        recalc_kr_progreso(kr_to_recalc)

# ── HISTORIAL ──
def get_historial(entidad_id, limit=20):
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM historial_cambios WHERE entidad_id=? ORDER BY fecha DESC LIMIT ?",
            (entidad_id, limit)).fetchall())

# ── ANALYTICS ESTRATÉGICO ──
def get_strategic_stats(unidad):
    with get_db() as conn:
        focos = conn.execute("SELECT COUNT(*) FROM focos WHERE unidad=? AND estado!='Eliminado'", (unidad,)).fetchone()[0]
        avg_prog = conn.execute("SELECT AVG(progreso) FROM focos WHERE unidad=? AND estado!='Eliminado'", (unidad,)).fetchone()[0] or 0
        tareas_total = conn.execute(
            "SELECT COUNT(*) FROM tareas t JOIN focos f ON t.foco_id=f.foco_id WHERE f.unidad=? AND t.estado!='Eliminado'",
            (unidad,)).fetchone()[0]
        tareas_vencidas = conn.execute(
            "SELECT COUNT(*) FROM tareas t JOIN focos f ON t.foco_id=f.foco_id "
            "WHERE f.unidad=? AND t.estado NOT IN ('Completado','Eliminado') AND t.fecha_limite < ?",
            (unidad, datetime.now().strftime("%Y-%m-%d"))).fetchone()[0]
        return {"focos": focos, "avg_progreso": round(avg_prog), "tareas_total": tareas_total, "tareas_vencidas": tareas_vencidas}

# ── ANALYTICS (Admin) ──
def get_analytics():
    with get_db() as db:
        total_users = db.execute("SELECT COUNT(*) FROM usuarios WHERE estado='Activo'").fetchone()[0]
        checkins_week = db.execute("SELECT COUNT(*) FROM checkins WHERE semana=?",
            (f"{datetime.now().year}-S{datetime.now().isocalendar()[1]:02d}",)).fetchone()[0]
        avg_estres = db.execute("SELECT AVG(nivel_estres) FROM checkins WHERE fecha > ?",
            ((datetime.now() - timedelta(days=7)).isoformat(),)).fetchone()[0] or 0
        alertas = db.execute("SELECT COUNT(*) FROM checkins WHERE alerta_enviada=1 AND fecha > ?",
            ((datetime.now() - timedelta(days=7)).isoformat(),)).fetchone()[0]
        faros_mes = db.execute("SELECT COUNT(*) FROM faros WHERE fecha_envio > ?",
            ((datetime.now() - timedelta(days=30)).isoformat(),)).fetchone()[0]
        total_faros = db.execute("SELECT COUNT(*) FROM faros").fetchone()[0]
        return {
            "total_users": total_users, "checkins_week": checkins_week,
            "avg_estres": round(avg_estres, 1), "alertas": alertas,
            "faros_mes": faros_mes, "total_faros": total_faros,
            "tasa_checkin": round((checkins_week / max(total_users, 1)) * 100),
        }

# ═══════════════════════════════════════════
# ADMIN: GESTIÓN DE COLABORADORES
# ═══════════════════════════════════════════

def update_password(email, new_password):
    """Actualizar contraseña de un usuario"""
    hashed_password = generate_password_hash(new_password)
    with get_db() as db:
        db.execute("UPDATE usuarios SET password=? WHERE email=?", (hashed_password, email))

def add_colaborador(email, nombre, rol, unidad, email_lider, cargo, telefono, fecha_ingreso):
    """Agregar un nuevo colaborador (desde panel admin)"""
    now = datetime.now().isoformat()
    default_hash = generate_password_hash('Itaca2026!')
    with get_db() as conn:
        existing = conn.execute("SELECT 1 FROM usuarios WHERE email=?", (email,)).fetchone()
        if existing:
            return False, "Ya existe un usuario con ese email."
        conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?,?)",
            (email, nombre, rol, "Activo", unidad, email_lider, now, now, default_hash))
        conn.execute("""INSERT INTO identidad
            (email,nombre,puesto,rol,unidad,estado,email_lider,telefono,fecha_ingreso,fecha_actualizacion)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (email, nombre, cargo, rol, unidad, "Activo", email_lider, telefono, fecha_ingreso, now))
    return True, f"✅ {nombre} agregado exitosamente."

def deactivate_colaborador(email):
    """Desactivar un colaborador (no se borra, se marca inactivo)"""
    with get_db() as conn:
        conn.execute("UPDATE usuarios SET estado='Inactivo' WHERE email=?", (email,))
        conn.execute("UPDATE identidad SET estado='Inactivo' WHERE email=?", (email,))
    return True, "Colaborador desactivado."

def reactivate_colaborador(email):
    """Reactivar un colaborador"""
    with get_db() as conn:
        conn.execute("UPDATE usuarios SET estado='Activo' WHERE email=?", (email,))
        conn.execute("UPDATE identidad SET estado='Activo' WHERE email=?", (email,))
    return True, "Colaborador reactivado."

def update_colaborador(email, **kwargs):
    """Actualizar datos de un colaborador (nombre, rol, unidad, etc.)"""
    with get_db() as conn:
        # Update usuarios
        user_fields = {k: v for k, v in kwargs.items() if k in ("nombre","rol","unidad","email_lider")}
        if user_fields:
            sets = ", ".join(f"{k}=?" for k in user_fields)
            conn.execute(f"UPDATE usuarios SET {sets} WHERE email=?", (*user_fields.values(), email))
        # Update identidad
        ident_fields = {k: v for k, v in kwargs.items() if k in ("nombre","rol","unidad","email_lider","puesto","telefono")}
        if ident_fields:
            sets = ", ".join(f"{k}=?" for k in ident_fields)
            conn.execute(f"UPDATE identidad SET {sets}, fecha_actualizacion=? WHERE email=?",
                (*ident_fields.values(), datetime.now().isoformat(), email))

def reset_password(email):
    """Resetear contraseña a la default"""
    default_hash = generate_password_hash('Itaca2026!')
    with get_db() as conn:
        conn.execute("UPDATE usuarios SET password=? WHERE email=?", (default_hash, email))
    return True, "Contraseña reseteada a Itaca2026!"

def get_all_users_admin():
    """Obtener TODOS los usuarios (activos e inactivos) para el panel admin"""
    with get_db() as conn:
        return dict_rows(conn.execute("""
            SELECT u.*, i.puesto, i.telefono, i.fecha_ingreso
            FROM usuarios u
            LEFT JOIN identidad i ON u.email = i.email
            ORDER BY u.estado DESC, u.unidad, u.nombre""").fetchall())

def get_units():
    """Obtener lista de unidades únicas"""
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT unidad FROM usuarios WHERE unidad IS NOT NULL AND unidad != '' ORDER BY unidad").fetchall()
        return [r[0] for r in rows]


# ═══════════════════════════════════════════════════════════════
# NUEVOS MÓDULOS v2.0: ESCUDO DE ESPARTA
# ═══════════════════════════════════════════════════════════════

def check_escudo_esparta(email_responsable):
    """
    🛡️ ESCUDO DE ESPARTA (Anti-Burnout):
    Si último estrés == 5 AND tareas vencidas > 3 → bloquear asignación
    Retorna: (bloqueado: bool, mensaje: str, nombre: str)
    """
    with get_db() as conn:
        ci = conn.execute(
            "SELECT nivel_estres FROM checkins WHERE email=? ORDER BY fecha DESC LIMIT 1",
            (email_responsable,)).fetchone()
        if not ci:
            return False, "", ""
        hoy = datetime.now().strftime("%Y-%m-%d")
        vencidas = conn.execute(
            "SELECT COUNT(*) FROM tareas WHERE email_responsable=? "
            "AND estado NOT IN ('Completado','Eliminado') AND fecha_limite < ?",
            (email_responsable, hoy)).fetchone()[0]
        nombre_row = conn.execute(
            "SELECT nombre FROM identidad WHERE email=?",
            (email_responsable,)).fetchone()
        nombre = nombre_row[0] if nombre_row else email_responsable
        if ci[0] == 5 and vencidas > 3:
            return True, (
                f"🛡️ Escudo de Esparta Activado: {nombre} superó su límite "
                f"(Estrés 5/5, {vencidas} tareas vencidas). "
                f"Reasigna a otro tripulante."
            ), nombre
    return False, "", ""


# ═══════════════════════════════════════════════════════════════
# PUESTOS / PERFILES DISC (Semáforo de Encaje)
# ═══════════════════════════════════════════════════════════════

def get_all_puestos():
    """Obtener todos los perfiles de puesto"""
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM puestos_perfiles ORDER BY nombre_puesto").fetchall())

def get_puesto_perfil(nombre_puesto):
    """Obtener perfil DISC ideal para un puesto"""
    with get_db() as db:
        return dict_row(db.execute(
            "SELECT * FROM puestos_perfiles WHERE nombre_puesto=?",
            (nombre_puesto,)).fetchone())

def add_puesto_perfil(nombre_puesto, disc_principal, disc_secundario, unidad, descripcion):
    """Agregar un perfil de puesto"""
    pid = f"PU_{int(datetime.now().timestamp()*1000)}"
    with get_db() as db:
        db.execute("INSERT INTO puestos_perfiles VALUES (?,?,?,?,?,?)",
            (pid, nombre_puesto, disc_principal, disc_secundario, unidad, descripcion))
    return pid

def get_encaje_disc(email):
    """
    Semáforo de Encaje DISC:
    Cruza el DISC del colaborador vs el DISC ideal del puesto
    Retorna: {"color": "Verde/Amarillo/Rojo", "emoji", "msg", "score"}
    """
    ident = get_identidad(email)
    if not ident or not ident.get("arquetipo_disc"):
        return None
    puesto_nombre = ident.get("puesto", "")
    perfil = get_puesto_perfil(puesto_nombre)
    if not perfil:
        return None
    disc_p = ident.get("arquetipo_disc", "")
    disc_s = ident.get("arquetipo_secundario", "")
    ideal_p = perfil.get("disc_ideal_principal", "")
    ideal_s = perfil.get("disc_ideal_secundario", "")
    score = 0
    if disc_p == ideal_p: score += 2
    elif disc_p == ideal_s: score += 1
    if disc_s == ideal_s: score += 1
    elif disc_s == ideal_p: score += 1
    if score >= 3:
        return {"color": "Verde", "emoji": "🟢", "msg": "Encaje ideal", "score": score}
    elif score >= 1:
        return {"color": "Amarillo", "emoji": "🟡", "msg": "Encaje parcial – explorar", "score": score}
    else:
        return {"color": "Rojo", "emoji": "🔴", "msg": "Desencaje – revisar reubicación", "score": score}


# ═══════════════════════════════════════════════════════════════
# TORRE DE CONTROL: ORÁCULO DE FUGAS + MATRIZ 9-BOX
# ═══════════════════════════════════════════════════════════════

def get_flight_risk():
    """
    🔮 ORÁCULO DE FUGAS (Flight Risk):
    Condición: estrés promedio >= 4 (últimas 2 semanas)
                AND 0 faros (enviados+recibidos) último mes
                AND > 2 tareas vencidas
    """
    hoy = datetime.now()
    hace_14d = (hoy - timedelta(days=14)).isoformat()
    hace_30d = (hoy - timedelta(days=30)).isoformat()
    hoy_str = hoy.strftime("%Y-%m-%d")
    with get_db() as conn:
        users = dict_rows(conn.execute(
            "SELECT email, nombre, unidad, puesto FROM identidad WHERE estado='Activo'"
        ).fetchall())
        risk_list = []
        for u in users:
            e = u["email"]
            avg_row = conn.execute(
                "SELECT AVG(nivel_estres) FROM checkins WHERE email=? AND fecha >= ?",
                (e, hace_14d)).fetchone()
            avg_estres = avg_row[0] if avg_row[0] else 0
            faros_env = conn.execute(
                "SELECT COUNT(*) FROM faros WHERE email_emisor=? AND fecha_envio >= ?",
                (e, hace_30d)).fetchone()[0]
            faros_rec = conn.execute(
                "SELECT COUNT(*) FROM faros WHERE email_receptor=? AND fecha_envio >= ?",
                (e, hace_30d)).fetchone()[0]
            vencidas = conn.execute(
                "SELECT COUNT(*) FROM tareas WHERE email_responsable=? "
                "AND estado NOT IN ('Completado','Eliminado') AND fecha_limite < ?",
                (e, hoy_str)).fetchone()[0]
            if avg_estres >= 4 and (faros_env + faros_rec) == 0 and vencidas > 2:
                risk_list.append({
                    **u, "avg_estres": round(avg_estres, 1),
                    "faros_total": faros_env + faros_rec,
                    "tareas_vencidas": vencidas, "riesgo": "ALTO"
                })
        return risk_list

def get_9box_data():
    """
    📊 MATRIZ 9-BOX:
    Eje X = Desempeño (promedio progreso tareas)
    Eje Y = Potencial (promedio eval 360 + faros recibidos)
    """
    with get_db() as conn:
        users = dict_rows(conn.execute(
            "SELECT email, nombre, unidad FROM identidad WHERE estado='Activo'"
        ).fetchall())
        data = []
        for u in users:
            e = u["email"]
            desemp = conn.execute(
                "SELECT AVG(progreso) FROM tareas "
                "WHERE email_responsable=? AND estado!='Eliminado'",
                (e,)).fetchone()[0] or 0
            avg_360 = conn.execute(
                "SELECT AVG(promedio) FROM eval_360 WHERE email_evaluado=?",
                (e,)).fetchone()[0] or 0
            faros_rec = conn.execute(
                "SELECT COUNT(*) FROM faros WHERE email_receptor=? AND fecha_envio > ?",
                (e, (datetime.now() - timedelta(days=90)).isoformat())).fetchone()[0]
            potencial = (avg_360 * 20) + min(faros_rec * 5, 20)
            if desemp > 0 or potencial > 0:
                d_level = "Alto" if desemp >= 70 else "Medio" if desemp >= 40 else "Bajo"
                p_level = "Alto" if potencial >= 70 else "Medio" if potencial >= 40 else "Bajo"
                data.append({
                    "email": e, "nombre": u["nombre"], "unidad": u["unidad"],
                    "desempeno": round(desemp, 1), "potencial": round(potencial, 1),
                    "d_level": d_level, "p_level": p_level,
                    "box": f"{p_level} Potencial / {d_level} Desempeño"
                })
        return data


# ═══════════════════════════════════════════════════════════════
# CRM — EL PUERTO
# ═══════════════════════════════════════════════════════════════

def create_lead(telefono, nombre_apoderado, nombre_nino, edad, ciudad,
                origen, precalificacion, unidad, email_asesor, notas=""):
    """Crear un nuevo lead en el pipeline"""
    lid = f"LEAD_{int(datetime.now().timestamp()*1000)}"
    now = datetime.now().isoformat()
    with get_db() as db:
        db.execute("INSERT INTO crm_leads VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (lid, telefono, nombre_apoderado, nombre_nino, edad, ciudad,
             origen, precalificacion, "Nuevo", unidad, notas, email_asesor, now, now))
    return lid

def get_leads(unidad=None, estado=None):
    """Obtener leads filtrados por unidad y/o estado"""
    with get_db() as db:
        q = "SELECT * FROM crm_leads WHERE 1=1"
        params = []
        if unidad:
            q += " AND unidad=?"
            params.append(unidad)
        if estado:
            q += " AND estado=?"
            params.append(estado)
        return dict_rows(db.execute(q + " ORDER BY fecha_creacion DESC", params).fetchall())

def get_lead(lead_id):
    """Obtener un lead por ID"""
    with get_db() as db:
        return dict_row(db.execute(
            "SELECT * FROM crm_leads WHERE lead_id=?", (lead_id,)).fetchone())

def update_lead(lead_id, **kwargs):
    """Actualizar campos de un lead"""
    kwargs["fecha_actualizacion"] = datetime.now().isoformat()
    with get_db() as db:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        db.execute(f"UPDATE crm_leads SET {sets} WHERE lead_id=?",
                   (*kwargs.values(), lead_id))

def inscribir_lead(lead_id, monto_total, num_cuotas):
    """
    Lead → Inscrito: genera cuotas automáticamente.
    Cuando una cuota se pague, ingresará a finanzas_flujo.
    """
    update_lead(lead_id, estado="Inscrito")
    lead = get_lead(lead_id)
    if not lead:
        return
    monto_cuota = round(monto_total / num_cuotas, 2)
    for i in range(1, num_cuotas + 1):
        cid = f"CUO_{int(datetime.now().timestamp()*1000)}_{i}"
        fecha_venc = (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m-%d")
        with get_db() as db:
            db.execute("INSERT INTO ventas_cuotas VALUES (?,?,?,?,?,?,?,?)",
                (cid, lead_id, i, monto_cuota, 0, fecha_venc, None, "Pendiente"))

def pagar_cuota(cuota_id, monto_pagado):
    """
    Pagar cuota → ingresa automáticamente a finanzas_flujo como Ingreso.
    """
    with get_db() as db:
        cuota = dict_row(db.execute(
            "SELECT * FROM ventas_cuotas WHERE cuota_id=?", (cuota_id,)).fetchone())
        if not cuota:
            return False
        db.execute(
            "UPDATE ventas_cuotas SET monto_pagado=?, fecha_pago=?, estado='Pagado' WHERE cuota_id=?",
            (monto_pagado, datetime.now().isoformat(), cuota_id))
        # Buscar unidad del lead
        lead = dict_row(db.execute(
            "SELECT * FROM crm_leads WHERE lead_id=?", (cuota["lead_id"],)).fetchone())
        unidad = lead["unidad"] if lead else ""
        # Auto-registro en finanzas
        fid = f"FIN_{int(datetime.now().timestamp()*1000)}"
        db.execute("INSERT INTO finanzas_flujo VALUES (?,?,?,?,?,?,?,?,?,?)",
            (fid, unidad, "Ingreso", "Cuota", monto_pagado,
             datetime.now().strftime("%Y-%m-%d"), "",
             f"Cuota {cuota['numero_cuota']} - Lead {cuota['lead_id']}",
             "", datetime.now().isoformat()))
    return True

def get_cuotas_by_lead(lead_id):
    """Obtener todas las cuotas de un lead"""
    with get_db() as db:
        return dict_rows(db.execute(
            "SELECT * FROM ventas_cuotas WHERE lead_id=? ORDER BY numero_cuota",
            (lead_id,)).fetchall())


# ═══════════════════════════════════════════════════════════════
# FINANZAS — LA BÓVEDA
# ═══════════════════════════════════════════════════════════════

def add_flujo_financiero(unidad, tipo, categoria, monto, fecha, campana,
                         descripcion, registrado_por):
    """Registrar un movimiento financiero"""
    fid = f"FIN_{int(datetime.now().timestamp()*1000)}"
    with get_db() as db:
        db.execute("INSERT INTO finanzas_flujo VALUES (?,?,?,?,?,?,?,?,?,?)",
            (fid, unidad, tipo, categoria, monto, fecha, campana,
             descripcion, registrado_por, datetime.now().isoformat()))
    return fid

def get_flujos(unidad=None, tipo=None, dias=30):
    """Obtener flujos financieros filtrados"""
    with get_db() as db:
        q = "SELECT * FROM finanzas_flujo WHERE fecha >= ?"
        params = [(datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")]
        if unidad:
            q += " AND unidad=?"
            params.append(unidad)
        if tipo:
            q += " AND tipo=?"
            params.append(tipo)
        return dict_rows(db.execute(q + " ORDER BY fecha DESC", params).fetchall())

def get_resumen_financiero(unidad=None, dias=30):
    """Resumen: ingresos, egresos, balance, movimientos"""
    flujos = get_flujos(unidad, dias=dias)
    ingresos = sum(f["monto"] for f in flujos if f["tipo"] == "Ingreso")
    egresos = sum(f["monto"] for f in flujos if f["tipo"] == "Egreso")
    return {
        "ingresos": ingresos, "egresos": egresos,
        "balance": ingresos - egresos, "movimientos": len(flujos)
    }


# ═══════════════════════════════════════════════════════════════
# PLAN ESTRATÉGICO ERM
# ═══════════════════════════════════════════════════════════════

def get_plan_estrategico(unidad):
    """Obtener plan estratégico de una unidad"""
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM planes_estrategicos WHERE unidad=? ORDER BY id",
            (unidad,)).fetchall())

def get_planes_todas_unidades():
    """Obtener todos los planes estratégicos"""
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM planes_estrategicos ORDER BY unidad, id").fetchall())

def save_plan_estrategico(rows, unidad, email_autor):
    """Guardar plan: borra filas de esa unidad e inserta las nuevas."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("DELETE FROM planes_estrategicos WHERE unidad=?", (unidad,))
        for r in rows:
            conn.execute("""INSERT INTO planes_estrategicos
                (unidad, foco_estrategico, objetivo, kr, actividad_clave,
                 fecha_creacion, creado_por)
                VALUES (?,?,?,?,?,?,?)""",
                (unidad, r.get("foco_estrategico",""), r.get("objetivo",""),
                 r.get("kr",""), r.get("actividad_clave",""),
                 now, email_autor))

def get_focos_unicos(unidad):
    """Obtener lista de focos únicos de una unidad (para dropdown de sprints)"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT foco_estrategico FROM planes_estrategicos WHERE unidad=? AND foco_estrategico!=''",
            (unidad,)).fetchall()
        return [r[0] for r in rows]

def get_sprints(unidad):
    """Obtener sprints/tareas de una unidad"""
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM seguimiento_sprints WHERE unidad=? ORDER BY id",
            (unidad,)).fetchall())

def save_sprints(rows, unidad):
    """Guardar sprints: borra filas de esa unidad e inserta las nuevas."""
    with get_db() as conn:
        conn.execute("DELETE FROM seguimiento_sprints WHERE unidad=?", (unidad,))
        for r in rows:
            conn.execute("""INSERT INTO seguimiento_sprints
                (unidad, foco_relacionado, tarea, responsable, fecha_limite, estatus, avance)
                VALUES (?,?,?,?,?,?,?)""",
                (unidad, r.get("foco_relacionado",""), r.get("tarea",""),
                 r.get("responsable",""), r.get("fecha_limite",""),
                 r.get("estatus","Pendiente"), int(r.get("avance", 0) or 0)))

def delete_plan_fila(fila_id):
    """Eliminar una fila del plan estratégico"""
    with get_db() as conn:
        conn.execute("DELETE FROM planes_estrategicos WHERE id=?", (fila_id,))

def get_metas_mensuales(unidad):
    """Obtener metas mensuales de una unidad"""
    with get_db() as conn:
        return dict_rows(conn.execute(
            "SELECT * FROM metas_mensuales WHERE unidad=? ORDER BY id",
            (unidad,)).fetchall())

def save_metas_mensuales(rows, unidad):
    """Guardar metas mensuales: delete + insert"""
    with get_db() as conn:
        conn.execute("DELETE FROM metas_mensuales WHERE unidad=?", (unidad,))
        for r in rows:
            conn.execute("""INSERT INTO metas_mensuales
                (unidad, programa, precio_unitario,
                 meta_ene, real_ene, meta_feb, real_feb, meta_mar, real_mar,
                 meta_abr, real_abr, meta_may, real_may, meta_jun, real_jun,
                 meta_jul, real_jul, meta_ago, real_ago, meta_sep, real_sep,
                 meta_oct, real_oct, meta_nov, real_nov, meta_dic, real_dic)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (unidad, r.get("programa",""), float(r.get("precio_unitario",0) or 0),
                 int(r.get("meta_ene",0) or 0), int(r.get("real_ene",0) or 0),
                 int(r.get("meta_feb",0) or 0), int(r.get("real_feb",0) or 0),
                 int(r.get("meta_mar",0) or 0), int(r.get("real_mar",0) or 0),
                 int(r.get("meta_abr",0) or 0), int(r.get("real_abr",0) or 0),
                 int(r.get("meta_may",0) or 0), int(r.get("real_may",0) or 0),
                 int(r.get("meta_jun",0) or 0), int(r.get("real_jun",0) or 0),
                 int(r.get("meta_jul",0) or 0), int(r.get("real_jul",0) or 0),
                 int(r.get("meta_ago",0) or 0), int(r.get("real_ago",0) or 0),
                 int(r.get("meta_sep",0) or 0), int(r.get("real_sep",0) or 0),
                 int(r.get("meta_oct",0) or 0), int(r.get("real_oct",0) or 0),
                 int(r.get("meta_nov",0) or 0), int(r.get("real_nov",0) or 0),
                 int(r.get("meta_dic",0) or 0), int(r.get("real_dic",0) or 0)))


# ═══════════════════════════════════════════════════════════════════
# ÍTACA PLAY — Capacitaciones Gamificadas con YouTube
# ═══════════════════════════════════════════════════════════════════

def _extract_youtube_id(url: str) -> str:
    import re
    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else url

def add_play_curso(titulo, descripcion, youtube_url, categoria, dificultad,
                   puntos, badge_nombre, badge_icono, palabra_clave,
                   pregunta, opcion_a, opcion_b, opcion_c, opcion_d,
                   respuesta_correcta, creado_por, orden=0):
    cid = f"PLAY_{int(datetime.now().timestamp()*1000)}"
    yt_id = _extract_youtube_id(youtube_url)
    with get_db() as db:
        db.execute("""INSERT INTO itaca_play_cursos VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,0)""",
            (cid, titulo, descripcion, youtube_url, yt_id, categoria, dificultad,
             puntos, badge_nombre, badge_icono, palabra_clave.strip().lower(),
             pregunta, opcion_a, opcion_b, opcion_c, opcion_d,
             respuesta_correcta, orden, creado_por, datetime.now().isoformat()))
    return cid

def get_play_cursos(solo_activos=True):
    with get_db() as db:
        q = "SELECT * FROM itaca_play_cursos"
        if solo_activos: q += " WHERE activo=1"
        q += " ORDER BY orden ASC, fecha_creacion DESC"
        return dict_rows(db.execute(q).fetchall())

def get_play_curso(curso_id):
    with get_db() as db:
        r = db.execute("SELECT * FROM itaca_play_cursos WHERE curso_id=?", (curso_id,)).fetchone()
        return dict(r) if r else None

def get_play_progreso_usuario(email):
    with get_db() as db:
        rows = db.execute(
            "SELECT curso_id, aprobado, puntos_ganados, intento_num FROM itaca_play_intentos WHERE email=?",
            (email,)).fetchall()
        return {r["curso_id"]: dict(r) for r in rows}

def curso_aprobado(email, curso_id) -> bool:
    with get_db() as db:
        return db.execute(
            "SELECT aprobado FROM itaca_play_intentos WHERE email=? AND curso_id=? AND aprobado=1",
            (email, curso_id)).fetchone() is not None

def submit_play_intento(email, curso_id, palabra_ingresada, respuesta_dada):
    curso = get_play_curso(curso_id)
    if not curso: return {"ok": False, "msg": "Curso no encontrado."}
    if curso_aprobado(email, curso_id): return {"ok": False, "msg": "Ya completaste este curso. 🎉"}
    with get_db() as db:
        num = db.execute("SELECT COUNT(*) FROM itaca_play_intentos WHERE email=? AND curso_id=?",
                         (email, curso_id)).fetchone()[0] + 1
    pal_ok = palabra_ingresada.strip().lower() == curso["palabra_clave"].strip().lower()
    resp_ok = respuesta_dada.strip().upper() == curso["respuesta_correcta"].strip().upper()
    aprobado = pal_ok and resp_ok
    puntos = curso["puntos"] if aprobado else 0
    iid = f"INT_{email.split('@')[0]}_{curso_id}_{int(datetime.now().timestamp()*1000)}"
    with get_db() as db:
        db.execute("INSERT INTO itaca_play_intentos VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (iid, email, curso_id, palabra_ingresada, int(pal_ok),
             respuesta_dada, int(resp_ok), int(aprobado), puntos,
             datetime.now().isoformat(), num))
        db.execute("UPDATE itaca_play_cursos SET vistas=vistas+1 WHERE curso_id=?", (curso_id,))
    if aprobado:
        otorgar_badge(email, f"PLAY_{curso_id}",
                      curso.get("badge_nombre") or f"🎬 {curso['titulo']}",
                      f"Completaste: {curso['titulo']}", puntos, "Ítaca Play",
                      curso.get("badge_icono", "🎬"))
        _notif_interna(email, "play", "🎬 ¡Curso completado!",
                       f"Aprobaste '{curso['titulo']}' y ganaste {puntos} puntos.")
    return {"ok": True, "aprobado": aprobado, "pal_ok": pal_ok,
            "resp_ok": resp_ok, "puntos": puntos, "intento_num": num}

def toggle_play_curso(curso_id, activo: bool):
    with get_db() as db:
        db.execute("UPDATE itaca_play_cursos SET activo=? WHERE curso_id=?", (int(activo), curso_id))

def delete_play_curso(curso_id):
    with get_db() as db:
        db.execute("DELETE FROM itaca_play_cursos WHERE curso_id=?", (curso_id,))

def get_play_stats_admin():
    with get_db() as db:
        total_cursos = db.execute("SELECT COUNT(*) FROM itaca_play_cursos WHERE activo=1").fetchone()[0]
        total_aprobados = db.execute("SELECT COUNT(*) FROM itaca_play_intentos WHERE aprobado=1").fetchone()[0]
        total_intentos = db.execute("SELECT COUNT(*) FROM itaca_play_intentos").fetchone()[0]
        top = dict_rows(db.execute("""
            SELECT c.titulo, COUNT(i.intento_id) as intentos, SUM(i.aprobado) as aprobados
            FROM itaca_play_cursos c LEFT JOIN itaca_play_intentos i ON c.curso_id=i.curso_id
            GROUP BY c.curso_id ORDER BY aprobados DESC LIMIT 5""").fetchall())
        ranking = dict_rows(db.execute("""
            SELECT u.nombre, u.unidad, COUNT(i.intento_id) as cursos_completados,
                   SUM(i.puntos_ganados) as puntos_play
            FROM itaca_play_intentos i JOIN usuarios u ON i.email=u.email
            WHERE i.aprobado=1 GROUP BY i.email
            ORDER BY cursos_completados DESC, puntos_play DESC LIMIT 10""").fetchall())
    return {"total_cursos": total_cursos, "total_aprobados": total_aprobados,
            "total_intentos": total_intentos, "top_cursos": top, "ranking": ranking}

def seed_play_cursos():
    with get_db() as db:
        if db.execute("SELECT COUNT(*) FROM itaca_play_cursos").fetchone()[0] > 0: return
    cursos = [
        {"titulo":"Liderazgo Gung Ho: El Espíritu de la Ardilla","descripcion":"El primer pilar Gung Ho aplicado al liderazgo diario.",
         "youtube_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","categoria":"Liderazgo","dificultad":"Básico","puntos":100,
         "badge_nombre":"🐿️ Espíritu Ardilla","badge_icono":"🐿️","palabra_clave":"valor",
         "pregunta":"¿Cuál es el principio del Espíritu de la Ardilla?",
         "opcion_a":"El trabajo debe ser rápido","opcion_b":"El trabajo debe ser VALIOSO",
         "opcion_c":"El trabajo individual es lo más importante","opcion_d":"La eficiencia es el único objetivo",
         "respuesta_correcta":"B","orden":1},
        {"titulo":"Inteligencia Emocional en el Trabajo","descripcion":"Las 5 competencias de Goleman aplicadas.",
         "youtube_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","categoria":"IE","dificultad":"Intermedio","puntos":150,
         "badge_nombre":"🧠 Capitán Emocional","badge_icono":"🧠","palabra_clave":"empatia",
         "pregunta":"¿Cuántas competencias tiene la IE según Goleman?",
         "opcion_a":"3","opcion_b":"4","opcion_c":"5","opcion_d":"6",
         "respuesta_correcta":"C","orden":2},
        {"titulo":"OKRs: Metas que mueven montañas","descripcion":"Objetivos y Resultados Clave que impulsan equipos.",
         "youtube_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","categoria":"Estrategia","dificultad":"Intermedio","puntos":120,
         "badge_nombre":"🎯 Estratega Ítaca","badge_icono":"🎯","palabra_clave":"resultado",
         "pregunta":"¿Qué significa KR en OKR?",
         "opcion_a":"Key Relationship","opcion_b":"Key Result","opcion_c":"Key Resource","opcion_d":"Key Review",
         "respuesta_correcta":"B","orden":3},
        {"titulo":"Feedback Radical: Honestidad compasiva","descripcion":"Cómo dar feedback que genera crecimiento real.",
         "youtube_url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","categoria":"Comunicación","dificultad":"Avanzado","puntos":200,
         "badge_nombre":"🪿 Maestro del Ganso","badge_icono":"🪿","palabra_clave":"confianza",
         "pregunta":"¿Cuál es el ingrediente crítico para el feedback efectivo?",
         "opcion_a":"Ser directo sin importar el impacto","opcion_b":"Esperar el momento perfecto",
         "opcion_c":"Confianza mutua y seguridad psicológica","opcion_d":"Hacerlo siempre en privado",
         "respuesta_correcta":"C","orden":4},
    ]
    for c in cursos:
        add_play_curso(**c, creado_por="admin@itaca.com")


# ═══════════════════════════════════════════════════════════════════
# EVALUACIÓN 360° v2
# ═══════════════════════════════════════════════════════════════════

def crear_periodo_360(nombre, trimestre, fecha_inicio, fecha_fin, creado_por):
    pid = f"P360_{int(datetime.now().timestamp()*1000)}"
    with get_db() as db:
        db.execute("UPDATE periodos_360 SET activo=0")
        db.execute("INSERT INTO periodos_360 VALUES (?,?,?,?,?,1,?,?)",
            (pid, nombre, trimestre, fecha_inicio, fecha_fin,
             creado_por, datetime.now().isoformat()))
    return pid

def get_periodo_activo():
    with get_db() as db:
        r = db.execute("SELECT * FROM periodos_360 WHERE activo=1 ORDER BY fecha_creacion DESC LIMIT 1").fetchone()
        return dict(r) if r else None

def get_all_periodos_360():
    with get_db() as db:
        return dict_rows(db.execute("SELECT * FROM periodos_360 ORDER BY fecha_creacion DESC").fetchall())

def cerrar_periodo_360(periodo_id):
    with get_db() as db:
        db.execute("UPDATE periodos_360 SET activo=0 WHERE periodo_id=?", (periodo_id,))

def save_eval_360_v2(periodo_id, email_evaluado, email_evaluador, unidad, es_auto,
                     pilar_itactividad, pilar_mas1, pilar_confianza,
                     hex_vision, hex_planificacion, hex_encaje,
                     hex_entrenamiento, hex_evaluacion, hex_reconocimiento,
                     ie_auto, ie_autor, ie_motiv, ie_empatia, ie_social,
                     fortaleza, area_mejora, comentario, evalua_hexagono=False):
    eid = f"E360V2_{int(datetime.now().timestamp()*1000)}"
    prom_pilares = round((pilar_itactividad + pilar_mas1 + pilar_confianza) / 3, 2)
    prom_hex = round((hex_vision + hex_planificacion + hex_encaje +
                       hex_entrenamiento + hex_evaluacion + hex_reconocimiento) / 6, 2) if evalua_hexagono else 0.0
    prom_ie = round((ie_auto + ie_autor + ie_motiv + ie_empatia + ie_social) / 5, 2)
    prom_total = round((prom_pilares + prom_hex + prom_ie) / 3, 2) if evalua_hexagono else round((prom_pilares + prom_ie) / 2, 2)
    with get_db() as db:
        db.execute("""INSERT INTO eval_360_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (eid, periodo_id, email_evaluado, email_evaluador, unidad, datetime.now().isoformat(),
             pilar_itactividad, pilar_mas1, pilar_confianza,
             hex_vision, hex_planificacion, hex_encaje, hex_entrenamiento, hex_evaluacion, hex_reconocimiento,
             ie_auto, ie_autor, ie_motiv, ie_empatia, ie_social,
             fortaleza, area_mejora, comentario,
             prom_pilares, prom_hex, prom_ie, prom_total, int(es_auto)))
    return eid

def has_evaluated_360_v2(email_evaluador, email_evaluado, periodo_id):
    with get_db() as db:
        return db.execute("SELECT 1 FROM eval_360_v2 WHERE email_evaluador=? AND email_evaluado=? AND periodo_id=?",
                          (email_evaluador, email_evaluado, periodo_id)).fetchone() is not None

def get_resultados_360_v2(email_evaluado, periodo_id):
    with get_db() as db:
        avgs = db.execute("""
            SELECT COUNT(*) as total_evaluadores,
                AVG(pilar_itactividad) as pilar_itactividad, AVG(pilar_mas1) as pilar_mas1,
                AVG(pilar_confianza) as pilar_confianza,
                AVG(hex_vision) as hex_vision, AVG(hex_planificacion) as hex_planificacion,
                AVG(hex_encaje) as hex_encaje, AVG(hex_entrenamiento) as hex_entrenamiento,
                AVG(hex_evaluacion) as hex_evaluacion, AVG(hex_reconocimiento) as hex_reconocimiento,
                AVG(ie_autoconocimiento) as ie_autoconocimiento, AVG(ie_autorregulacion) as ie_autorregulacion,
                AVG(ie_motivacion) as ie_motivacion, AVG(ie_empatia) as ie_empatia,
                AVG(ie_habilidades_sociales) as ie_habilidades_sociales,
                AVG(prom_pilares) as prom_pilares, AVG(prom_hexagono) as prom_hexagono,
                AVG(prom_ie) as prom_ie, AVG(prom_total) as prom_total
            FROM eval_360_v2 WHERE email_evaluado=? AND periodo_id=? AND es_autoevaluacion=0
        """, (email_evaluado, periodo_id)).fetchone()
        auto = db.execute("SELECT * FROM eval_360_v2 WHERE email_evaluado=? AND periodo_id=? AND es_autoevaluacion=1",
                          (email_evaluado, periodo_id)).fetchone()
        comentarios = db.execute("""SELECT fortaleza_principal, area_mejora, comentario FROM eval_360_v2
            WHERE email_evaluado=? AND periodo_id=? AND es_autoevaluacion=0
            AND (fortaleza_principal!='' OR area_mejora!='' OR comentario!='')""",
            (email_evaluado, periodo_id)).fetchall()
    return {"avgs": dict_row(avgs) if avgs else {},
            "auto": dict(auto) if auto else {},
            "comentarios": dict_rows(comentarios)}

def get_resultados_360_v2_admin(email_evaluado, periodo_id):
    with get_db() as db:
        rows = db.execute("""SELECT e.*, u.nombre as nombre_evaluador FROM eval_360_v2 e
            LEFT JOIN usuarios u ON e.email_evaluador = u.email
            WHERE e.email_evaluado=? AND e.periodo_id=? ORDER BY e.fecha DESC""",
            (email_evaluado, periodo_id)).fetchall()
        return dict_rows(rows)

def get_pending_evaluaciones(email_evaluador, periodo_id):
    with get_db() as db:
        unidad = db.execute("SELECT unidad FROM usuarios WHERE email=?", (email_evaluador,)).fetchone()
        if not unidad: return []
        ya = [r[0] for r in db.execute(
            "SELECT email_evaluado FROM eval_360_v2 WHERE email_evaluador=? AND periodo_id=?",
            (email_evaluador, periodo_id)).fetchall()]
        compas = db.execute("SELECT email, nombre, rol, puesto FROM identidad WHERE unidad=? AND email!=? AND estado='Activo'",
                            (unidad[0], email_evaluador)).fetchall()
        return [dict(c) for c in compas if c["email"] not in ya]

def get_equipo_resultados_lider(email_lider, periodo_id):
    with get_db() as db:
        unidad = db.execute("SELECT unidad FROM usuarios WHERE email=?", (email_lider,)).fetchone()
        if not unidad: return []
        miembros = db.execute("SELECT email, nombre FROM identidad WHERE unidad=? AND estado='Activo'", (unidad[0],)).fetchall()
        resultados = []
        for m in miembros:
            avgs = db.execute("""SELECT COUNT(*) as total, AVG(prom_total) as prom_total,
                AVG(prom_pilares) as prom_pilares, AVG(prom_ie) as prom_ie
                FROM eval_360_v2 WHERE email_evaluado=? AND periodo_id=? AND es_autoevaluacion=0""",
                (m["email"], periodo_id)).fetchone()
            resultados.append({"email": m["email"], "nombre": m["nombre"],
                "total_evaluadores": avgs["total"] if avgs else 0,
                "prom_total": round(avgs["prom_total"] or 0, 2),
                "prom_pilares": round(avgs["prom_pilares"] or 0, 2),
                "prom_ie": round(avgs["prom_ie"] or 0, 2)})
        return resultados

def get_stats_360_admin(periodo_id):
    with get_db() as db:
        top = dict_rows(db.execute("""SELECT i.nombre, i.unidad, AVG(e.prom_total) as prom
            FROM eval_360_v2 e JOIN identidad i ON e.email_evaluado=i.email
            WHERE e.periodo_id=? AND e.es_autoevaluacion=0
            GROUP BY e.email_evaluado ORDER BY prom DESC LIMIT 5""", (periodo_id,)).fetchall())
        return {
            "total_evaluadores": db.execute("SELECT COUNT(DISTINCT email_evaluador) FROM eval_360_v2 WHERE periodo_id=? AND es_autoevaluacion=0", (periodo_id,)).fetchone()[0],
            "total_evaluados": db.execute("SELECT COUNT(DISTINCT email_evaluado) FROM eval_360_v2 WHERE periodo_id=? AND es_autoevaluacion=0", (periodo_id,)).fetchone()[0],
            "total_registros": db.execute("SELECT COUNT(*) FROM eval_360_v2 WHERE periodo_id=?", (periodo_id,)).fetchone()[0],
            "top_colaboradores": top}


# ═══════════════════════════════════════════════════════════════════
# CAPACITACIONES EXTERNAS — flujo de aprobación
# ═══════════════════════════════════════════════════════════════════

def registrar_capacitacion_ext(email, nombre, tipo, institucion, horas,
                                fecha, certificado, costo_empresa, notas):
    cid = f"CAPEXT_{int(datetime.now().timestamp()*1000)}"
    with get_db() as db:
        db.execute("""INSERT INTO capacitaciones_ext
            (cap_id, email, nombre_cap, tipo, institucion, horas, fecha,
             certificado, costo_empresa, notas, estado, fecha_registro)
            VALUES (?,?,?,?,?,?,?,?,?,?,'Pendiente',?)""",
            (cid, email, nombre, tipo, institucion, horas, fecha,
             certificado, costo_empresa, notas, datetime.now().isoformat()))
    with get_db() as db:
        r = db.execute("SELECT email_lider, nombre FROM identidad WHERE email=?", (email,)).fetchone()
        if r and r["email_lider"]:
            _notif_interna(r["email_lider"], "capacitacion", "🎓 Nueva capacitación para aprobar",
                           f"{r['nombre']} registró '{nombre}' ({horas}h). Pendiente de aprobación.")
    return True, "Capacitación enviada para aprobación."

def get_capacitaciones_ext(email):
    with get_db() as db:
        return dict_rows(db.execute("""SELECT c.*, i.nombre as nombre_colaborador, i.unidad
            FROM capacitaciones_ext c JOIN identidad i ON c.email = i.email
            WHERE c.email=? ORDER BY c.fecha_registro DESC""", (email,)).fetchall())

def get_caps_pendientes_aprobacion(email_lider, rol):
    with get_db() as db:
        if rol == "Admin":
            return dict_rows(db.execute("""SELECT c.*, i.nombre as nombre_colaborador, i.unidad
                FROM capacitaciones_ext c JOIN identidad i ON c.email = i.email
                WHERE c.estado='Pendiente' ORDER BY c.fecha_registro ASC""").fetchall())
        return dict_rows(db.execute("""SELECT c.*, i.nombre as nombre_colaborador, i.unidad
            FROM capacitaciones_ext c JOIN identidad i ON c.email = i.email
            WHERE c.estado='Pendiente' AND i.email_lider=?
            ORDER BY c.fecha_registro ASC""", (email_lider,)).fetchall())

def aprobar_capacitacion(cap_id, email_aprobador, puntos):
    with get_db() as db:
        cap = db.execute("SELECT * FROM capacitaciones_ext WHERE cap_id=?", (cap_id,)).fetchone()
        if not cap: return False
        db.execute("""UPDATE capacitaciones_ext SET estado='Aprobado', email_aprobador=?,
            fecha_aprobacion=?, puntos_otorgados=? WHERE cap_id=?""",
            (email_aprobador, datetime.now().isoformat(), puntos, cap_id))
    otorgar_badge(cap["email"], f"CAPEXT_{cap_id}", f"🎓 {cap['nombre_cap'][:30]}",
                  f"Cap. externa aprobada: {cap['nombre_cap']}", puntos, "Capacitación", "🎓")
    _notif_interna(cap["email"], "capacitacion", "🎓 ¡Capacitación aprobada!",
                   f"'{cap['nombre_cap']}' fue aprobada. +{puntos} puntos.")
    return True

def rechazar_capacitacion(cap_id, email_aprobador, motivo=""):
    with get_db() as db:
        cap = db.execute("SELECT email, nombre_cap FROM capacitaciones_ext WHERE cap_id=?", (cap_id,)).fetchone()
        db.execute("""UPDATE capacitaciones_ext SET estado='Rechazado', email_aprobador=?,
            fecha_aprobacion=?, motivo_rechazo=? WHERE cap_id=?""",
            (email_aprobador, datetime.now().isoformat(), motivo, cap_id))
    if cap:
        _notif_interna(cap["email"], "capacitacion", "ℹ️ Capacitación revisada",
                       f"'{cap['nombre_cap']}' requiere ajustes." + (f" Motivo: {motivo}" if motivo else ""))

def get_caps_stats_equipo(email_lider, rol):
    with get_db() as db:
        if rol == "Admin":
            miembros = dict_rows(db.execute("SELECT email, nombre FROM identidad WHERE estado='Activo'").fetchall())
        else:
            miembros = dict_rows(db.execute("SELECT email, nombre FROM identidad WHERE email_lider=? AND estado='Activo'", (email_lider,)).fetchall())
        stats = []
        for m in miembros:
            row = db.execute("""SELECT COUNT(*) as total,
                SUM(CASE WHEN estado='Aprobado' THEN 1 ELSE 0 END) as aprobadas,
                SUM(CASE WHEN estado='Aprobado' THEN horas ELSE 0 END) as horas_totales,
                SUM(CASE WHEN estado='Aprobado' THEN puntos_otorgados ELSE 0 END) as puntos_totales
                FROM capacitaciones_ext WHERE email=?""", (m["email"],)).fetchone()
            if row and row["total"] > 0:
                stats.append({"email": m["email"], "nombre": m["nombre"],
                    "total": row["total"] or 0, "aprobadas": row["aprobadas"] or 0,
                    "horas_totales": row["horas_totales"] or 0, "puntos_totales": row["puntos_totales"] or 0})
        return stats


# ═══════════════════════════════════════════════════════════════════
# REPORTE UNIDAD — datos consolidados para PDF
# ═══════════════════════════════════════════════════════════════════

def get_reporte_unidad_completo(unidad, email_lider, periodo_id=None):
    clima   = get_reporte_clima(unidad, dias=30)
    cultura = get_reporte_cultura(dias=30)
    focos   = get_reporte_estrategico(unidad)
    hex_data = get_my_hexagono(email_lider, limit=1) if email_lider else []
    data_360 = {"total_evaluadores": 0, "total_evaluados": 0, "total_registros": 0, "top_colaboradores": []}
    if periodo_id:
        try: data_360 = get_stats_360_admin(periodo_id)
        except Exception: pass
    play_data = {"total_cursos": 0, "total_aprobados": 0, "total_intentos": 0, "ranking": []}
    try: play_data = get_play_stats_admin()
    except Exception: pass
    return {"clima": clima, "cultura": cultura, "focos": focos,
            "hexagono": hex_data, "360": data_360, "play": play_data}


# ═══════════════════════════════════════════════════════════════════
# FEED EN VIVO + PREFERENCIAS UI
# ═══════════════════════════════════════════════════════════════════

def get_feed_vivo(limit=20):
    eventos = []
    with get_db() as db:
        faros = dict_rows(db.execute("""
            SELECT f.faro_id as id, f.nombre_emisor, f.nombre_receptor,
                   f.tipo_faro, f.mensaje, f.fecha_envio as fecha, f.celebraciones,
                   i.foto_url as foto_emisor, i.color_favorito as color_emisor
            FROM faros f LEFT JOIN identidad i ON f.email_emisor = i.email
            WHERE f.visible=1 ORDER BY f.fecha_envio DESC LIMIT ?""", (limit,)).fetchall())
        for f in faros: f["tipo_evento"] = "faro"
        eventos.extend(faros)
        logros = dict_rows(db.execute("""
            SELECT l.logro_id as id, l.email, l.nombre_badge, l.descripcion,
                   l.puntos, l.icono, l.fecha, l.categoria,
                   i.nombre as nombre_usuario, i.foto_url, i.color_favorito, i.unidad
            FROM logros l JOIN identidad i ON l.email = i.email
            ORDER BY l.fecha DESC LIMIT ?""", (limit,)).fetchall())
        for l in logros: l["tipo_evento"] = "logro"
        eventos.extend(logros)
        try:
            play = dict_rows(db.execute("""
                SELECT p.intento_id as id, p.email, p.fecha, p.puntos_ganados,
                       c.titulo as curso_titulo, c.badge_icono, c.categoria,
                       i.nombre as nombre_usuario, i.foto_url, i.color_favorito, i.unidad
                FROM itaca_play_intentos p
                JOIN itaca_play_cursos c ON p.curso_id = c.curso_id
                JOIN identidad i ON p.email = i.email
                WHERE p.aprobado=1 ORDER BY p.fecha DESC LIMIT ?""", (limit,)).fetchall())
            for p in play: p["tipo_evento"] = "play"
            eventos.extend(play)
        except Exception: pass
    eventos.sort(key=lambda e: e.get("fecha") or e.get("fecha_envio") or "", reverse=True)
    return eventos[:limit]

def get_feed_stats():
    with get_db() as db:
        faros_hoy = db.execute("SELECT COUNT(*) FROM faros WHERE fecha_envio >= date('now') AND visible=1").fetchone()[0]
        checkins_sem = db.execute("SELECT COUNT(*) FROM checkins WHERE semana=?",
            (f"{datetime.now().year}-S{datetime.now().isocalendar()[1]:02d}",)).fetchone()[0]
        total_activos = db.execute("SELECT COUNT(*) FROM usuarios WHERE estado='Activo'").fetchone()[0]
        try:
            play_hoy = db.execute("SELECT COUNT(*) FROM itaca_play_intentos WHERE aprobado=1 AND fecha >= date('now')").fetchone()[0]
        except Exception: play_hoy = 0
    return {"faros_hoy": faros_hoy, "checkins_semana": checkins_sem,
            "total_activos": total_activos, "play_hoy": play_hoy}

def save_foto_perfil(email: str, foto_bytes: bytes, mime: str = "image/jpeg") -> str:
    import base64
    b64 = base64.b64encode(foto_bytes).decode()
    data_uri = f"data:{mime};base64,{b64}"
    update_identidad(email, foto_url=data_uri)
    return data_uri

def save_preferencias_ui(email: str, color_favorito: str, dark_mode: bool):
    update_identidad(email, color_favorito=color_favorito, dark_mode=int(dark_mode))

def get_preferencias_ui(email: str) -> dict:
    ident = get_identidad(email)
    return {"color_favorito": ident.get("color_favorito") or "#26C6DA",
            "dark_mode": bool(ident.get("dark_mode", 0)),
            "foto_url": ident.get("foto_url") or ""}

def _notif_interna(email_dest, tipo, titulo, mensaje, prioridad="Media"):
    nid = f"N_{int(datetime.now().timestamp()*1000)}_{email_dest[:5]}"
    with get_db() as db:
        db.execute("INSERT INTO notificaciones VALUES (?,?,?,?,?,?,0,?)",
                   (nid, email_dest, tipo, titulo, mensaje,
                    datetime.now().isoformat(), prioridad))


# Inicializar al importar
init_db()
seed_play_cursos()
