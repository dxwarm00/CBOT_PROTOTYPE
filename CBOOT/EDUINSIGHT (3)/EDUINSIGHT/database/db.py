"""Conexión con SQLite: crear tablas, guardar consultas y leerlas."""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "eduinsight.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
CSV_DEMO = BASE_DIR / "data" / "preguntas.csv"


_inicializada = False


def conectar():
    # timeout: si otra parte de la app está escribiendo, espera en vez de fallar
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def inicializar_db():
    """Crea las tablas y, si la base está vacía, carga los datos de prueba.
    Solo trabaja la primera vez; después regresa de inmediato."""
    global _inicializada
    if _inicializada and DB_PATH.exists():
        return
    with conectar() as conn:
        conn.execute("PRAGMA journal_mode = WAL")   # permite leer mientras se escribe
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        total = conn.execute("SELECT COUNT(*) FROM consultas").fetchone()[0]
    if total == 0 and CSV_DEMO.exists():
        cargar_datos_demo()
    _inicializada = True


def obtener_o_crear_estudiante(matricula, carrera=None, semestre=None):
    with conectar() as conn:
        fila = conn.execute(
            "SELECT id FROM estudiantes WHERE matricula = ?", (matricula,)
        ).fetchone()
        if fila:
            return fila["id"]
        cur = conn.execute(
            "INSERT INTO estudiantes (matricula, carrera, semestre) VALUES (?, ?, ?)",
            (matricula, carrera, semestre),
        )
        return cur.lastrowid


def guardar_consulta(estudiante_id, pregunta, respuesta, materia, tema,
                     confianza, fuente, fecha=None):
    fecha = fecha or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with conectar() as conn:
        conn.execute(
            """INSERT INTO consultas
               (estudiante_id, pregunta, respuesta, materia, tema, confianza, fuente, fecha)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (estudiante_id, pregunta, respuesta, materia, tema, confianza, fuente, fecha),
        )


def obtener_consultas():
    """Regresa todas las consultas con datos del estudiante como DataFrame."""
    with conectar() as conn:
        df = pd.read_sql_query(
            """SELECT c.*, e.matricula, e.carrera, e.semestre
               FROM consultas c
               LEFT JOIN estudiantes e ON e.id = c.estudiante_id
               ORDER BY c.fecha""",
            conn,
        )
    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def cargar_datos_demo():
    """Carga data/preguntas.csv para que el dashboard tenga algo que mostrar.
    Todo se guarda en una sola transacción (rápido y sin bloquear la base)."""
    df = pd.read_csv(CSV_DEMO)
    with conectar() as conn:
        # bloquea la base mientras se carga, y revisa que otra ventana no la haya llenado ya
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT COUNT(*) FROM consultas").fetchone()[0] > 0:
            return
        ids = {}
        for _, r in df.iterrows():
            mat = str(r["matricula"])
            if mat not in ids:
                conn.execute(
                    "INSERT OR IGNORE INTO estudiantes (matricula, carrera, semestre) VALUES (?, ?, ?)",
                    (mat, r["carrera"], int(r["semestre"])),
                )
                ids[mat] = conn.execute(
                    "SELECT id FROM estudiantes WHERE matricula = ?", (mat,)
                ).fetchone()["id"]
            conn.execute(
                """INSERT INTO consultas
                   (estudiante_id, pregunta, respuesta, materia, tema, confianza, fuente, fecha)
                   VALUES (?, ?, NULL, ?, ?, 1.0, ?, ?)""",
                (ids[mat], r["pregunta"], r["materia"], r["tema"],
                 r.get("fuente", "demo"), r["fecha"]),
            )


def reiniciar_db():
    """Borra todo y vuelve a cargar los datos de prueba."""
    global _inicializada
    with conectar() as conn:
        conn.execute("DELETE FROM consultas")
        conn.execute("DELETE FROM estudiantes")
    _inicializada = False
    inicializar_db()
