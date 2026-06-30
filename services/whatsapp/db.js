// db.js — SQLite database (sql.js, pure JS, no native compilation needed)
//
// Schema — 3FN (Tercera Forma Normal):
//   1FN: todos los valores atómicos, sin grupos repetidos
//   2FN: sin dependencias parciales (PKs de una columna → cumplida automáticamente)
//   3FN: sin dependencias transitivas — datos del docente viven solo en `docentes`;
//        `tutores_cursos` solo almacena claves foráneas, nunca datos derivados

const initSqlJs = require('sql.js');
const fs        = require('fs');
const path      = require('path');

const DB_FILE = path.join(__dirname, 'conservatorio.db');

let _db    = null;
let _ready = null;

// ──────────────────────────────────────────────
// Schema DDL
// ──────────────────────────────────────────────
const SCHEMA = `
  PRAGMA journal_mode = WAL;
  PRAGMA foreign_keys = ON;

  -- Docentes: tabla maestra de todos los docentes del conservatorio
  CREATE TABLE IF NOT EXISTS docentes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre                TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    cargo                 TEXT,
    correo_institucional  TEXT,
    correo_personal       TEXT,
    celular               TEXT,
    fuente                TEXT    NOT NULL DEFAULT 'xlsx',   -- 'xlsx' | 'form' | 'manual'
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now'))
  );

  -- Cursos: catálogo de cursos/paralelos del conservatorio
  CREATE TABLE IF NOT EXISTS cursos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT    NOT NULL UNIQUE,               -- "1o A", "9o Año (1o Bach) A"
    anio      INTEGER NOT NULL CHECK(anio BETWEEN 1 AND 11),
    paralelo  TEXT    NOT NULL CHECK(paralelo IN ('A','B','C','D')),
    nivel     TEXT    NOT NULL CHECK(nivel IN ('Básica Superior','Bachillerato'))
  );

  -- Tutores-cursos: qué docente es tutor de qué curso en qué año lectivo
  -- Relación N:M resuelta en tabla asociativa (3FN: solo claves, sin atributos de docente/curso)
  CREATE TABLE IF NOT EXISTS tutores_cursos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    curso_id      INTEGER NOT NULL REFERENCES cursos(id)   ON DELETE CASCADE,
    docente_id    INTEGER NOT NULL REFERENCES docentes(id) ON DELETE CASCADE,
    anio_lectivo  TEXT    NOT NULL DEFAULT '2025-2026',
    UNIQUE(curso_id, anio_lectivo)
  );

  CREATE INDEX IF NOT EXISTS idx_tc_docente ON tutores_cursos(docente_id);
  CREATE INDEX IF NOT EXISTS idx_tc_curso   ON tutores_cursos(curso_id);

  -- Sesiones de clase: tema y descripción compartidos por todos los alumnos de esa sesión
  CREATE TABLE IF NOT EXISTS clases_sesiones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sheet_id    TEXT    NOT NULL,
    tab         TEXT    NOT NULL,
    col_index   INTEGER NOT NULL,
    col_name    TEXT    NOT NULL,
    tema        TEXT,
    descripcion TEXT,
    fecha       TEXT    DEFAULT (date('now')),
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(sheet_id, tab, col_index)
  );

  -- Recomendaciones por estudiante: personalizada por alumno en cada sesión
  CREATE TABLE IF NOT EXISTS clase_recomendaciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id        INTEGER NOT NULL REFERENCES clases_sesiones(id) ON DELETE CASCADE,
    student_nombre   TEXT    NOT NULL,
    recomendacion    TEXT,
    created_at       TEXT    DEFAULT (datetime('now')),
    updated_at       TEXT    DEFAULT (datetime('now')),
    UNIQUE(sesion_id, student_nombre)
  );

  CREATE INDEX IF NOT EXISTS idx_cr_sesion   ON clase_recomendaciones(sesion_id);
  CREATE INDEX IF NOT EXISTS idx_cr_student  ON clase_recomendaciones(student_nombre);
`;

