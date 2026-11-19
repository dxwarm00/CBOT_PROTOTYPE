-- Esquema de EDUINSIGHT (SQLite)

CREATE TABLE IF NOT EXISTS estudiantes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula   TEXT UNIQUE NOT NULL,
    carrera     TEXT,
    semestre    INTEGER
);

CREATE TABLE IF NOT EXISTS consultas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER,
    pregunta      TEXT NOT NULL,
    respuesta     TEXT,
    materia       TEXT,
    tema          TEXT,
    confianza     REAL,
    fuente        TEXT,              -- 'reglas', 'ia' o 'demo'
    fecha         TEXT NOT NULL,     -- ISO: 2026-11-18 14:30:00
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
);

CREATE INDEX IF NOT EXISTS idx_consultas_tema  ON consultas(tema);
CREATE INDEX IF NOT EXISTS idx_consultas_fecha ON consultas(fecha);
