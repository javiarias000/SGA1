require('dotenv').config();
const express = require('express');
const { google } = require('googleapis');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const OpenAI = require('openai');
const XLSX = require('xlsx');
const dbModule = require('./db');

const TZ_GYE = 'America/Guayaquil';
function todayGye() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ_GYE }).format(new Date());
}
function nowGye() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ_GYE,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date()).replace(', ', ' ');
}

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public'), {
  etag:         false,
  lastModified: false,
  setHeaders:   (res) => { res.setHeader('Cache-Control', 'no-store'); },
}));

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// ── Proxy SGA1 Django ─────────────────────────────────────────────────────────
// Reenvía /api/informes/* al backend Django (SGA1).
// Configura SGA1_BASE en el .env si Django corre en otro host/puerto.
const SGA1_BASE = (process.env.SGA1_BASE || 'http://localhost:8000').replace(/\/$/, '');
app.use('/api/informes', async (req, res) => {
  try {
    const qs = Object.keys(req.query).length
      ? '?' + new URLSearchParams(req.query).toString()
      : '';
    const target = `${SGA1_BASE}/api/informes${req.path}${qs}`;
    const cfg = { method: req.method, url: target, headers: { 'Content-Type': 'application/json' } };
    if (['POST', 'PUT', 'PATCH'].includes(req.method) && req.body && Object.keys(req.body).length) {
      cfg.data = req.body;
    }
    const resp = await axios(cfg);
    res.status(resp.status).json(resp.data);
  } catch (e) {
    const data = e.response?.data || { error: e.message };
    res.status(e.response?.status || 502).json(data);
  }
});

// ── Evolution API ─────────────────────────────────────────────────────────────
const EVO_URL = (process.env.EVOLUTION_API_URL || '').replace(/\/$/, '');
const EVO_KEY = process.env.EVOLUTION_API_KEY || '';
const evoH    = { apikey: EVO_KEY, 'Content-Type': 'application/json' };

function normalizePhone(raw) {
  const digits = String(raw || '').replace(/\D/g, '');
  if (!digits) return null;
  if (digits.startsWith('593')) return digits;
  if (digits.startsWith('0'))   return '593' + digits.slice(1);
  if (digits.length === 9)      return '593' + digits; // missing leading 0
  return digits;
}

// ── Docentes loader ───────────────────────────────────────────────────────────
// Filename uses NFD decomposed í (i + combining accent cc81)
const DOCENTES_XLSX = (() => {
  const dir   = path.join(__dirname, 'Datos');
  const found = fs.readdirSync(dir).find(f => f.includes('DOCENTES'));
  return found ? path.join(dir, found) : path.join(dir, 'DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx');
})();
const DOCENTES_OVERRIDES  = path.join(__dirname, 'docentes_overrides.json');

function loadDocenteOverrides() {
  if (!fs.existsSync(DOCENTES_OVERRIDES)) return {};
  try { return JSON.parse(fs.readFileSync(DOCENTES_OVERRIDES, 'utf8')); } catch { return {}; }
}

function saveDocenteOverride(nombre, data) {
  const ov = loadDocenteOverrides();
  ov[nombre] = { ...(ov[nombre] || {}), ...data };
  fs.writeFileSync(DOCENTES_OVERRIDES, JSON.stringify(ov, null, 2));
}

function loadDocentes() {
  if (!fs.existsSync(DOCENTES_XLSX)) return [];
  const wb   = XLSX.readFile(DOCENTES_XLSX);
  const rows = XLSX.utils.sheet_to_json(wb.Sheets['GENERAL'], { header: 1, defval: '' });
  const overrides = loadDocenteOverrides();

  return rows.slice(3)
    .filter(r => r[1] && String(r[1]).trim())
    .map(r => {
      const nombre = String(r[1]).trim();
      const base = {
        nombre,
        cargo:               String(r[4]).trim(),
        celular:             normalizePhone(r[7]),
        correoInstitucional: String(r[5]).trim().replace(/\s/g, ''),
        correoPersonal:      String(r[6]).trim().replace(/\s/g, ''),
      };
      // Merge overrides (override can change celular, correo, etc.)
      const ov = overrides[nombre] || {};
      return {
        ...base,
        ...ov,
        // Always re-normalize phone if override provided raw number
        celular: ov.celular ? normalizePhone(ov.celular) : base.celular,
      };
    })
    .filter(d => d.nombre);
}

// ── Submissions store ─────────────────────────────────────────────────────────
const SUBMISSIONS_FILE = path.join(__dirname, 'submissions.json');

function loadSubmissionsFile() {
  if (!fs.existsSync(SUBMISSIONS_FILE)) return [];
  try { return JSON.parse(fs.readFileSync(SUBMISSIONS_FILE, 'utf8')); } catch { return []; }
}

function saveSubmissionsFile(list) {
  fs.writeFileSync(SUBMISSIONS_FILE, JSON.stringify(list, null, 2));
}

function addSubmissionRecord(record) {
  const list = loadSubmissionsFile();
  list.unshift(record); // newest first
  if (list.length > 500) list.splice(500); // cap
  saveSubmissionsFile(list);
}

// ── OAuth setup ───────────────────────────────────────────────────────────────

const credentials = JSON.parse(fs.readFileSync('credentials.json')).web;
const REDIRECT_URI = 'https://victory-postal-relief-generations.trycloudflare.com/oauth2callback';
const oauth2Client = new google.auth.OAuth2(
  credentials.client_id,
  credentials.client_secret,
  REDIRECT_URI
);

const SCOPES = ['https://www.googleapis.com/auth/spreadsheets'];
const TOKEN_PATH = 'token.json';

if (fs.existsSync(TOKEN_PATH)) {
  oauth2Client.setCredentials(JSON.parse(fs.readFileSync(TOKEN_PATH)));
}

app.get('/auth', (req, res) => {
  const url = oauth2Client.generateAuthUrl({ access_type: 'offline', scope: SCOPES });
  res.redirect(url);
});

app.get('/oauth2callback', async (req, res) => {
  try {
    const { tokens } = await oauth2Client.getToken(req.query.code);
    oauth2Client.setCredentials(tokens);
    fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens));
    res.redirect('/?auth=ok');
  } catch {
    res.redirect('/?auth=error');
  }
});

app.get('/api/auth-status', (req, res) => {
  const authenticated = fs.existsSync(TOKEN_PATH);
  let canWrite = false;
  if (authenticated) {
    try {
      const tok = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
      const scope = tok.scope || '';
      // Has write access if scope includes spreadsheets but NOT readonly-only
      canWrite = scope.includes('spreadsheets') && !scope.includes('spreadsheets.readonly');
    } catch { canWrite = false; }
  }
  res.json({ authenticated, canWrite });
});

// ── Google Form constants ─────────────────────────────────────────────────────

const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLSewGgx9m2qI-xia17kWKHLUijep2rFVdql7d7YNpb8pAGGN6w/formResponse';

// Exact dropdown options from the form
const CURSO_TUTOR_OPTIONS = [
  '1o A  Larreátegui Feijoó Inés María',
  '2o A  Laura Guaman Christian Daniel',
  '3o A Túquerez Nuñez Diego Javier',
  '4o A  Solis Solis Juan Francisco',
  '5o A Solis Solis Juan Francisco',
  '7o A Amancha Hidalgo Félix Marcelo',
  '8o A Quinapanta Tibán Angel Rodrigo',
  '9o Año (1o Bach ) A Arévalo Castañeda Angel Jorge',
  '10o año (2o Bach)  A Chicaiza Yanez Jeferson Alexander',
  '11o Año (3o Bach) A Guananga Aysabucha Santiago Javier',
  '1o B Reyes Garcés Elizabeth del Roció',
  '1o C Paredes Santana Marco Antonio',
  '2o B Amores Valdivieso Jenny',
  '2o C Nuñez  Cunalata Zoila Delia',
  '3o B  Peña Nuñez Andrea Michelle',
  '3o C  Fonseca  Sandoval Walter Guillermo',
  '4o B  Guzñay Paca Inti Rafael',
  '4o C  Chico Analuisa Fabricio Renato',
  '5o B De la Cruz Changalombo Jorge Ramiro',
  '5o C Pérez Mayorga Edwin Israel',
  '6o B Acosta Zagal Karolina de los Angeles',
  '6o C Caiza Caiza Roberto Carlos',
  '7o B Toapanta Arequipa Danny Alexander',
  '7o C Gutama Galán Juan Diego',
  '8o B Peralta Aponte Christian',
  '8o C Zumbana  Quinapanta Santiago Maximiliano',
  '9o año (1o Bach)  B Chicaiza Cuenca Rubén Geovany',
  '10o año (2o Bach) B Chico Espinoza Edwin Patricio',
  '10o Año (2o Bach) C Jiménez Vega Mauricio Marmonte',
  '11o año (3o Bach) B Tocto Villarreal Marco Antonio',
];

// ── Course matching ───────────────────────────────────────────────────────────

// Pre-compute dropdown map: "grade_PARALELO" → full option string
const DROPDOWN_MAP = (() => {
  const map = {};
  for (const opt of CURSO_TUTOR_OPTIONS) {
    const lo = opt.toLowerCase();
    let grade = null;

    // Bach variants in parentheses → map to grade 9/10/11
    const bachM = lo.match(/\((\d+)o bach/);
    if (bachM) {
      const n = parseInt(bachM[1]);
      grade = n === 1 ? 9 : n === 2 ? 10 : n === 3 ? 11 : null;
    } else {
      const gm = lo.match(/^(\d+)/);
      if (gm) grade = parseInt(gm[1]);
    }

    // Paralelo: first standalone A/B/C after the leading grade/year block
    const afterGrade = lo
      .replace(/^\d+o?\s*(a[ñn]o\s*)?\([^)]*\)\s*/i, '')
      .replace(/^\d+o?\s*(a[ñn]o\s*)?/i, '');
    const pm = afterGrade.match(/^([abc])\b/i);
    const paralelo = pm ? pm[1].toUpperCase() : null;

    if (grade && paralelo) map[`${grade}_${paralelo}`] = opt;
  }
  return map;
})();