// ──────────────────────────────────────────────
// Init & persist
// ──────────────────────────────────────────────
async function getDb() {
  if (_ready) return _ready;
  _ready = initSqlJs().then(SQL => {
    const buf = fs.existsSync(DB_FILE) ? fs.readFileSync(DB_FILE) : null;
    _db = buf ? new SQL.Database(buf) : new SQL.Database();
    _db.run(SCHEMA);
    _persist();
    return _db;
  });
  return _ready;
}

function _persist() {
  if (!_db) return;
  fs.writeFileSync(DB_FILE, Buffer.from(_db.export()));
}

// Helper: execute a SELECT and return array of plain objects
function _all(db, sql, params = []) {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) rows.push(stmt.getAsObject());
  stmt.free();
  return rows;
}

// Helper: execute a statement and return { lastInsertRowid, changes }
function _run(db, sql, params = []) {
  db.run(sql, params);
  const meta = _all(db, 'SELECT last_insert_rowid() as id, changes() as ch');
  return { lastInsertRowid: meta[0]?.id, changes: meta[0]?.ch };
}

// ──────────────────────────────────────────────
// Docentes
// ──────────────────────────────────────────────
async function getAllDocentes() {
  const db = await getDb();
  return _all(db, `SELECT * FROM docentes ORDER BY nombre`);
}

