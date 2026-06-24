"""
Normalizacion de datos fuente a 4FN (BCNF).
Fuentes:
  - 25-26 Matriculados... .csv           → datos estudiantes + representantes
  - 25-26 Distribucion instrumento...xlsx → asignaciones instrumento/agrupacion
  - Docentes_limpio.csv                   → docentes

Violaciones encontradas:
  1FN: columnas M/F (repeating semantics), 3 grupos de teléfono, PARALELO embebe jornada
  2FN: datos representante dependen del representante, no de la matrícula
  3FN: Edad derivable de FechaNacimiento (eliminada); jornada transitiva desde paralelo
  BCNF: PARALELO = (letra, jornada) → descompuesto en tabla paralelo

Salida: base_de_datos_json/normalizado/*.csv
"""

import pandas as pd
import numpy as np
import re
import glob
import os

BASE = '/home/jav/SGA1/base_de_datos_json'
OUT  = os.path.join(BASE, 'normalizado')
os.makedirs(OUT, exist_ok=True)

CICLO = '2025-2026'

# ─── helpers ────────────────────────────────────────────────────────────────

def clean_str(s):
    if pd.isna(s): return None
    return str(s).strip()

def clean_name(s):
    if pd.isna(s): return None
    return str(s).strip().upper()

INSTRUMENTO_ALIAS = {
    'saxofon':          'Saxofón',
    'saxofón':          'Saxofón',
    'flauta traversa':  'Flauta traversa',
    'flauta transversa':'Flauta traversa',
    'violonchelo':      'Violonchelo',
    'viloncello':       'Violonchelo',
    'violin':           'Violín',
    'violín':           'Violín',
    'clarinete':        'Clarinete',
    'percusion':        'Percusión',
    'percusión':        'Percusión',
    'trombon':          'Trombón',
    'trombón':          'Trombón',
    'trompeta':         'Trompeta',
    'guitarra':         'Guitarra',
    'contrabajo':       'Contrabajo',
    'viola':            'Viola',
    'piano':            'Piano',
    # combos
    'trompeta- pecusión':  'Trompeta-Percusión',
    'trompeta-percusión':  'Trompeta-Percusión',
    'piano-percusión':     'Piano-Percusión',
    'piano- percusión':    'Piano-Percusión',
}

def normalize_instrumento(s):
    if pd.isna(s): return None
    raw = str(s).strip()
    key = raw.lower().strip()
    return INSTRUMENTO_ALIAS.get(key, raw.capitalize())

def parse_paralelo(raw):
    """
    'C (vespertino)' → letra='C', jornada='VESPERTINO'
    'B extrarodinario' → letra='B', jornada='EXTRAORDINARIO'
    'A (matutina)' → letra='A', jornada='MATUTINO'
    """
    if pd.isna(raw): return None, None
    raw = str(raw).strip()
    m = re.match(r'^([A-Za-z])\s*[\(\s]?(matutina|matutino|vespertina|vespertino|extraordinario|extrarodinario|extra)?', raw, re.IGNORECASE)
    if not m: return raw.upper(), None
    letra = m.group(1).upper()
    jornada_raw = m.group(2)
    if not jornada_raw: return letra, None
    j = jornada_raw.lower()
    if 'mat' in j: jornada = 'MATUTINO'
    elif 'vest' in j or 'vesp' in j: jornada = 'VESPERTINO'
    elif 'ext' in j: jornada = 'EXTRAORDINARIO'
    else: jornada = j.upper()
    return letra, jornada

def normalize_anio(raw):
    """'11o (3o Bachillerato)' → '11o';  '9o (1o Bachillerato)' → '9o' """
    if pd.isna(raw): return None
    s = str(raw).strip()
    m = re.match(r'^(\d+o)', s, re.IGNORECASE)
    if not m: return None  # filtra headers como "Año de estudio"
    return m.group(1)

# ─── lookup tables (generadas en vuelo) ─────────────────────────────────────

jornadas = {}     # nombre → id
paralelos = {}    # (letra, jornada_id) → id
cursos = {}       # anio_str → id
instrumentos = {} # nombre_norm → id
agrupaciones = {} # nombre → id
docentes = {}     # nombre_completo_norm → id