function parseCursoKey(cursoStr) {
  const lo = cursoStr.toLowerCase().trim();

  // "Xdo/Xer/Xmo/Xvo Bach [paralelo]" → bachillerato
  const bachM = lo.match(/(\d+)[a-z]*\s*bach[^\s]*\s+([abc])/i);
  if (bachM) {
    const n = parseInt(bachM[1]);
    const grade = n === 1 ? 9 : n === 2 ? 10 : n === 3 ? 11 : null;
    return grade ? `${grade}_${bachM[2].toUpperCase()}` : null;
  }

  // Regular: extract leading number + trailing paralelo letter
  const gm = lo.match(/(\d+)/);
  const pm = lo.match(/\b([abc])\s*$/i);
  if (gm && pm) return `${parseInt(gm[1])}_${pm[1].toUpperCase()}`;

  return null;
}

function findDropdownOption(cursoFromSheet) {
  const key = parseCursoKey(cursoFromSheet);
  return key ? (DROPDOWN_MAP[key] || null) : null;
}

// ── Sheets helpers ────────────────────────────────────────────────────────────

function extractSheetId(urlOrId) {
  const clean = (urlOrId || '').replace(/[?#].*$/, '').trim();
  const match = clean.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  return match ? match[1] : clean;
}

async function getTabNames(sheets, id) {
  const res = await sheets.spreadsheets.get({ spreadsheetId: id });
  return res.data.sheets.map(s => s.properties.title);
}

async function readTab(sheets, id, tab) {
  try {
    const res = await sheets.spreadsheets.values.get({
      spreadsheetId: id,
      range: `'${tab}'!A:Z`,
    });
    return res.data.values || [];
  } catch {
    return [];
  }
}

function normName(str) {
  return (str || '').trim().replace(/\s+/g, ' ').toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
}

// Returns: { [studentName]: { promedio, curso } }
async function readStudentSheet(sheets, spreadsheetId) {
  const allTabs = await getTabNames(sheets, spreadsheetId);
  const findTab = kw => allTabs.find(t =>
    t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(kw)
  ) || null;

  const contactTab = findTab('contacto');
  const anualTab   = findTab('anual');
  console.log(`[${spreadsheetId}] contacto="${contactTab}" anual="${anualTab}"`);

  const contactRows = contactTab ? await readTab(sheets, spreadsheetId, contactTab) : [];
  const anualRows   = anualTab   ? await readTab(sheets, spreadsheetId, anualTab)   : [];

  // ── Parse Contacto ────────────────────────────────────────────────────────
  // Columns: id | Apellidos | Nombres | Telefono | ... | Curso
  const cursoMap = {}; // normName → { fullName, curso }
  if (contactRows.length >= 2) {
    const h = contactRows[0].map(c => (c || '').toLowerCase().trim());
    const apeIdx  = h.findIndex(c => c.includes('apellido'));
    const nomIdx  = h.findIndex(c => c === 'nombres' || (c.includes('nombre') && !c.includes('apellido')));
    const cursoIdx = h.findIndex(c => c.includes('curso') || c.includes('grado') || c.includes('paralelo'));

    for (let i = 1; i < contactRows.length; i++) {
      const row = contactRows[i];
      const ape  = (row[apeIdx]  || '').trim();
      const nom  = (row[nomIdx]  || '').trim();
      const curso = cursoIdx >= 0 ? (row[cursoIdx] || '').trim() : '';
      const full = [ape, nom].filter(Boolean).join(' ');
      if (full) cursoMap[normName(full)] = { fullName: full, curso };
    }
  }

  // ── Parse Anual ───────────────────────────────────────────────────────────
  // Rows 0-5: institutional headers. Row 6: column headers. Row 7: sub-header. Row 8+: data.
  // Find the header row dynamically (contains "ESTUDIANTE" or "NOTA FINAL")
  const noteMap = {}; // normName → nota
  let headerRowIdx = -1;
  for (let i = 0; i < Math.min(anualRows.length, 15); i++) {
    const cells = anualRows[i].map(c => (c || '').toUpperCase());
    if (cells.some(c => c.includes('ESTUDIANTE') || c.includes('NOTA FINAL'))) {
      headerRowIdx = i;
      break;
    }
  }

  if (headerRowIdx >= 0) {
    const h = anualRows[headerRowIdx].map(c => (c || '').toLowerCase().trim());
    // Name: look for "estudiante" → that's apellidos; the next column is nombres
    const apeIdx  = h.findIndex(c => c.includes('estudiante'));
    const nomIdx  = apeIdx >= 0 ? apeIdx + 1 : -1;
    const noteIdx = h.findIndex(c => c.includes('nota') && c.includes('final'));

    // Skip header row + sub-header row (if any)
    const dataStart = headerRowIdx + 2;

    for (let i = dataStart; i < anualRows.length; i++) {
      const row = anualRows[i];
      const ape  = (row[apeIdx]  || '').trim();
      const nom  = nomIdx >= 0 ? (row[nomIdx] || '').trim() : '';
      const full = [ape, nom].filter(Boolean).join(' ');
      const noteStr = (row[noteIdx] || '').trim().replace(',', '.');
      const note = parseFloat(noteStr);
      if (full && !isNaN(note)) noteMap[normName(full)] = note;
    }
  }

  console.log(`  contacto: ${Object.keys(cursoMap).length} alumnos | anual: ${Object.keys(noteMap).length} notas`);

  // ── Merge by normalized name ──────────────────────────────────────────────
  const result = {};
  for (const [norm, { fullName, curso }] of Object.entries(cursoMap)) {
    const nota = noteMap[norm];
    if (nota !== undefined) {
      result[fullName] = { promedio: Math.round(nota * 100) / 100, curso };
    }
  }
  return result;
}

// ── Configurable student sheet reader ────────────────────────────────────────
// cfg.cols: { ape, nom (optional), curso, gradeApe, gradeNom (optional), nota }
// All col values are column indices (numbers)

async function readStudentSheetConfigured(sheets, spreadsheetId, cfg) {
  const { contactTab, gradeTab, cols } = cfg;

  const contactRows = contactTab ? await readTab(sheets, spreadsheetId, contactTab) : [];
  const gradeRows   = gradeTab   ? await readTab(sheets, spreadsheetId, gradeTab)   : [];

  // ── Find data start row for grades (skip institutional headers) ────────────
  let gradeHeaderIdx = 0;
  for (let i = 0; i < Math.min(gradeRows.length, 15); i++) {
    if (gradeRows[i].filter(c => c && c.trim()).length > 2) {
      gradeHeaderIdx = i;
      break;
    }
  }

  // ── Parse contact tab → cursoMap ──────────────────────────────────────────
  const cursoMap = {}; // normName → { fullName, curso }
  const contactStart = contactRows.length > 1 ? 1 : 0; // skip header row
  for (let i = contactStart; i < contactRows.length; i++) {
    const row = contactRows[i];
    const ape  = (row[cols.ape]  || '').trim();
    const nom  = cols.nom != null ? (row[cols.nom] || '').trim() : '';
    const curso = (row[cols.curso] || '').trim();
    const full = [ape, nom].filter(Boolean).join(' ');
    if (full) cursoMap[normName(full)] = { fullName: full, curso };
  }

  // ── Parse grade tab → noteMap ─────────────────────────────────────────────
  const noteMap = {}; // normName → nota
  const gradeStart = gradeHeaderIdx + (gradeRows.length > gradeHeaderIdx + 1 ? 2 : 1);

  // Auto-detect nombre column: if gradeNom is not set, check if the next column
  // after gradeApe contains text names (not numbers) in the first data row.
  let effectiveGradeNom = cols.gradeNom ?? null;
  if (effectiveGradeNom == null && gradeRows[gradeStart]) {
    const nextIdx = (cols.gradeApe ?? 0) + 1;
    const sample  = (gradeRows[gradeStart][nextIdx] || '').trim();
    if (sample && /[a-záéíóúüñ]/i.test(sample) && isNaN(parseFloat(sample.replace(',', '.')))) {
      effectiveGradeNom = nextIdx;
    }
  }

  for (let i = gradeStart; i < gradeRows.length; i++) {
    const row = gradeRows[i];
    const ape  = (row[cols.gradeApe]  || '').trim();
    const nom  = effectiveGradeNom != null ? (row[effectiveGradeNom] || '').trim() : '';
    const full = [ape, nom].filter(Boolean).join(' ');
    const noteStr = (row[cols.nota] || '').trim().replace(',', '.');
    const note = parseFloat(noteStr);
    if (full && !isNaN(note)) noteMap[normName(full)] = note;
  }

  console.log(`  grade start=${gradeStart} gradeApe=${cols.gradeApe} effectiveGradeNom=${effectiveGradeNom} nota=${cols.nota} → ${Object.keys(noteMap).length} notas`);

  // ── Merge ─────────────────────────────────────────────────────────────────
  const result = {};
  for (const [norm, { fullName, curso }] of Object.entries(cursoMap)) {
    const nota = noteMap[norm];
    if (nota !== undefined) {
      result[fullName] = { promedio: Math.round(nota * 100) / 100, curso };
    }
  }
  return result;
}

// ── Form text builder ─────────────────────────────────────────────────────────

function buildFormText(contenidos, dificultades, acciones) {
  const lines = [];

  lines.push('1 - Contenidos trabajados en el 2do quimestre:');
  lines.push(contenidos);
  lines.push('');

  lines.push('2 - Apellidos y nombres del estudiante que presente dificultades académicas o faltas:');
  if (dificultades.length === 0) {
    lines.push('Ninguno');
  } else {
    dificultades.forEach(d => lines.push(`- ${d.nombre} (promedio: ${d.promedio}/10)`));
  }
  lines.push('');

  lines.push('3 - Actividades realizadas:');
  lines.push(dificultades.length === 0 ? 'No aplica' : acciones);

  return lines.join('\n');
}

// ── API: get tabs of a sheet ──────────────────────────────────────────────────

app.post('/api/get-tabs', async (req, res) => {
  try {
    const { sheetUrl } = req.body;
    const sheets = google.sheets({ version: 'v4', auth: oauth2Client });
    const tabs = await getTabNames(sheets, extractSheetId(sheetUrl));
    res.json({ success: true, tabs });
  } catch (err) {
    res.json({ success: false, error: err.message });
  }
});

// ── API: get column headers of a specific tab ─────────────────────────────────

app.post('/api/get-columns', async (req, res) => {
  try {
    const { sheetUrl, tab } = req.body;
    const sheets = google.sheets({ version: 'v4', auth: oauth2Client });
    const rows = await readTab(sheets, extractSheetId(sheetUrl), tab);

    // For sheets with institutional headers (like Anual), find the real header row
    // (first row where more than 2 cells are non-empty)
    let headerRow = rows[0] || [];
    for (let i = 0; i < Math.min(rows.length, 15); i++) {
      const nonEmpty = rows[i].filter(c => c && c.trim()).length;
      if (nonEmpty > 2) { headerRow = rows[i]; break; }
    }

    const columns = headerRow.map((label, idx) => ({
      idx,
      label: label ? label.trim() : `Columna ${idx + 1}`,
    })).filter(c => c.label);

    res.json({ success: true, columns });
  } catch (err) {
    res.json({ success: false, error: err.message });
  }
});

// ── API: load and preview ─────────────────────────────────────────────────────
// Body: { subjects: [{ name, sheetUrl, contactTab, gradeTab, cols: { ape, nom, curso, nota } }] }

app.post('/api/load-data', async (req, res) => {
  try {
    const { subjects: subjectConfigs } = req.body;
    const sheets = google.sheets({ version: 'v4', auth: oauth2Client });

    const groups = [];

    for (const cfg of subjectConfigs) {
      const id = extractSheetId(cfg.sheetUrl);
      const data = await readStudentSheetConfigured(sheets, id, cfg);
      const byCurso = {};
      for (const [nombre, d] of Object.entries(data)) {
        const key = d.curso || 'Sin curso';
        if (!byCurso[key]) byCurso[key] = [];
        byCurso[key].push({ nombre, promedio: d.promedio });
      }
      for (const [curso, students] of Object.entries(byCurso)) {
        groups.push({
          materia: cfg.name,
          curso,
          dropdownOption: findDropdownOption(curso),
          students,
          dificultades: students.filter(s => s.promedio < 7),
        });
      }
      console.log(`${cfg.name}: ${Object.keys(data).length} estudiantes`);
    }

    res.json({ success: true, groups });
  } catch (err) {
    console.error(err);
    res.json({ success: false, error: err.message });
  }
});

// ── API: analyze Google Form structure ───────────────────────────────────────

app.post('/api/analyze-form', async (req, res) => {
  try {
    const { formUrl } = req.body;

    // Normalize: allow forms.gle, viewform, formResponse — always fetch viewform
    let viewUrl = formUrl.trim().replace(/[?#].*$/, '');
    if (!viewUrl.includes('viewform') && !viewUrl.includes('formResponse')) {
      // short URL like forms.gle/xxx — fetch as-is, axios will follow redirect
    } else {
      viewUrl = viewUrl.replace('/formResponse', '/viewform');
    }

    const htmlRes = await axios.get(viewUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
      },
      timeout: 20000,
      maxRedirects: 10,
    });

    const html = htmlRes.data;

    // ── Extract raw JSON ──────────────────────────────────────────────────────
    const dataStart = html.indexOf('var FB_PUBLIC_LOAD_DATA_ = ');
    if (dataStart === -1) {
      console.error('[analyze-form] FB_PUBLIC_LOAD_DATA_ not found. HTML snippet:', html.slice(0, 500));
      throw new Error('No se encontró la estructura del formulario. Asegúrate de que el link sea público y accesible.');
    }

    const jsonStart = dataStart + 'var FB_PUBLIC_LOAD_DATA_ = '.length;
    const jsonEnd   = html.indexOf(';</script>', jsonStart);
    if (jsonEnd === -1) throw new Error('No se pudo delimitar el JSON del formulario');

    const rawJson = html.slice(jsonStart, jsonEnd);
    let data;
    try { data = JSON.parse(rawJson); }
    catch (e) { throw new Error('JSON del formulario malformado: ' + e.message); }

    // ── Strategy 1: regex over the raw string (catches most Google Forms) ──────
    // Pattern: [entryId, null, "label", (null|"desc"), typeNum
    const TYPES = { 0: 'short_text', 1: 'paragraph', 2: 'radio', 3: 'dropdown', 4: 'checkbox', 5: 'scale', 7: 'grid', 9: 'date', 10: 'time' };
    const seen = new Set();
    const rawFields = [];

    const re = /\[(\d{7,12}),null,"((?:[^"\\]|\\.)*)"/g;
    let m;
    while ((m = re.exec(rawJson)) !== null) {
      const entryId = parseInt(m[1]);
      const label   = m[2].replace(/\\n/g, ' ').replace(/\\"/g, '"').trim();
      if (seen.has(entryId) || !label) continue;
      seen.add(entryId);
      rawFields.push({ entryId, label, type: 'unknown', choices: [] });
    }

    // ── Strategy 2: recursive JSON scan (fills in type + choices) ─────────────
    function scan(node, depth) {
      if (!Array.isArray(node) || depth > 15) return;
      if (
        node.length >= 5 &&
        typeof node[0] === 'number' && String(Math.abs(node[0])).length >= 7 &&
        typeof node[2] === 'string' && node[2].trim().length > 0 &&
        typeof node[4] === 'number' && node[4] >= 0 && node[4] <= 15
      ) {
        const existing = rawFields.find(f => f.entryId === node[0]);
        const choices = Array.isArray(node[6])
          ? node[6].filter(c => Array.isArray(c) && c[0]).map(c => String(c[0])).slice(0, 8)
          : [];
        if (existing) {
          existing.type    = TYPES[node[4]] || existing.type;
          existing.choices = choices.length ? choices : existing.choices;
          return;
        }
        if (!seen.has(node[0])) {
          seen.add(node[0]);
          rawFields.push({ entryId: node[0], label: node[2].trim(), type: TYPES[node[4]] || 'other', choices });
        }
        return;
      }
      for (const child of node) scan(child, depth + 1);
    }
    scan(data, 0);

    console.log(`[analyze-form] found ${rawFields.length} fields:`, rawFields.map(f => `${f.entryId}="${f.label}"`));

    // ── Strategy 3: if still nothing, let GPT parse the raw JSON ──────────────
    let fieldsToMap = rawFields;
    if (rawFields.length === 0) {
      const parseCompletion = await openai.chat.completions.create({
        model: 'gpt-4.1-mini',
        response_format: { type: 'json_object' },
        messages: [
          {
            role: 'system',
            content: 'Eres experto en parsear FB_PUBLIC_LOAD_DATA_ de Google Forms. Extrae todos los campos (preguntas) con su entryId (número 7-12 dígitos), label y tipo. Responde JSON: {"fields":[{"entryId":number,"label":"...","type":"...","choices":[]}]}',
          },
          {
            role: 'user',
            content: 'Extrae los campos de este JSON de Google Forms:\n' + rawJson.slice(0, 30000),
          },
        ],
      });
      const parsed = JSON.parse(parseCompletion.choices[0].message.content);
      fieldsToMap = parsed.fields || [];
    }

    if (fieldsToMap.length === 0) throw new Error('No se encontraron campos en el formulario. Verifica que el link sea público.');

    // ── Ask GPT to suggest mappings ───────────────────────────────────────────
    const completion = await openai.chat.completions.create({
      model: 'gpt-4.1-mini',
      response_format: { type: 'json_object' },
      messages: [
        {
          role: 'system',
          content: `Eres un experto en formularios escolares de música en Ecuador.
Asigna a cada campo el tipo de dato más apropiado.

Tipos disponibles:
- "auto_curso": Curso y tutor del estudiante (dropdown, auto-detectado de la hoja)
- "auto_materia": Nombre de la materia musical (del nombre configurado en la app)
- "text_docente": Nombre del docente (texto que escribe el usuario, uno para todos)
- "text_contenidos": Contenidos del quimestre (uno por materia, en cada tarjeta)
- "auto_dificultades": Lista de estudiantes con dificultades (generado automáticamente)
- "text_acciones": Acciones correctivas (texto que escribe el usuario, uno para todos)
- "informe_completo": Texto completo: contenidos + dificultades + acciones combinados
- "ignore": Campo que no aplica

Responde SOLO con JSON: {"fields":[{"entryId":number,"label":"...","mapping":"tipo","description":"qué se enviará, max 10 palabras"}]}`,
        },
        {
          role: 'user',
          content: `Campos del formulario:\n${JSON.stringify(fieldsToMap, null, 2)}`,
        },
      ],
    });

    const result = JSON.parse(completion.choices[0].message.content);
    res.json({ success: true, fields: result.fields });
  } catch (err) {
    console.error('[analyze-form]', err.message);
    res.json({ success: false, error: err.message });
  }
});

// ── API: docentes (SQLite via db.js) ─────────────────────────────────────────
app.get('/api/docentes', async (_req, res) => {
  try {
    const rows = await dbModule.getAllDocentes();
    // Map DB column names → camelCase for frontend compat
    const docentes = rows.map(r => ({
      id:                   r.id,
      nombre:               r.nombre,
      cargo:                r.cargo,
      celular:              r.celular,
      correoInstitucional:  r.correo_institucional,
      correoPersonal:       r.correo_personal,
      fuente:               r.fuente,
    }));
    res.json({ docentes });
  } catch (e) {
    console.error('[docentes]', e.message);
    res.json({ docentes: loadDocentes() }); // fallback to xlsx
  }
});

app.post('/api/docentes/upsert', async (req, res) => {
  const { nombre, celular, correoInstitucional, correoPersonal, cargo } = req.body;
  if (!nombre) return res.json({ success: false, error: 'Falta nombre' });
  try {
    const phone = celular ? normalizePhone(celular) : undefined;
    const row = await dbModule.upsertDocente({
      nombre,
      cargo:               cargo               || undefined,
      correoInstitucional: correoInstitucional || undefined,
      correoPersonal:      correoPersonal      || undefined,
      celular:             phone               || undefined,
    });
    res.json({
      success: true,
      docente: {
        id:                  row.id,
        nombre:              row.nombre,
        cargo:               row.cargo,
        celular:             row.celular,
        correoInstitucional: row.correo_institucional,
        correoPersonal:      row.correo_personal,
      },
    });
  } catch (e) {
    console.error('[docentes/upsert]', e.message);
    res.json({ success: false, error: e.message });
  }
});

// Catálogo de cursos con su tutor asignado
app.get('/api/cursos', async (_req, res) => {
  try {
    const rows = await dbModule.getAllCursos();
    res.json({ cursos: rows });
  } catch (e) {
    console.error('[cursos]', e.message);
    res.json({ cursos: [] });
  }
});

// Tabla tutores-cursos completa (join docentes + cursos)
app.get('/api/tutores-cursos', async (req, res) => {
  try {
    const anioLectivo = req.query.anio || '2025-2026';
    const rows = await dbModule.getAllTutoresCursos(anioLectivo);
    res.json({ tutoresCursos: rows, anioLectivo });
  } catch (e) {
    console.error('[tutores-cursos]', e.message);
    res.json({ tutoresCursos: [] });
  }
});

// Tutor de un curso específico (por nombre exacto del curso)
app.get('/api/tutor-por-curso', async (req, res) => {
  const { curso, anio } = req.query;
  if (!curso) return res.json({ tutor: null });
  try {
    const tutor = await dbModule.getTutorByCursoNombre(curso, anio || '2025-2026');
    res.json({
      tutor: tutor ? {
        id:                  tutor.id,
        nombre:              tutor.nombre,
        cargo:               tutor.cargo,
        celular:             tutor.celular,
        correoInstitucional: tutor.correo_institucional,
        correoPersonal:      tutor.correo_personal,
      } : null,
    });
  } catch (e) {
    res.json({ tutor: null });
  }
});

// ── API: WhatsApp / Evolution API ─────────────────────────────────────────────

// Crear o conectar instancia → devuelve QR en base64
app.post('/api/wa/instance', async (req, res) => {
  const { instanceName } = req.body;
  if (!instanceName) return res.json({ success: false, error: 'Falta instanceName' });
  try {
    // Try to create; if already exists Evolution returns an error — we ignore it
    await axios.post(`${EVO_URL}/instance/create`, {
      instanceName,
      qrcode:      true,
      integration: 'WHATSAPP-BAILEYS',
    }, { headers: evoH }).catch(() => {});

    // Fetch QR / connection info
    const r = await axios.get(`${EVO_URL}/instance/connect/${instanceName}`, { headers: evoH });
    const payload = r.data;
    // Evolution v1 wraps in { qrcode: { base64, pairingCode } }; v2 may differ
    const base64 = payload?.qrcode?.base64 || payload?.base64 || null;
    res.json({ success: true, qr: base64, raw: payload });
  } catch (e) {
    res.json({ success: false, error: e.response?.data?.message || e.message });
  }
});

// Estado de la instancia
app.get('/api/wa/status/:instance', async (req, res) => {
  try {
    const r = await axios.get(`${EVO_URL}/instance/connectionState/${req.params.instance}`, { headers: evoH });
    const state = r.data?.instance?.state || r.data?.state || r.data?.connectionStatus || 'unknown';
    res.json({ success: true, state });
  } catch (e) {
    res.json({ success: false, state: 'close', error: e.message });
  }
});

// Enviar mensaje de texto
app.post('/api/wa/send', async (req, res) => {
  const { instanceName, phone, message } = req.body;
  if (!instanceName || !phone || !message)
    return res.json({ success: false, error: 'Faltan parámetros' });
  try {
    const r = await axios.post(`${EVO_URL}/message/sendText/${instanceName}`,
      { number: phone, text: message },
      { headers: evoH }
    );
    res.json({ success: true, data: r.data });
  } catch (e) {
    res.json({ success: false, error: e.response?.data?.message || e.message });
  }
});

// ── API: submit forms ─────────────────────────────────────────────────────────

app.post('/api/submit-forms', async (req, res) => {
  const { submissions, formUrl, formFields } = req.body;
  const targetUrl = (formUrl || FORM_URL).trim().replace('/viewform', '/formResponse');

  const results = [];

  for (const sub of submissions) {
    try {
      const params = new URLSearchParams();

      if (formFields && formFields.length > 0) {
        // Dynamic mode: use the detected form fields
        for (const field of formFields) {
          let value;
          switch (field.mapping) {
            case 'auto_curso':      value = sub.dropdownOption; break;
            case 'text_docente':    value = sub.docente; break;
            case 'auto_materia':    value = sub.materia; break;
            case 'text_contenidos': value = sub.contenidos || ''; break;
            case 'auto_dificultades':
              value = sub.dificultades && sub.dificultades.length
                ? sub.dificultades.map(d => `- ${d.nombre} (${d.promedio}/10)`).join('\n')
                : 'Ninguno';
              break;
            case 'text_acciones':
              value = sub.dificultades && sub.dificultades.length
                ? (sub.acciones || '')
                : 'No aplica';
              break;
            case 'informe_completo': value = sub.formText; break;
            case 'ignore': continue;
            default: value = ''; break;
          }
          if (value !== undefined && value !== null) {
            params.append(`entry.${field.entryId}`, value);
          }
        }
      } else {
        // Legacy fallback: hardcoded entries
        params.append('entry.1403373118', sub.dropdownOption);
        params.append('entry.697644543',  sub.docente);
        params.append('entry.2132854786', sub.materia);
        params.append('entry.411694821',  sub.formText);
      }

      params.append('fvv', '1');
      params.append('draftResponse', '[]');
      params.append('pageHistory', '0');
      params.append('fbzx', Math.floor(Math.random() * 1e16).toString());

      await axios.post(targetUrl, params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        maxRedirects: 0,
        validateStatus: s => s < 400,
      });

      // Persist successful submission
      addSubmissionRecord({
        id:            `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        sentAt:        new Date().toISOString(),
        formSuccess:   true,
        tabName:       sub.tabName       || '',
        sheetId:       sub.sheetId       || '',
        materia:       sub.materia       || '',
        docente:       sub.docente       || '',
        docenteNombre: sub.docenteNombre || sub.docente || '',
        docentePhone:  sub.docentePhone  || '',
        curso:         sub.dropdownOption,
        dificultades:  sub.dificultades  || [],
        students:      sub.students      || [],
        contenidos:    sub.contenidos    || '',
        acciones:      sub.acciones      || '',
        formText:      sub.formText      || '',
        formUrl:       formUrl           || '',
        formFields:    formFields        || [],
        waSentAt:      null,
        formSentCount: 1,
      });
      results.push({ label: `${sub.materia} – ${sub.dropdownOption}`, success: true });
    } catch (err) {
      results.push({
        label: `${sub.materia} – ${sub.dropdownOption}`,
        success: false,
        error: err.message,
      });
    }

    await new Promise(r => setTimeout(r, 800));
  }

  res.json({ results });
});

// ── API: historial de envíos ───────────────────────────────────────────────────
app.get('/api/submissions', (_req, res) => {
  res.json({ submissions: loadSubmissionsFile() });
});

app.post('/api/submissions/:id/mark-wa-sent', (req, res) => {
  const list = loadSubmissionsFile();
  const rec  = list.find(s => s.id === req.params.id);
  if (!rec) return res.json({ success: false, error: 'No encontrado' });
  rec.waSentAt = new Date().toISOString();
  saveSubmissionsFile(list);
  res.json({ success: true });
});

// Reenviar al formulario usando datos guardados
app.post('/api/submissions/:id/resend-form', async (req, res) => {
  const list = loadSubmissionsFile();
  const rec  = list.find(s => s.id === req.params.id);
  if (!rec) return res.json({ success: false, error: 'No encontrado' });
  if (!rec.formUrl) return res.json({ success: false, error: 'No hay URL de formulario guardada' });

  const targetUrl = rec.formUrl.trim().replace('/viewform', '/formResponse');
  const params = new URLSearchParams();

  if (rec.formFields && rec.formFields.length > 0) {
    for (const field of rec.formFields) {
      let value;
      switch (field.mapping) {
        case 'auto_curso':        value = rec.curso;       break;
        case 'text_docente':      value = rec.docente;     break;
        case 'auto_materia':      value = rec.materia;     break;
        case 'text_contenidos':   value = rec.contenidos;  break;
        case 'auto_dificultades':
          value = rec.dificultades?.length
            ? rec.dificultades.map(d => `- ${d.nombre} (${d.promedio}/10)`).join('\n')
            : 'Ninguno';
          break;
        case 'text_acciones':
          value = rec.dificultades?.length ? (rec.acciones || '') : 'No aplica';
          break;
        case 'informe_completo': value = rec.formText; break;
        case 'ignore': continue;
        default: value = ''; break;
      }
      if (value !== undefined && value !== null) params.append(`entry.${field.entryId}`, value);
    }
  } else {
    params.append('entry.1403373118', rec.curso);
    params.append('entry.697644543',  rec.docente);
    params.append('entry.2132854786', rec.materia);
    params.append('entry.411694821',  rec.formText);
  }
  params.append('fvv', '1');
  params.append('draftResponse', '[]');
  params.append('pageHistory', '0');
  params.append('fbzx', Math.floor(Math.random() * 1e16).toString());

  try {
    await axios.post(targetUrl, params.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      maxRedirects: 0,
      validateStatus: s => s < 400,
    });
    rec.formSentCount = (rec.formSentCount || 1) + 1;
    rec.lastFormSentAt = new Date().toISOString();
    saveSubmissionsFile(list);
    res.json({ success: true });
  } catch (e) {
    res.json({ success: false, error: e.message });
  }
});

// ── API: analyze sheet structure with Claude ──────────────────────────────────

app.post('/api/analyze-sheet', async (req, res) => {
  try {
    const { sheetUrl } = req.body;
    const sheets = google.sheets({ version: 'v4', auth: oauth2Client });
    const id = extractSheetId(sheetUrl);

    const tabs = await getTabNames(sheets, id);

    // Sample first 15 rows of each tab
    const tabSamples = {};
    for (const tab of tabs) {
      const rows = await readTab(sheets, id, tab);
      tabSamples[tab] = rows.slice(0, 15);
    }

    const sheetDescription = tabs.map(tab => {
      const rows = tabSamples[tab];
      const preview = rows.map((row, i) =>
        `  Fila ${i}: [${row.map(c => JSON.stringify(c || '')).join(', ')}]`
      ).join('\n');
      return `=== Hoja: "${tab}" (${rows.length} filas mostradas) ===\n${preview}`;
    }).join('\n\n');

    const prompt = `Analiza la estructura de esta hoja de cálculo de Google Sheets y determina:

1. Cuál hoja contiene los datos de contacto de estudiantes (apellidos, nombres, curso/grado/paralelo)
2. Cuál hoja contiene las calificaciones finales (nota final y apellidos de estudiantes)
3. Los índices de columna (empezando en 0) para cada dato relevante

Datos de la hoja de cálculo:

${sheetDescription}

Responde ÚNICAMENTE con un JSON válido en este formato exacto (sin texto adicional):
{
  "contactTab": "nombre exacto de la hoja de contactos",
  "gradeTab": "nombre exacto de la hoja de calificaciones",
  "cols": {
    "ape": <índice columna apellidos en contactos>,
    "nom": <índice columna nombres en contactos, o null si no hay>,
    "curso": <índice columna curso/paralelo en contactos>,
    "gradeApe": <índice columna apellidos en calificaciones>,
    "gradeNom": <índice columna nombres en calificaciones, o null si no hay>,
    "nota": <índice columna nota final en calificaciones>
  }
}`;

    const completion = await openai.chat.completions.create({
      model: 'gpt-4.1-mini',
      response_format: { type: 'json_object' },
      messages: [
        {
          role: 'system',
          content: 'Eres un asistente que analiza hojas de cálculo de Google Sheets. Responde únicamente con JSON válido.',
        },
        { role: 'user', content: prompt },
      ],
    });

    const result = JSON.parse(completion.choices[0].message.content);
    res.json({ success: true, ...result });
  } catch (err) {
    console.error('[analyze-sheet]', err.message);
    res.json({ success: false, error: err.message });
  }
});

// ── Smart load: match sheet tabs against column_map.json ─────────────────────

app.post('/api/smart-load', async (req, res) => {
  try {
    const { sheetUrl, subjectName, gradeTab: gradeTabOverride } = req.body;
    const map = loadColMap();
    const knownSheets = map.sheets || {};

    const sheetsApi = google.sheets({ version: 'v4', auth: oauth2Client });
    const id = extractSheetId(sheetUrl);
    const tabs = await getTabNames(sheetsApi, id);

    // Match each tab to a known sheet ID (exact then fuzzy)
    const matched = {};
    for (const tab of tabs) {
      const t = tab.trim();
      if (knownSheets[t]) { matched[t] = knownSheets[t]; continue; }
      for (const [sheetId, cfg] of Object.entries(knownSheets)) {
        if (t.toLowerCase().includes(sheetId.toLowerCase())) {
          matched[t] = cfg; break;
        }
      }
    }

    const matchCount = Object.keys(matched).length;
    if (matchCount === 0) {
      return res.json({ success: false, recognized: false, error: 'Formato no reconocido' });
    }

    // Find the contact and grade tabs
    const findTab = (keywords) =>
      Object.entries(matched).find(([tab]) =>
        keywords.some(kw => tab.toLowerCase().includes(kw.toLowerCase()))
      );

    const contactEntry = findTab(['contacto']);

    // If caller specified a tab, use it; otherwise auto-detect best grade tab
    const gradeEntry = gradeTabOverride
      ? Object.entries(matched).find(([tab]) =>
          tab === gradeTabOverride ||
          tab.toLowerCase() === gradeTabOverride.toLowerCase()
        ) || findTab(['anual', '2Q', '1Q'])
      : findTab(['anual', '2Q', '1Q']);

    if (!contactEntry) {
      return res.json({
        success: true,
        recognized: true,
        format:      map.institution || 'Formato conocido',
        matchedTabs: Object.keys(matched),
        gradeTabs:   Object.keys(matched).filter(t => !t.toLowerCase().includes('contacto')),
        contactTab:  null,
        groups:      [],
        warning:     'Se reconoció el formato pero falta la hoja Contacto',
      });
    }

    if (!gradeEntry) {
      return res.json({
        success:     true,
        recognized:  true,
        format:      map.institution || 'Formato conocido',
        matchedTabs: Object.keys(matched),
        gradeTabs:   Object.keys(matched).filter(t => !t.toLowerCase().includes('contacto')),
        contactTab:  contactEntry[0],
        groups:      [],
        warning:     'No se encontró una hoja de calificaciones válida',
      });
    }

    const [contactTab, contactCfg] = contactEntry;
    const [gradeTab,   gradeCfg]   = gradeEntry;

    // Extract column indices by name from the map
    const colIdx = (cfg, ...names) => {
      for (const name of names) {
        const col = cfg.columns.find(c =>
          c.name.toLowerCase().includes(name.toLowerCase())
        );
        if (col) return col.index;
      }
      return null;
    };

    const cols = {
      ape:      colIdx(contactCfg, 'Apellidos'),
      nom:      colIdx(contactCfg, 'Nombres'),
      curso:    colIdx(contactCfg, 'Curso'),
      gradeApe: colIdx(gradeCfg, 'Apellidos'),
      gradeNom: colIdx(gradeCfg, 'Nombres'),
      // 1P/2P/3P/4P use "Promedio parcial"; 1Q/2Q use "Nota final …"; Anual uses "NOTA FINAL"
      nota:     colIdx(gradeCfg, 'NOTA FINAL', 'Nota Final', 'nota final', 'Promedio parcial', 'Promedio'),
    };

    const data = await readStudentSheetConfigured(sheetsApi, id, { contactTab, gradeTab, cols });

    const byCurso = {};
    for (const [nombre, d] of Object.entries(data)) {
      const key = d.curso || 'Sin curso';
      if (!byCurso[key]) byCurso[key] = [];
      byCurso[key].push({ nombre, promedio: d.promedio });
    }

    const groups = Object.entries(byCurso).map(([curso, students]) => ({
      materia:        subjectName || 'Materia',
      curso,
      dropdownOption: findDropdownOption(curso),
      students,
      dificultades:   students.filter(s => s.promedio < 7),
    }));

    console.log(`[smart-load] ${map.institution} | ${matchCount} tabs | ${groups.length} grupos`);

    res.json({
      success:     true,
      recognized:  true,
      format:      map.institution || 'Formato conocido',
      matchedTabs: Object.keys(matched),
      gradeTabs:   Object.keys(matched).filter(t => !t.toLowerCase().includes('contacto')),
      contactTab,
      gradeTab,
      cols,
      groups,
    });
  } catch (err) {
    console.error('[smart-load]', err.message);
    res.json({ success: false, recognized: false, error: err.message });
  }
});

// ── API: full student table for one tab ──────────────────────────────────────

app.post('/api/tab-table', async (req, res) => {
  try {
    const { sheetUrl, tabName } = req.body;
    const map = loadColMap();
    const cfg = map.sheets[tabName];
    if (!cfg) return res.json({ success: false, error: `Tab "${tabName}" no mapeado` });

    const sheetsApi = google.sheets({ version: 'v4', auth: oauth2Client });
    const sheetId   = extractSheetId(sheetUrl);

    // Read grade tab and Contacto tab in parallel
    const [rows, contactoRows] = await Promise.all([
      readTab(sheetsApi, sheetId, tabName),
      readTab(sheetsApi, sheetId, 'Contacto').catch(() => []),
    ]);

    // Build name → curso map from Contacto
    const contactoCfg = map.sheets['Contacto'];
    const cApe   = contactoCfg?.columns.find(c => c.name === 'Apellidos')?.index ?? 1;
    const cNom   = contactoCfg?.columns.find(c => c.name === 'Nombres')?.index   ?? 2;
    const cCurso = contactoCfg?.columns.find(c => c.name === 'Curso')?.index     ?? 7;
    const cStart = contactoCfg?.dataStartRow ?? 1;

    const cursoMap = {}; // normName → curso
    for (let i = cStart; i < contactoRows.length; i++) {
      const r   = contactoRows[i];
      const ape = (r[cApe]   || '').trim();
      const nom = (r[cNom]   || '').trim();
      const cur = (r[cCurso] || '').trim();
      if (ape && cur) cursoMap[normName(`${ape} ${nom}`)] = cur;
    }

    const dataStart = cfg.dataStartRow;
    const skipSet   = new Set(cfg.skipRows || []);

    // Columns: Curso first, then all grade cols except "No"
    const gradeCols = cfg.columns.filter(c => c.name !== 'No');
    const colNames  = ['Curso', ...gradeCols.map(c => c.name)];

    const apeIdx = cfg.columns.find(c => c.name === 'Apellidos')?.index ?? 1;
    const nomIdx = cfg.columns.find(c => c.name === 'Nombres')?.index   ?? 2;

    const data = [];
    for (let i = dataStart; i < rows.length; i++) {
      if (skipSet.has(i)) continue;
      const row = rows[i];
      const ape = (row[apeIdx] || '').trim();
      if (!ape) continue;
      const nom = (row[nomIdx] || '').trim();
      const key = normName(`${ape} ${nom}`);

      const entry = { Curso: cursoMap[key] || '—' };
      for (const col of gradeCols) {
        entry[col.name] = (row[col.index] || '').trim();
      }
      data.push(entry);
    }

    // Sort by Curso then Apellidos
    data.sort((a, b) => {
      const cc = (a.Curso || '').localeCompare(b.Curso || '', 'es');
      if (cc !== 0) return cc;
      return (a.Apellidos || '').localeCompare(b.Apellidos || '', 'es');
    });

    res.json({ success: true, label: cfg.label, columns: colNames, data });
  } catch (err) {
    console.error('[tab-table]', err.message);
    res.json({ success: false, error: err.message });
  }
});

// ── CSV column mapping ────────────────────────────────────────────────────────

const DATOS_DIR = path.join(__dirname, 'Datos');
const COL_MAP_PATH = path.join(DATOS_DIR, 'column_map.json');

function parseCSV(text) {
  const rows = [];
  let row = [], cell = '', inQuote = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (inQuote && text[i + 1] === '"') { cell += '"'; i++; }
      else inQuote = !inQuote;
    } else if (ch === ',' && !inQuote) {
      row.push(cell); cell = '';
    } else if ((ch === '\n' || ch === '\r') && !inQuote) {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else {
      cell += ch;
    }
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

function loadColMap() {
  if (!fs.existsSync(COL_MAP_PATH)) return { sheets: {} };
  return JSON.parse(fs.readFileSync(COL_MAP_PATH, 'utf8'));
}

// GET /api/cal/sheets — lista hojas mapeadas y pendientes
app.get('/api/cal/sheets', (req, res) => {
  const map = loadColMap();
  const files = fs.readdirSync(DATOS_DIR)
    .filter(f => f.endsWith('.csv'))
    .map(f => f.replace('.csv', ''));

  const sheets = files.map(id => {
    const cfg = map.sheets?.[id];
    return { id, label: cfg?.label || id, mapped: !!cfg, columns: cfg?.columns || [] };
  });

  res.json({ institution: map.institution || '', sheets });
});

// GET /api/cal/raw/:sheet — encabezados sin procesar (línea real del CSV)
app.get('/api/cal/raw/:sheet', (req, res) => {
  const file = path.join(DATOS_DIR, `${req.params.sheet}.csv`);
  if (!fs.existsSync(file)) return res.status(404).json({ error: 'No encontrado' });

  const rows = parseCSV(fs.readFileSync(file, 'utf8'));
  const preview = rows.slice(0, 20).map((r, i) => ({ line: i + 1, cells: r }));
  res.json({ preview });
});

// GET /api/cal/data/:sheet — datos según el mapa de columnas
app.get('/api/cal/data/:sheet', (req, res) => {
  const map = loadColMap();
  const cfg = map.sheets?.[req.params.sheet];
  if (!cfg) return res.status(404).json({ error: 'Hoja no mapeada aún' });

  const file = path.join(DATOS_DIR, `${req.params.sheet}.csv`);
  if (!fs.existsSync(file)) return res.status(404).json({ error: 'CSV no encontrado' });

  const rows = parseCSV(fs.readFileSync(file, 'utf8'));
  const skip = new Set(cfg.skipRows || []);
  const data = [];

  for (let i = cfg.dataStartRow; i < rows.length; i++) {
    if (skip.has(i)) continue;
    const row = rows[i];
    if (row.every(c => !c.trim())) continue;
    const record = {};
    for (const col of cfg.columns) {
      record[col.name] = (row[col.index] || '').trim();
    }
    data.push(record);
  }

  res.json({ label: cfg.label, columns: cfg.columns.map(c => c.name), data });
});

// POST /api/cal/map — guarda o actualiza el mapeo de una hoja
app.post('/api/cal/map', (req, res) => {
  const { sheetId, label, headerRow, skipRows, dataStartRow, columns } = req.body;
  if (!sheetId) return res.status(400).json({ error: 'sheetId requerido' });

  const map = loadColMap();
  map.sheets = map.sheets || {};
  map.sheets[sheetId] = { label, headerRow, skipRows, dataStartRow, columns };
  fs.writeFileSync(COL_MAP_PATH, JSON.stringify(map, null, 2));
  res.json({ success: true });
});

// ── Informes a representantes (padres de familia) ────────────────────────────

// Auto-detect structure of an A1-A4 attendance tab
// Returns: { dateCols: [{index, name}], summaryCols: [{index, name}], dataStartRow }
function detectAttendanceStructure(rows) {
  if (!rows.length) return { dateCols: [], summaryCols: [], dataStartRow: 1 };
  const header = rows[0];
  const total  = header.length;

  // A date-like cell: dd/mm, d/m, or short strings < 8 chars that look like dates
  const isDateLike = (v) => {
    const s = String(v || '').trim();
    if (!s) return false;
    if (/^\d{1,2}\/\d{1,2}(\/\d{2,4})?$/.test(s)) return true;
    if (/^\d{1,2}-\d{1,2}(-\d{2,4})?$/.test(s)) return true;
    // Short alphabetic date abbreviations like "Ene 5", "5 Ene", etc.
    if (/^\d{1,2}\s+[a-záéíóú]{3}/i.test(s)) return true;
    if (/^[a-záéíóú]{3}\s+\d{1,2}/i.test(s)) return true;
    return false;
  };

  const isSummaryLike = (v) => {
    const s = String(v || '').trim().toLowerCase();
    return s.includes('falta') || s.includes('injust') || s.includes('justif') ||
           s.includes('total') || s.includes('ausent') || s.includes('asist');
  };

  const dateCols    = [];
  const summaryCols = [];

  for (let i = 3; i < total; i++) {
    const val = header[i];
    if (isSummaryLike(val)) {
      summaryCols.push({ index: i, name: String(val || '').trim() });
    } else if (isDateLike(val)) {
      dateCols.push({ index: i, name: String(val || '').trim() });
    }
  }

  return { dateCols, summaryCols, dataStartRow: 1 };
}

// Extract attendance data from a row given attendance structure
function extractAttendanceData(row, struct) {
  const { dateCols, summaryCols } = struct;
  let asistencias = 0, faltasJ = 0, faltasI = 0;

  for (const col of dateCols) {
    const v = String(row[col.index] || '').trim().toUpperCase();
    if (v === 'A')       asistencias++;
    else if (v === 'F.J' || v === 'FJ') faltasJ++;
    else if (v === 'F.I' || v === 'FI') faltasI++;
  }

  // Also try to read from summary cols (override counted values)
  for (const col of summaryCols) {
    const name = col.name.toLowerCase();
    const val  = parseFloat(String(row[col.index] || '').replace(',', '.'));
    if (isNaN(val)) continue;
    if (name.includes('injust') || name.includes('f.i') || name.includes('fi')) faltasI = val;
    else if (name.includes('justif') || name.includes('f.j') || name.includes('fj')) faltasJ = val;
  }

  const totalClases    = dateCols.length;
  const pctAsistencia  = totalClases > 0 ? Math.round((asistencias / totalClases) * 1000) / 10 : 0;

  let estado;
  if (faltasI >= 3)           estado = 'INASISTENCIAS';
  else if (pctAsistencia < 75) estado = 'BAJO_ASISTENCIA';
  else                         estado = 'REGULAR';

  return { asistencias, faltasJ, faltasI, totalClases, pctAsistencia, estado };
}

// Extract grade fields from a row using column_map indices
function extractGradeData(row, tabName) {
  const n = (i) => { const v = row[i]; return (v != null && v !== '') ? (parseFloat(v) ?? null) : null; };
  const s = (i) => String(row[i] || '').trim();

  if (['1P','2P','3P','4P'].includes(tabName)) {
    const nota = n(19);
    return { nota: nota ?? 0, estado: (nota ?? 0) < 7 ? 'DIFICULTAD' : 'APROBADO' };
  }
  if (['1Q','2Q'].includes(tabName)) {
    const nota = n(17);
    return {
      nota: nota ?? 0,
      p1: n(3), p2: n(8), promParciales: n(13),
      examen: n(15), escala: s(18),
      faltasJ: n(21), faltasI: n(22),
      estado: (nota ?? 0) < 7 ? 'DIFICULTAD' : 'APROBADO',
    };
  }
  if (tabName === 'Anual') {
    const nota = n(9);
    return {
      nota: nota ?? 0, q1: n(3), q2: n(4), escala: s(10),
      faltasJ: n(14), faltasI: n(15),
      estado: (nota ?? 0) < 7 ? 'DIFICULTAD' : 'APROBADO',
    };
  }
  return { nota: 0, estado: 'APROBADO' };
}

function buildParentMessage(student, materia, periodo, tabName, docenteNombre) {
  const fmt = (v) => (v != null && v !== '' ? Number(v).toFixed(2) : '—');

  // ── Attendance tabs (A1-A4) ──────────────────────────────────────────────
  if (['A1','A2','A3','A4'].includes(tabName)) {
    const regLabel = { A1: '1er Parcial', A2: '2do Parcial', A3: '3er Parcial', A4: '4to Parcial' }[tabName];
    let msg = `📚 *Conservatorio Bolívar de Ambato*\n`;
    msg += `_Informe de asistencias — Registro ${tabName}_\n\n`;
    msg += `Estimado/a representante de *${student.nombre}*:\n`;
    msg += `🎓 Curso: ${student.curso || '—'} | 📖 Asignatura: ${materia}\n\n`;
    msg += `📅 *Asistencias [${tabName}]:*\n`;
    msg += `• Clases registradas: ${student.totalClases ?? 0}\n`;
    msg += `• Asistencias: ${student.asistencias ?? 0}\n`;
    msg += `• Faltas justificadas: ${student.faltasJ ?? 0}\n`;
    msg += `• Faltas injustificadas: ${student.faltasI ?? 0}\n`;
    msg += `• Porcentaje: ${(student.pctAsistencia ?? 0).toFixed(1)}%\n`;
    if ((student.faltasI ?? 0) >= 3) {
      msg += '\n⚠️ *Registra inasistencias injustificadas.* Le invitamos a comunicarse con la institución.\n';
    } else if ((student.pctAsistencia ?? 100) < 75) {
      msg += '\n⚠️ *Bajo porcentaje de asistencia.*\n';
    } else {
      msg += '\n✅ Asistencia regular.\n';
    }
    msg += `\n_Atentamente,_\n_${docenteNombre || 'Docente'}_\n_Conservatorio Bolívar de Ambato_`;
    return msg;
  }

  // ── Grade tabs ────────────────────────────────────────────────────────────
  let msg = `📚 *Conservatorio Bolívar de Ambato*\n`;
  msg += `_Informe de calificaciones — ${periodo}_\n\n`;
  msg += `Estimado/a representante de *${student.nombre}*:\n`;
  msg += `🎓 Curso: ${student.curso || '—'}  |  📖 Asignatura: ${materia}\n\n`;
  msg += `📊 *Calificaciones ${periodo}:*\n`;

  if (['1P','2P','3P','4P'].includes(tabName)) {
    msg += `• Promedio: *${fmt(student.nota)}*\n`;
  } else if (['1Q','2Q'].includes(tabName)) {
    if (student.p1    != null) msg += `• 1er Parcial: ${fmt(student.p1)}\n`;
    if (student.p2    != null) msg += `• 2do Parcial: ${fmt(student.p2)}\n`;
    if (student.promParciales != null) msg += `• Prom. Parciales: ${fmt(student.promParciales)}\n`;
    if (student.examen != null) msg += `• Examen Quimestral: ${fmt(student.examen)}\n`;
    msg += `• *Nota Final: ${fmt(student.nota)}*`;
    if (student.escala) msg += ` (${student.escala})`;
    msg += '\n';
    const fJ = student.faltasJ, fI = student.faltasI;
    if (fJ || fI) {
      msg += `\n📅 *Asistencia:*\n`;
      if (fJ) msg += `• Justificadas: ${fJ}\n`;
      if (fI) msg += `• Injustificadas: ${fI}\n`;
    }
  } else if (tabName === 'Anual') {
    if (student.q1 != null) msg += `• 1er Quimestre: ${fmt(student.q1)}\n`;
    if (student.q2 != null) msg += `• 2do Quimestre: ${fmt(student.q2)}\n`;
    msg += `• *Nota Final Anual: ${fmt(student.nota)}*`;
    if (student.escala) msg += ` (${student.escala})`;
    msg += '\n';
    const fJ = student.faltasJ, fI = student.faltasI;
    if (fJ || fI) {
      msg += `\n📅 *Asistencia anual:*\n`;
      if (fJ) msg += `• Justificadas: ${fJ}\n`;
      if (fI) msg += `• Injustificadas: ${fI}\n`;
    }
  }

  msg += student.estado === 'DIFICULTAD'
    ? '\n⚠️ *Su representado/a presenta dificultades académicas.* Le invitamos a comunicarse con la institución.\n'
    : '\n✅ Aprobado/a en esta etapa.\n';

  msg += `\n_Atentamente,_\n_${docenteNombre || 'Docente'}_\n_Conservatorio Bolívar de Ambato_`;
  return msg;
}

// Carga calificaciones + datos de contacto para una pestaña
app.post('/api/parent-grades', async (req, res) => {
  try {
    const { sheetId, tabName } = req.body;
    if (!sheetId || !tabName) return res.json({ success: false, error: 'Falta sheetId o tabName' });

    const isAttendance = ['A1','A2','A3','A4'].includes(tabName);

    const colMap     = loadColMap();
    const contactCfg = colMap.sheets?.['Contacto'] || { dataStartRow: 1 };

    const sheets   = google.sheets({ version: 'v4', auth: oauth2Client });
    const allTabs  = await getTabNames(sheets, sheetId);
    const contactTabName = allTabs.find(t => t.toLowerCase().includes('contacto')) || 'Contacto';

    // Find the actual tab (exact match or contains)
    const actualTab = allTabs.find(t => t === tabName) ||
                      allTabs.find(t => t.toUpperCase().includes(tabName.toUpperCase())) ||
                      tabName;

    const [contactRows, gradeRows] = await Promise.all([
      readTab(sheets, sheetId, contactTabName),
      readTab(sheets, sheetId, actualTab),
    ]);

    // Build contact map: normName → { nombre, telefono, curso }
    const contactMap = {};
    for (let i = contactCfg.dataStartRow ?? 1; i < contactRows.length; i++) {
      const r = contactRows[i];
      const ape  = String(r[1] || '').trim();
      const nom  = String(r[2] || '').trim();
      const full = [ape, nom].filter(Boolean).join(' ');
      if (!full) continue;
      contactMap[normName(full)] = {
        nombre:   full,
        telefono: normalizePhone(r[3]),
        curso:    String(r[7] || '').trim(),
      };
    }

    // ── Attendance tabs (A1-A4) ──────────────────────────────────────────────
    if (isAttendance) {
      const struct   = detectAttendanceStructure(gradeRows);
      const students = [];

      for (let i = struct.dataStartRow; i < gradeRows.length; i++) {
        const r   = gradeRows[i];
        const ape = String(r[1] || '').trim();
        const nom = String(r[2] || '').trim();
        const full = [ape, nom].filter(Boolean).join(' ');
        if (!full || /total|promedio/i.test(full)) continue;

        const contact = contactMap[normName(full)];
        students.push({
          nombre:   full,
          curso:    contact?.curso || '',
          telefono: contact?.telefono || null,
          ...extractAttendanceData(r, struct),
        });
      }

      const labelMap = { A1: 'Asistencias 1er Parcial', A2: 'Asistencias 2do Parcial', A3: 'Asistencias 3er Parcial', A4: 'Asistencias 4to Parcial' };
      return res.json({
        success: true, tabName,
        label:       labelMap[tabName] || tabName,
        students,
        total:       students.length,
        conTelefono: students.filter(s => s.telefono).length,
      });
    }

    // ── Grade tabs (existing logic) ──────────────────────────────────────────
    const tabCfg = colMap.sheets?.[tabName];
    if (!tabCfg) return res.json({ success: false, error: `Pestaña ${tabName} no configurada` });

    const skipSet  = new Set(tabCfg.skipRows || []);
    const students = [];

    for (let i = tabCfg.dataStartRow; i < gradeRows.length; i++) {
      if (skipSet.has(i)) continue;
      const r   = gradeRows[i];
      const ape = String(r[1] || '').trim();
      const nom = String(r[2] || '').trim();
      const full = [ape, nom].filter(Boolean).join(' ');
      if (!full || /total|promedio/i.test(full)) continue;

      const contact = contactMap[normName(full)];
      students.push({
        nombre:   full,
        curso:    contact?.curso || '',
        telefono: contact?.telefono || null,
        ...extractGradeData(r, tabName),
      });
    }

    res.json({
      success: true, tabName,
      label:       tabCfg.label || tabName,
      students,
      total:       students.length,
      conTelefono: students.filter(s => s.telefono).length,
    });
  } catch (e) {
    console.error('[parent-grades]', e.message);
    res.json({ success: false, error: e.message });
  }
});

// Envía mensajes WhatsApp a representantes
app.post('/api/wa/send-parent-report', async (req, res) => {
  try {
    const { instance, materia, periodo, tabName, docenteNombre, students } = req.body;
    if (!instance || !students?.length) return res.json({ success: false, error: 'Faltan parámetros' });

    const results = [];
    for (const s of students) {
      if (!s.telefono) { results.push({ nombre: s.nombre, status: 'sin_telefono' }); continue; }
      const text = buildParentMessage(s, materia, periodo, tabName, docenteNombre);
      try {
        await axios.post(`${EVO_URL}/message/sendText/${instance}`, { number: s.telefono, text }, { headers: evoH });
        results.push({ nombre: s.nombre, status: 'sent', telefono: s.telefono });
      } catch (e) {
        results.push({ nombre: s.nombre, status: 'error', error: e.response?.data?.message || e.message });
      }
      await new Promise(r => setTimeout(r, 400));
    }

    res.json({ success: true, results, sent: results.filter(r => r.status === 'sent').length });
  } catch (e) {
    console.error('[send-parent-report]', e.message);
    res.json({ success: false, error: e.message });
  }
});

// ── Helper: convert 0-based column index to A1 notation letter ───────────────
function colLetter(n) {
  let s = '';
  while (true) {
    s = String.fromCharCode(65 + (n % 26)) + s;
    if (n < 26) break;
    n = Math.floor(n / 26) - 1;
  }
  return s;
}

// ── API: tab-data — load a sheet tab for editing ──────────────────────────────
app.get('/api/tab-data', async (req, res) => {
  try {
    const { sheetId, tab } = req.query;
    if (!sheetId || !tab) return res.json({ success: false, error: 'Falta sheetId o tab' });

    const sheets   = google.sheets({ version: 'v4', auth: oauth2Client });
    const allTabs  = await getTabNames(sheets, sheetId);
    const actualTab = allTabs.find(t => t === tab) ||
                      allTabs.find(t => t.toUpperCase().includes(tab.toUpperCase())) ||
                      tab;

    const rows = await readTab(sheets, sheetId, actualTab);
    if (!rows.length) return res.json({ success: false, error: 'Tab vacío o no encontrado' });

    const colMap = loadColMap();
    const isAttendance = ['A1','A2','A3','A4'].includes(tab);

    // ── Grade tabs ────────────────────────────────────────────────────────────
    if (!isAttendance) {
      const tabCfg = colMap.sheets?.[tab];
      if (!tabCfg) return res.json({ success: false, error: `Tab "${tab}" no configurado` });

      const labelMap = { '1P':'Primer Parcial','2P':'Segundo Parcial','3P':'Tercer Parcial',
                         '4P':'Cuarto Parcial','1Q':'Primer Quimestre','2Q':'Segundo Quimestre',
                         'Anual':'Anual' };

      // Determine editable vs readonly cols
      let editableCols = [], readonlyCols = [];
      if (['1P','2P','3P','4P'].includes(tab)) {
        // Clase N1..N5 are editable (indices 3-7), Promedio parcial is readonly
        editableCols = tabCfg.columns
          .filter(c => c.index >= 3 && c.index <= 7)
          .map(c => ({ index: c.index, name: c.name }));
        readonlyCols = tabCfg.columns
          .filter(c => c.index === 19)
          .map(c => ({ index: c.index, name: c.name }));
      } else if (['1Q','2Q'].includes(tab)) {
        // Faltas cols editable
        editableCols = tabCfg.columns
          .filter(c => [6,7,11,12].includes(c.index))
          .map(c => ({ index: c.index, name: c.name }));
        readonlyCols = tabCfg.columns
          .filter(c => ![0,1,2,6,7,11,12].includes(c.index))
          .map(c => ({ index: c.index, name: c.name }));
      } else {
        // Anual: nothing editable
        editableCols = [];
        readonlyCols = tabCfg.columns
          .filter(c => c.name !== 'No')
          .map(c => ({ index: c.index, name: c.name }));
      }

      const skipSet  = new Set(tabCfg.skipRows || []);
      const apeIdx   = tabCfg.columns.find(c => c.name === 'Apellidos')?.index ?? 1;
      const nomIdx   = tabCfg.columns.find(c => c.name === 'Nombres')?.index   ?? 2;
      const allCols  = [...editableCols, ...readonlyCols];
      const students = [];
      let   currentCurso = null;

      for (let i = tabCfg.dataStartRow; i < rows.length; i++) {
        if (skipSet.has(i)) continue;
        const r      = rows[i];
        const noCell = String(r[0] || '').trim();
        const ape    = String(r[apeIdx] || '').trim();

        // Skip totals / promedios
        if (/total|promedio/i.test(ape) || /total|promedio/i.test(noCell)) continue;

        // Determine if this is a student row: Nº must be a positive integer
        const noNum    = parseInt(noCell);
        const isStudent = noCell !== '' && !isNaN(noNum) && noNum > 0;

        if (!isStudent) {
          // Course / section header row — grab the name from any non-empty cell
          // Format A: r[0]="" , r[apeIdx]="4to de Básica A"
          // Format B: r[0]="4to de Básica A", r[apeIdx]=""
          const candidate = ape || noCell;
          if (candidate && candidate.length > 1) currentCurso = candidate;
          continue;
        }

        if (!ape) continue; // student row with no name → skip

        const nom    = String(r[nomIdx] || '').trim();
        const values = {};
        for (const col of allCols) {
          values[col.index] = (r[col.index] ?? '');
        }
        students.push({
          sheetRow: i + 1,
          nombre: [ape, nom].filter(Boolean).join(' '),
          curso: currentCurso || null,
          values,
        });
      }

      let courses = [...new Set(students.map(s => s.curso).filter(Boolean))];

      // Cruzar siempre con Contacto para obtener fila exacta + curso si falta
      let contactoTabRet = null;
      let contactoCursoColRet = null;
      try {
        const contactoTabName = allTabs.find(t =>
          t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').includes('contacto')
        );
        if (contactoTabName) {
          const cRows = await readTab(sheets, sheetId, contactoTabName);
          if (cRows.length >= 2) {
            const h      = cRows[0].map(c => (c||'').toLowerCase().trim());
            const cApe   = h.findIndex(c => c.includes('apellido'));
            const cNom   = h.findIndex(c => c==='nombres'||(c.includes('nombre')&&!c.includes('apellido')));
            const cCurso = h.findIndex(c => c.includes('curso')||c.includes('grado')||c.includes('paralelo'));
            contactoTabRet     = contactoTabName;
            contactoCursoColRet = cCurso;

            // nombre → { sheetRow, curso }
            const m = {};
            for (let ci = 1; ci < cRows.length; ci++) {
              const cr   = cRows[ci];
              const ape  = (cr[cApe]  || '').trim();
              const nom  = (cr[cNom]  || '').trim();
              const cur  = cCurso >= 0 ? (cr[cCurso] || '').trim() : '';
              const full = [ape, nom].filter(Boolean).join(' ');
              if (full) m[normName(full)] = { sheetRow: ci + 1, curso: cur };
            }
            for (const s of students) {
              const entry = m[normName(s.nombre)];
              if (entry) {
                s.contactoSheetRow = entry.sheetRow;
                if (!s.curso && entry.curso) s.curso = entry.curso;
              }
            }
            if (!courses.length) {
              courses = [...new Set(students.map(s => s.curso).filter(Boolean))];
            }
            console.log(`[tab-data] Contacto: ${courses.length} cursos, ${students.filter(s=>s.contactoSheetRow).length}/${students.length} mapeados`);
          }
        }
      } catch(e) {
        console.log('[tab-data] Contacto lookup failed:', e.message);
      }

      return res.json({
        success: true, tab, label: tabCfg.label || labelMap[tab] || tab,
        type: 'grade', editableCols, readonlyCols,
        nameCols: { ape: apeIdx, nom: nomIdx },
        students, courses,
        contactoTab: contactoTabRet,
        contactoCursoCol: contactoCursoColRet,
      });
    }

    // ── Attendance tabs (A1-A4) ──────────────────────────────────────────────
    const struct = detectAttendanceStructure(rows);
    const { dateCols, summaryCols } = struct;

    const editableCols = [
      ...dateCols.map(c => ({ index: c.index, name: c.name, isDate: true })),
      ...summaryCols.map(c => ({ index: c.index, name: c.name, isDate: false })),
    ];
    const labelMap = { A1:'Asistencias 1er Parcial', A2:'Asistencias 2do Parcial',
                       A3:'Asistencias 3er Parcial', A4:'Asistencias 4to Parcial' };

    const students = [];
    let attCurso = null;
    for (let i = struct.dataStartRow; i < rows.length; i++) {
      const r      = rows[i];
      const noCell = String(r[0] || '').trim();
      const ape    = String(r[1] || '').trim();

      if (/total|promedio/i.test(ape) || /total|promedio/i.test(noCell)) continue;

      const noNum     = parseInt(noCell);
      const isStudent = noCell !== '' && !isNaN(noNum) && noNum > 0;

      if (!isStudent) {
        const candidate = ape || noCell;
        if (candidate && candidate.length > 1) attCurso = candidate;
        continue;
      }
      if (!ape) continue;

      const nom    = String(r[2] || '').trim();
      const values = {};
      for (const col of editableCols) {
        values[col.index] = (r[col.index] ?? '');
      }
      students.push({ sheetRow: i + 1, nombre: [ape, nom].filter(Boolean).join(' '), curso: attCurso || null, values });
    }

    let courses = [...new Set(students.map(s => s.curso).filter(Boolean))];

    if (!courses.length) {
      try {
        const contactoTabName = allTabs.find(t =>
          t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').includes('contacto')
        );
        if (contactoTabName) {
          const cRows = await readTab(sheets, sheetId, contactoTabName);
          if (cRows.length >= 2) {
            const h = cRows[0].map(c => (c||'').toLowerCase().trim());
            const cApe   = h.findIndex(c => c.includes('apellido'));
            const cNom   = h.findIndex(c => c==='nombres'||(c.includes('nombre')&&!c.includes('apellido')));
            const cCurso = h.findIndex(c => c.includes('curso')||c.includes('grado')||c.includes('paralelo'));
            const m = {};
            for (let ci = 1; ci < cRows.length; ci++) {
              const cr  = cRows[ci];
              const ape = (cr[cApe]  || '').trim();
              const nom = (cr[cNom]  || '').trim();
              const cur = cCurso >= 0 ? (cr[cCurso] || '').trim() : '';
              const full = [ape, nom].filter(Boolean).join(' ');
              if (full && cur) m[normName(full)] = cur;
            }
            for (const s of students) {
              const found = m[normName(s.nombre)];
              if (found) s.curso = found;
            }
            courses = [...new Set(students.map(s => s.curso).filter(Boolean))];
          }
        }
      } catch(e) {
        console.log('[tab-data att] Contacto lookup failed:', e.message);
      }
    }

    return res.json({
      success: true, tab, label: labelMap[tab] || tab,
      type: 'attendance', editableCols, readonlyCols: [],
      nameCols: { ape: 1, nom: 2 },
      students, courses,
    });
  } catch (e) {
    if (e.response?.status === 403 || e.code === 403) {
      return res.json({ success: false, error: 'No tienes permisos de escritura. Re-autoriza en /auth', needsReauth: true });
    }
    console.error('[tab-data]', e.message);
    res.json({ success: false, error: e.message });
  }
});

// ── API: tab-write — write cells back to Google Sheet ────────────────────────
app.post('/api/tab-write', async (req, res) => {
  try {
    const { sheetId, tab, updates } = req.body;
    if (!sheetId || !tab || !updates || !updates.length)
      return res.status(400).json({ success: false, error: 'Faltan parámetros o no hay actualizaciones' });

    const sheets   = google.sheets({ version: 'v4', auth: oauth2Client });
    const allTabs  = await getTabNames(sheets, sheetId);
    const actualTab = allTabs.find(t => t === tab) ||
                      allTabs.find(t => t.toUpperCase().includes(tab.toUpperCase())) ||
                      tab;

    const data = updates.map(({ sheetRow, col, value }) => ({
      range:  `'${actualTab}'!${colLetter(col)}${sheetRow}`,
      values: [[value]],
    }));

    const result = await sheets.spreadsheets.values.batchUpdate({
      spreadsheetId: sheetId,
      requestBody: {
        valueInputOption: 'USER_ENTERED',
        data,
      },
    });

    const updatedCells = result.data.totalUpdatedCells || updates.length;
    res.json({ success: true, updatedCells });
  } catch (e) {
    const status = e.response?.status || e.status || parseInt(e.code);
    console.error('[tab-write]', status, e.message);
    if (status === 403) {
      return res.json({ success: false, error: 'No tienes permisos de escritura. Re-autoriza en /auth', needsReauth: true });
    }
    res.json({ success: false, error: e.message || String(e) });
  }
});

// ── API: clase — listar todas / eliminar / actualizar ─────────────────────────

app.get('/api/clase/all', async (_req, res) => {
  try {
    const sesiones = await dbModule.getAllSesiones();
    res.json({ success: true, sesiones });
  } catch(e) { res.json({ success: false, error: e.message }); }
});

app.delete('/api/clase/sesion/:id', async (req, res) => {
  try {
    await dbModule.deleteSesionClase(parseInt(req.params.id));
    res.json({ success: true });
  } catch(e) { res.json({ success: false, error: e.message }); }
});

app.put('/api/clase/sesion/:id', async (req, res) => {
  try {
    const { colName, tema, descripcion } = req.body;
    const fecha = req.body.fecha || todayGye();
    const sesion = await dbModule.updateSesionClase(parseInt(req.params.id), { colName, tema, descripcion, fecha });
    res.json({ success: true, sesion });
  } catch(e) { res.json({ success: false, error: e.message }); }
});

// ── API: clase pedagógica — sesión (tema/descripción compartida) ──────────────

app.post('/api/clase/sesion', async (req, res) => {
  try {
    const { sheetId, tab, colIndex, colName, tema, descripcion } = req.body;
    const fecha = req.body.fecha || todayGye();   // siempre hora Guayaquil
    if (!sheetId || !tab || colIndex == null) return res.status(400).json({ success: false, error: 'Faltan parámetros' });
    const sesion = await dbModule.upsertSesionClase({ sheetId, tab, colIndex, colName, tema, descripcion, fecha });
    res.json({ success: true, sesion });
  } catch (e) {
    console.error('[clase/sesion]', e.message);
    res.json({ success: false, error: e.message });
  }
});

app.get('/api/clase/sesion', async (req, res) => {
  try {
    const { sheetId, tab, colIndex } = req.query;
    if (!sheetId || !tab || colIndex == null) return res.status(400).json({ success: false, error: 'Faltan parámetros' });
    const sesion = await dbModule.getSesionClase(sheetId, tab, parseInt(colIndex));
    res.json({ success: true, sesion: sesion || null });
  } catch (e) {
    res.json({ success: false, error: e.message });
  }
});

app.get('/api/clase/sesiones', async (req, res) => {
  try {
    const { sheetId, tab } = req.query;
    const sesiones = await dbModule.getSesionesTab(sheetId, tab);
    res.json({ success: true, sesiones });
  } catch (e) {
    res.json({ success: false, error: e.message });
  }
});

// ── API: recomendación por estudiante ─────────────────────────────────────────

app.post('/api/clase/recomendacion', async (req, res) => {
  try {
    const { sheetId, tab, colIndex, colName, studentNombre, recomendacion } = req.body;
    if (!sheetId || !tab || colIndex == null || !studentNombre) return res.status(400).json({ success: false, error: 'Faltan parámetros' });
    await dbModule.upsertRecomendacion({ sheetId, tab, colIndex, colName, studentNombre, recomendacion });
    res.json({ success: true });
  } catch (e) {
    console.error('[clase/recomendacion]', e.message);
    res.json({ success: false, error: e.message });
  }
});

app.get('/api/clase/recomendaciones-estudiante', async (req, res) => {
  try {
    const { sheetId, tab, studentNombre } = req.query;
    const data = await dbModule.getRecomendacionesEstudiante(sheetId, tab, studentNombre);
    res.json({ success: true, data });
  } catch (e) {
    res.json({ success: false, error: e.message });
  }
});

app.get('/api/clase/data-completa', async (req, res) => {
  try {
    const { sheetId, tab } = req.query;
    const data = await dbModule.getClaseDataCompleta(sheetId, tab);
    res.json({ success: true, ...data });
  } catch (e) {
    res.json({ success: false, error: e.message });
  }
});

app.listen(3001, () => console.log('Servidor en http://localhost:3001'));