async function upsertDocente({ nombre, cargo, correoInstitucional, correoPersonal, celular, fuente = 'manual' }) {
  const db = await getDb();
  const existing = _all(db, `SELECT * FROM docentes WHERE nombre = ? COLLATE NOCASE`, [nombre]);
  if (existing.length) {
    db.run(
      `UPDATE docentes SET
         cargo = COALESCE(?, cargo),
         correo_institucional = COALESCE(?, correo_institucional),
         correo_personal      = COALESCE(?, correo_personal),
         celular              = COALESCE(?, celular),
         updated_at           = datetime('now')
       WHERE id = ?`,
      [cargo || null, correoInstitucional || null, correoPersonal || null, celular || null, existing[0].id]
    );
    _persist();
    return _all(db, `SELECT * FROM docentes WHERE id = ?`, [existing[0].id])[0];
  } else {
    const { lastInsertRowid } = _run(db,
      `INSERT INTO docentes (nombre, cargo, correo_institucional, correo_personal, celular, fuente)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [nombre, cargo || null, correoInstitucional || null, correoPersonal || null, celular || null, fuente]
    );
    _persist();
    return _all(db, `SELECT * FROM docentes WHERE id = ?`, [lastInsertRowid])[0];
  }
}

// ──────────────────────────────────────────────
// Cursos
// ──────────────────────────────────────────────
async function getAllCursos() {
  const db = await getDb();
  return _all(db, `
    SELECT c.*,
           d.id         AS docente_id,
           d.nombre     AS tutor_nombre,
           d.cargo      AS tutor_cargo,
           d.celular    AS tutor_celular,
           d.correo_institucional AS tutor_correo_inst,
           d.correo_personal     AS tutor_correo_pers
    FROM cursos c
    LEFT JOIN tutores_cursos tc ON tc.curso_id = c.id AND tc.anio_lectivo = '2025-2026'
    LEFT JOIN docentes d        ON d.id = tc.docente_id
    ORDER BY c.anio, c.paralelo
  `);
}

async function upsertCurso({ nombre, anio, paralelo, nivel }) {
  const db = await getDb();
  const existing = _all(db, `SELECT id FROM cursos WHERE nombre = ?`, [nombre]);
  if (existing.length) return existing[0];
  const { lastInsertRowid } = _run(db,
    `INSERT INTO cursos (nombre, anio, paralelo, nivel) VALUES (?, ?, ?, ?)`,
    [nombre, anio, paralelo, nivel]
  );
  _persist();
  return _all(db, `SELECT * FROM cursos WHERE id = ?`, [lastInsertRowid])[0];
}

// ──────────────────────────────────────────────
// Tutores-cursos
// ──────────────────────────────────────────────
async function getAllTutoresCursos(anioLectivo = '2025-2026') {
  const db = await getDb();
  return _all(db, `
    SELECT tc.id, tc.anio_lectivo,
           c.id AS curso_id, c.nombre AS curso, c.anio, c.paralelo, c.nivel,
           (c.anio || '_' || c.paralelo) AS curso_key,
           d.id AS docente_id, d.nombre AS tutor, d.cargo,
           d.celular, d.correo_institucional, d.correo_personal
    FROM tutores_cursos tc
    JOIN cursos   c ON c.id = tc.curso_id
    JOIN docentes d ON d.id = tc.docente_id
    WHERE tc.anio_lectivo = ?
    ORDER BY c.anio, c.paralelo
  `, [anioLectivo]);
}

async function linkTutorCurso({ cursoId, docenteId, anioLectivo = '2025-2026' }) {
  const db = await getDb();
  db.run(
    `INSERT INTO tutores_cursos (curso_id, docente_id, anio_lectivo) VALUES (?, ?, ?)
     ON CONFLICT(curso_id, anio_lectivo) DO UPDATE SET docente_id = excluded.docente_id`,
    [cursoId, docenteId, anioLectivo]
  );
  _persist();
}

// Returns the tutor docente for a given curso name and anio_lectivo
async function getTutorByCursoNombre(nombreCurso, anioLectivo = '2025-2026') {
  const db = await getDb();
  const rows = _all(db, `
    SELECT d.*
    FROM docentes d
    JOIN tutores_cursos tc ON tc.docente_id = d.id
    JOIN cursos c          ON c.id = tc.curso_id
    WHERE c.nombre = ? AND tc.anio_lectivo = ?
    LIMIT 1
  `, [nombreCurso, anioLectivo]);
  return rows[0] || null;
}

// ──────────────────────────────────────────────
// Sesiones de clase + Recomendaciones
// ──────────────────────────────────────────────

async function upsertSesionClase({ sheetId, tab, colIndex, colName, tema, descripcion, fecha }) {
  const db = await getDb();
  db.run(`
    INSERT INTO clases_sesiones (sheet_id, tab, col_index, col_name, tema, descripcion, fecha, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ON CONFLICT(sheet_id, tab, col_index) DO UPDATE SET
      col_name    = excluded.col_name,
      tema        = COALESCE(excluded.tema,        tema),
      descripcion = COALESCE(excluded.descripcion, descripcion),
      fecha       = COALESCE(excluded.fecha,       fecha),
      updated_at  = datetime('now')
  `, [sheetId, tab, colIndex, colName, tema || null, descripcion || null, fecha || null]);
  _persist();
  const rows = _all(db, `SELECT * FROM clases_sesiones WHERE sheet_id=? AND tab=? AND col_index=?`, [sheetId, tab, colIndex]);
  return rows[0];
}

async function getSesionClase(sheetId, tab, colIndex) {
  const db = await getDb();
  const rows = _all(db, `SELECT * FROM clases_sesiones WHERE sheet_id=? AND tab=? AND col_index=?`, [sheetId, tab, colIndex]);
  return rows[0] || null;
}

async function getSesionesTab(sheetId, tab) {
  const db = await getDb();
  return _all(db, `
    SELECT s.*, json_group_array(json_object('student', r.student_nombre, 'recomendacion', r.recomendacion)) AS recomendaciones_json
    FROM clases_sesiones s
    LEFT JOIN clase_recomendaciones r ON r.sesion_id = s.id
    WHERE s.sheet_id=? AND s.tab=?
    GROUP BY s.id
    ORDER BY s.col_index
  `, [sheetId, tab]);
}

async function upsertRecomendacion({ sheetId, tab, colIndex, colName, studentNombre, recomendacion }) {
  const db = await getDb();
  // Asegura que la sesión exista
  let sesion = _all(db, `SELECT id FROM clases_sesiones WHERE sheet_id=? AND tab=? AND col_index=?`, [sheetId, tab, colIndex])[0];
  if (!sesion) {
    db.run(`INSERT INTO clases_sesiones (sheet_id, tab, col_index, col_name) VALUES (?,?,?,?)`, [sheetId, tab, colIndex, colName || `Col${colIndex}`]);
    sesion = _all(db, `SELECT id FROM clases_sesiones WHERE sheet_id=? AND tab=? AND col_index=?`, [sheetId, tab, colIndex])[0];
  }
  db.run(`
    INSERT INTO clase_recomendaciones (sesion_id, student_nombre, recomendacion, updated_at)
    VALUES (?, ?, ?, datetime('now'))
    ON CONFLICT(sesion_id, student_nombre) DO UPDATE SET
      recomendacion = excluded.recomendacion,
      updated_at    = datetime('now')
  `, [sesion.id, studentNombre, recomendacion || null]);
  _persist();
}

async function getRecomendacionesEstudiante(sheetId, tab, studentNombre) {
  const db = await getDb();
  return _all(db, `
    SELECT s.col_index, s.col_name, s.tema, s.descripcion, r.recomendacion
    FROM clases_sesiones s
    JOIN clase_recomendaciones r ON r.sesion_id = s.id
    WHERE s.sheet_id=? AND s.tab=? AND r.student_nombre=?
    ORDER BY s.col_index
  `, [sheetId, tab, studentNombre]);
}

async function getAllSesiones() {
  const db = await getDb();
  return _all(db, `
    SELECT s.*, COUNT(r.id) AS num_recomendaciones
    FROM clases_sesiones s
    LEFT JOIN clase_recomendaciones r ON r.sesion_id = s.id
    GROUP BY s.id
    ORDER BY s.fecha DESC, s.created_at DESC
  `);
}

async function getSesionById(id) {
  const db = await getDb();
  const rows = _all(db, `SELECT * FROM clases_sesiones WHERE id = ?`, [id]);
  return rows[0] || null;
}

async function deleteSesionClase(id) {
  const db = await getDb();
  db.run(`DELETE FROM clases_sesiones WHERE id = ?`, [id]);
  _persist();
}

async function updateSesionClase(id, { colName, tema, descripcion, fecha }) {
  const db = await getDb();
  db.run(`
    UPDATE clases_sesiones SET
      col_name    = COALESCE(?, col_name),
      tema        = ?,
      descripcion = ?,
      fecha       = COALESCE(?, fecha),
      updated_at  = datetime('now')
    WHERE id = ?
  `, [colName || null, tema || null, descripcion || null, fecha || null, id]);
  _persist();
  const rows = _all(db, `SELECT * FROM clases_sesiones WHERE id = ?`, [id]);
  return rows[0];
}

async function getClaseDataCompleta(sheetId, tab) {
  const db = await getDb();
  const sesiones = _all(db, `SELECT * FROM clases_sesiones WHERE sheet_id=? AND tab=? ORDER BY col_index`, [sheetId, tab]);
  const recomendaciones = _all(db, `
    SELECT r.student_nombre, r.recomendacion, s.col_index, s.col_name
    FROM clase_recomendaciones r
    JOIN clases_sesiones s ON s.id = r.sesion_id
    WHERE s.sheet_id=? AND s.tab=?
  `, [sheetId, tab]);
  return { sesiones, recomendaciones };
}

module.exports = {
  getDb,
  getAllDocentes,
  upsertDocente,
  getAllCursos,
  upsertCurso,
  getAllTutoresCursos,
  linkTutorCurso,
  upsertSesionClase,
  getAllSesiones,
  getSesionById,
  deleteSesionClase,
  updateSesionClase,
  getSesionClase,
  getSesionesTab,
  upsertRecomendacion,
  getRecomendacionesEstudiante,
  getClaseDataCompleta,
  getTutorByCursoNombre,
};