def get_jornada(nombre):
    if nombre not in jornadas:
        jornadas[nombre] = len(jornadas) + 1
    return jornadas[nombre]

def get_paralelo(letra, jornada_id):
    key = (letra, jornada_id)
    if key not in paralelos:
        paralelos[key] = len(paralelos) + 1
    return paralelos[key]

def get_curso(anio):
    if anio not in cursos:
        cursos[anio] = len(cursos) + 1
    return cursos[anio]

def get_instrumento(nombre):
    norm = normalize_instrumento(nombre)
    if norm and norm not in instrumentos:
        instrumentos[norm] = len(instrumentos) + 1
    return instrumentos.get(norm), norm

AGRUPACION_ALIAS = {
    'coro matutino':            'Coro Matutino',
    'coro (matutino)':          'Coro Matutino',
    'coro vespertino':          'Coro Vespertino',
    'coro (vespertino)':        'Coro Vespertino',
    'orquesta matutina':        'Orquesta Matutina',
    'ensamble de guitarras':    'Ensamble de Guitarras',
    'ensamble de flautas traversas': 'Ensamble de Flautas Traversas',
    'ensamble de flautas transversas': 'Ensamble de Flautas Traversas',
}

def get_agrupacion(nombre):
    n = clean_str(nombre)
    if not n: return None
    canon = AGRUPACION_ALIAS.get(n.lower(), n)
    if canon not in agrupaciones:
        agrupaciones[canon] = len(agrupaciones) + 1
    return agrupaciones.get(canon)

def get_docente(nombre):
    n = clean_name(nombre)
    if n and n not in docentes:
        docentes[n] = len(docentes) + 1
    return docentes.get(n), n

# ════════════════════════════════════════════════════════════════════════════
# 1. MATRICULADOS
# ════════════════════════════════════════════════════════════════════════════

mat_file = glob.glob(f'{BASE}/*Matriculados*.csv')[0]
raw = pd.read_csv(mat_file, encoding='utf-8', dtype=str)

estudiantes_rows    = []
representantes_rows = []
est_rep_rows        = []
telefonos_rows      = []
info_escolar_rows   = []
info_medica_rows    = []
matriculas_rows     = []

telefono_id = 1

for _, r in raw.iterrows():
    cedula_est = clean_str(r.get('Número de Cédula del Estudiante'))
    # Skip embedded header rows and blank rows
    if not cedula_est or cedula_est in ('nan', 'Número de Cédula del Estudiante'):
        continue
    # Skip rows where cedula is clearly not numeric (header bleed)
    if not cedula_est.replace(' ', '').isdigit():
        continue

    # ── 1FN fix: M/F → genero ──
    if str(r.get('M', '')).strip() == '1':
        genero = 'M'
    elif str(r.get('F', '')).strip() == '1':
        genero = 'F'
    else:
        genero = None

    # ── TABLA: estudiante ──
    estudiantes_rows.append({
        'cedula':           cedula_est,
        'apellidos':        clean_name(r.get('Apellidos del Estudiante')),
        'nombres':          clean_name(r.get('Nombres del Estudiante ')),
        'genero':           genero,
        'fecha_nacimiento': clean_str(r.get('Fecha de Nacimiento del estudiante')),
        # Edad eliminada — viola 3FN (derivable)
        'correo':           clean_str(r.get('Dirección de correo electrónico')),
    })

    # ── TABLA: representante ──
    cedula_rep = clean_str(r.get('Número de cédula del Representante'))
    # Validar que cedula_rep sea numérica (algunos campos tienen teléfonos o texto)
    if cedula_rep and cedula_rep != 'nan' and cedula_rep.replace(' ', '').isdigit() and len(cedula_rep.strip()) >= 8:
        representantes_rows.append({
            'cedula':   cedula_rep,
            'apellidos': clean_name(r.get('Apellidos del Representante del Estudiante')),
            'nombres':   clean_name(r.get('Nombres del Representante del Estudiante')),
        })

        # ── TABLA: estudiante_representante ──
        est_rep_rows.append({
            'cedula_estudiante':    cedula_est,
            'cedula_representante': cedula_rep,
            'direccion':            clean_str(r.get('Dirección')),
        })

        # ── TABLA: telefono (1FN: des-agrupación de grupos repetitivos) ──
        tel_conv = clean_str(r.get('Número telefónico convencional '))
        if tel_conv:
            telefonos_rows.append({
                'id': telefono_id,
                'cedula_representante': cedula_rep,
                'numero': tel_conv,
                'tipo': 'CONVENCIONAL',
                'pertenece_a': None,
            })
            telefono_id += 1

        for i, (num_col, prop_col) in enumerate([
            ('Número telefónico celular 1', 'Número telefónico celular 1 pertenece a '),
            ('Número Telefónico celular 2', 'Número Telefónico celular 2 a quien pertenece'),
            ('Número Telefónico celular 3', 'Número Telefónico Celular 3 a quien pertenece'),
        ], 1):
            num = clean_str(r.get(num_col))
            prop = clean_str(r.get(prop_col))
            if num and num != 'nan':
                telefonos_rows.append({
                    'id': telefono_id,
                    'cedula_representante': cedula_rep,
                    'numero': num,
                    'tipo': f'CELULAR_{i}',
                    'pertenece_a': prop,
                })
                telefono_id += 1

    # ── TABLA: info_escolar (2FN: depende de estudiante, no de matrícula) ──
    info_escolar_rows.append({
        'cedula_estudiante':   cedula_est,
        'institucion_regular': clean_str(r.get('Institución que estudia su formación regular')),
        'anio_estudio_regular': clean_str(r.get('Año de Estudio en su formación Regular')),
    })

    # ── TABLA: info_medica (2FN: depende de estudiante) ──
    alergias = clean_str(r.get('¿Existe alguna alergia/enfermedad/ condición del estudiante que la institución debe tener en cuenta durante clases?\r\n'))
    necesidad = clean_str(r.get('Indique si su representado tiene alguna Necesidad Educativa  no asociada a una discapacidad '))
    detalle   = clean_str(r.get('Si respondió SI Indique cual es la necesidad educativa'))
    info_medica_rows.append({
        'cedula_estudiante':   cedula_est,
        'alergias_condiciones': alergias,
        'tiene_necesidad_educativa': necesidad,
        'detalle_necesidad': detalle,
    })

    # ── BCNF fix: PARALELO → (letra, jornada) ──
    paralelo_raw = r.get('PARALELO')
    letra, jornada_nombre = parse_paralelo(paralelo_raw)
    jornada_id  = get_jornada(jornada_nombre) if jornada_nombre else None
    paralelo_id = get_paralelo(letra, jornada_id) if letra else None

    anio_raw = clean_str(r.get('CURSO'))
    curso_id = get_curso(anio_raw) if anio_raw else None

    # ── TABLA: matricula ──
    matriculas_rows.append({
        'cedula_estudiante': cedula_est,
        'curso_id':          curso_id,
        'paralelo_id':       paralelo_id,
        'ciclo':             CICLO,
    })

# ════════════════════════════════════════════════════════════════════════════
# 2. DOCENTES (desde Docentes_limpio.csv)
# ════════════════════════════════════════════════════════════════════════════

doc_raw = pd.read_csv(f'{BASE}/Docentes_limpio.csv', encoding='utf-8', dtype=str)
docentes_rows = []
for _, r in doc_raw.iterrows():
    nombre = clean_name(r.get('apellidos_y_nombres'))
    if not nombre: continue
    did, nombre_norm = get_docente(nombre)
    docentes_rows.append({
        'id':                    did,
        'nombre_completo':       nombre_norm,
        'cedula':                clean_str(r.get('cedula')),
        'fecha_nacimiento':      clean_str(r.get('fecha_de_nacimiento')),
        'puesto_cargo':          clean_str(r.get('puesto_cargo')),
        'correo_institucional':  clean_str(r.get('correo_electronico_institucional')),
        'correo_personal':       clean_str(r.get('correo_electronico_personal')),
        'celular':               clean_str(r.get('celular')),
    })

# ════════════════════════════════════════════════════════════════════════════
# 3. DISTRIBUCION (instrumento y agrupaciones)
# ════════════════════════════════════════════════════════════════════════════

xl = pd.ExcelFile(f'{BASE}/25-26 Distribucion instrumento, agrupaciones.xlsx')

asig_instrumento_rows    = []
asig_agrupacion_rows     = []
asig_acompanamiento_rows = []
asig_complementario_rows = []

INSTRUMENTO_SHEETS = ['Vientos', 'Guitarras', 'Frotadas', 'teclados']
AGRUPACION_SHEETS  = ['agrupaciones', 'Conj. inst']

def parse_dist_row(r):
    """Retorna dict con campos base de una fila de distribucion."""
    anio = normalize_anio(r.get('Año de estudio'))
    paralelo_raw = r.get('PARALELO (señalar el mismo paralelo en el que estuvieron el año anterior)')
    letra, jornada_nombre = parse_paralelo(paralelo_raw)
    jornada_id  = get_jornada(jornada_nombre) if jornada_nombre else None
    paralelo_id = get_paralelo(letra, jornada_id) if letra else None
    curso_id    = get_curso(anio) if anio else None
    return {
        'apellidos_estudiante': clean_name(r.get('Apellidos del Estudiante')),
        'nombres_estudiante':   clean_name(r.get('Nombres del Estudiante')),
        'curso_id':             curso_id,
        'paralelo_id':          paralelo_id,
        'ciclo':                CICLO,
    }

asig_instr_id = 1
asig_agrup_id = 1
asig_acom_id  = 1
asig_comp_id  = 1

HEADER_SENTINEL = 'Apellidos del Estudiante'

for sheet in INSTRUMENTO_SHEETS:
    df = xl.parse(sheet, dtype=str)
    # 1FN fix: eliminar filas que son repetición del header (todas las hojas tienen esto)
    df = df[df['No'] != 'No']
    df = df[df['Apellidos del Estudiante'] != HEADER_SENTINEL]
    df = df.dropna(subset=['Apellidos del Estudiante'])

    for _, r in df.iterrows():
        base = parse_dist_row(r)
        if not base['apellidos_estudiante']: continue

        instr_id, _ = get_instrumento(r.get('Instrumento que estudia en el Conservatorio Bolívar'))
        doc_id, _   = get_docente(r.get('Maestro de Instrumento'))

        asig_instrumento_rows.append({
            'id': asig_instr_id,
            **base,
            'instrumento_id': instr_id,
            'docente_id':     doc_id,
        })
        asig_instr_id += 1

for sheet in AGRUPACION_SHEETS:
    df = xl.parse(sheet, dtype=str)
    df = df[df['No'] != 'No']
    df = df[df['Apellidos del Estudiante'] != HEADER_SENTINEL]
    df = df.dropna(subset=['Apellidos del Estudiante'])

    for _, r in df.iterrows():
        base = parse_dist_row(r)
        if not base['apellidos_estudiante']: continue

        instr_id, _ = get_instrumento(r.get('Instrumento que estudia en el Conservatorio Bolívar'))
        agrup_id    = get_agrupacion(r.get('Agrupación'))

        asig_agrupacion_rows.append({
            'id': asig_agrup_id,
            **base,
            'instrumento_id': instr_id,
            'agrupacion_id':  agrup_id,
        })
        asig_agrup_id += 1

# acompañamiento: 3FN fix → dos FK docente separadas (no denormalizadas en misma fila)
df_acom = xl.parse('acompañamiento', dtype=str)
df_acom = df_acom[df_acom['Apellidos del Estudiante'] != HEADER_SENTINEL].dropna(subset=['Apellidos del Estudiante'])
for _, r in df_acom.iterrows():
    base = parse_dist_row(r)
    if not base['apellidos_estudiante']: continue
    doc_instr_id, _  = get_docente(r.get('Maestro de Instrumento'))
    doc_acom_id,  _  = get_docente(r.get('Docente piano acompañamiento'))
    asig_acompanamiento_rows.append({
        'id': asig_acom_id,
        **base,
        'docente_instrumento_id':      doc_instr_id,
        'docente_acompanamiento_id':   doc_acom_id,
    })
    asig_acom_id += 1

# complementario
df_comp = xl.parse('complementario', dtype=str)
df_comp = df_comp[df_comp['Apellidos del Estudiante'] != HEADER_SENTINEL].dropna(subset=['Apellidos del Estudiante'])
for _, r in df_comp.iterrows():
    base = parse_dist_row(r)
    if not base['apellidos_estudiante']: continue
    doc_instr_id, _ = get_docente(r.get('Maestro de Instrumento'))
    doc_comp_id,  _ = get_docente(r.get('Docente piano complementario'))
    asig_complementario_rows.append({
        'id': asig_comp_id,
        **base,
        'docente_instrumento_id':    doc_instr_id,
        'docente_complementario_id': doc_comp_id,
    })
    asig_comp_id += 1

# ════════════════════════════════════════════════════════════════════════════
# 4. LOOKUP TABLES
# ════════════════════════════════════════════════════════════════════════════

jornadas_rows  = [{'id': v, 'nombre': k} for k, v in jornadas.items()]
paralelos_rows = [{'id': v, 'letra': k[0], 'jornada_id': k[1]} for k, v in paralelos.items()]
cursos_rows    = [{'id': v, 'anio': k} for k, v in cursos.items()]
instr_rows     = [{'id': v, 'nombre': k} for k, v in instrumentos.items()]
agrup_rows     = [{'id': v, 'nombre': k} for k, v in agrupaciones.items()]

# docentes que aparecen solo en distribucion (sin cedula)
docentes_extra = []
existing_names = {clean_name(r['nombre_completo']) for r in docentes_rows}
for nombre_norm, did in docentes.items():
    if nombre_norm not in existing_names:
        docentes_extra.append({'id': did, 'nombre_completo': nombre_norm,
                               'cedula': None, 'fecha_nacimiento': None,
                               'puesto_cargo': None, 'correo_institucional': None,
                               'correo_personal': None, 'celular': None})
docentes_rows.extend(docentes_extra)

# ════════════════════════════════════════════════════════════════════════════
# 5. GUARDAR CSV
# ════════════════════════════════════════════════════════════════════════════

def save(name, rows):
    if not rows:
        print(f'  [skip] {name} (empty)')
        return
    df = pd.DataFrame(rows)
    # Dedup donde aplica
    if name in ('estudiante', 'representante', 'docente'):
        pk = 'cedula' if name != 'docente' else 'id'
        df = df.drop_duplicates(subset=[pk])
    path = os.path.join(OUT, f'{name}.csv')
    df.to_csv(path, index=False, encoding='utf-8')
    print(f'  ✓ {name}.csv  ({len(df)} filas)')

print('\n=== Guardando tablas normalizadas ===\n')
save('jornada',              jornadas_rows)
save('paralelo',             paralelos_rows)
save('curso',                cursos_rows)
save('instrumento',          instr_rows)
save('agrupacion',           agrup_rows)
save('docente',              docentes_rows)
save('estudiante',           estudiantes_rows)
save('representante',        representantes_rows)
save('telefono',             telefonos_rows)
save('estudiante_representante', est_rep_rows)
save('info_escolar',         info_escolar_rows)
save('info_medica',          info_medica_rows)
save('matricula',            matriculas_rows)
save('asignacion_instrumento',   asig_instrumento_rows)
save('asignacion_agrupacion',    asig_agrupacion_rows)
save('asignacion_acompanamiento', asig_acompanamiento_rows)
save('asignacion_complementario', asig_complementario_rows)

print('\n=== RESUMEN FORMAS NORMALES ===')
print("""
1FN  → columnas M/F unificadas en 'genero'
       grupos repetitivos de teléfonos → tabla 'telefono' (una fila por número)
       filas-header duplicadas en Frotadas → eliminadas
       PARALELO embebe jornada → separado

2FN  → datos representante extraídos a tabla propia 'representante'
       info_escolar e info_medica separadas (dependen del estudiante, no de la matrícula)
       docentes en tabla propia

3FN  → columna 'Edad' eliminada (derivable de fecha_nacimiento)
       dos docentes en acompañamiento/complementario → FKs separadas, no texto en misma columna

BCNF → PARALELO = (letra, jornada): jornada ya no depende transitivamente de paralelo
       tablas lookup: jornada, paralelo, curso, instrumento, agrupacion
""")
