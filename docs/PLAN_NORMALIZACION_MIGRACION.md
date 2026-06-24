# Plan: Normalización y migración de materias (Teoría / Agrupaciones / Instrumento)

## Objetivo
- **Materias únicas (sin repetición)** en `subjects.Subject`.
- **Teoría**: inscripción por **curso/paralelo** (GradeLevel) y docente según el horario.
- **Agrupaciones**: inscripción multi-curso (estudiantes de varios GradeLevel).
- **Instrumento**: inscripción individual (estudiante ↔ docente) por instrumento.

## Fuentes de datos
Carpeta `base_de_datos_json/`:
- `personal_docente/DOCENTES.json` (JSONL)
- `estudiantes_matriculados/*.json`
- `asignaciones_grupales/ASIGNACIONES_agrupaciones.json`
- `asignaciones_grupales/asignaciones_docentes.json`
- `Instrumento_Agrupaciones/ASIGNACIONES_*.json`
- `horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json`

## Regla confirmada: Teoría vs Agrupaciones
- Si una materia aparece en datasets de **Agrupaciones**, se clasifica como `AGRUPACION` aunque aparezca también en horarios, para evitar duplicados.

## Modelo destino (DB)
- `subjects.Subject`: catálogo único, con `tipo_materia`.
- `classes.Clase`: instancia por (materia, ciclo) y en teoría por (materia, ciclo, GradeLevel). Para instrumento se diferencia además por `docente_base`.
- `classes.Enrollment`: inscripción estudiante (`users.Usuario`) ↔ `Clase`, con `Enrollment.docente` asignado.
- `classes.Horario`: horario asociado a `Clase`.

## Diseño
### 1) Normalización canónica
Crear un normalizador reutilizable que produzca:
- `norm_key(text)`: trim + colapsar espacios + quitar acentos + casefold.
- `canonical_subject_name(raw)`: nombre canónico + alias.
- `canonical_teacher_name(raw)`: resuelve alias contra el listado oficial de docentes.
- `map_grade_level(curso_raw, paralelo_raw)`: soporta `Primero/Segundo/...` y `1o/2o/...` + bachillerato.

Agregar mapeos versionados:
- `base_de_datos_json/etl_mappings/subjects_aliases.json`
- `base_de_datos_json/etl_mappings/teachers_aliases.json`

### 2) Paso Normalize-first (sin tocar originales)
Crear comando `normalize_json_datasets`:
- Lee los JSON de `base_de_datos_json/`.
- Escribe una copia estandarizada en `base_de_datos_json/normalized/`.
- Genera auditoría:
  - `base_de_datos_json/etl_logs/unmatched_subjects.txt`
  - `base_de_datos_json/etl_logs/unmatched_teachers.txt`
  - `base_de_datos_json/etl_logs/ambiguous_matches.json`

### 3) ETL idempotente desde normalizado
Actualizar `etl_import_json.py` para:
- soportar `--base-dir base_de_datos_json/normalized`
- garantizar `Subject.name` canónico
- reforzar clasificación de `tipo_materia` por fuente

### 4) Teoría: clases por curso + matrícula masiva
Nuevo comando `import_horarios_teoria`:
- A partir de `horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json`:
  - Crear/obtener `GradeLevel(level, section)`.
  - Crear/obtener `Subject` canónico tipo `TEORIA`.
  - Crear/obtener `Clase` por (subject, ciclo, grade_level).
  - Crear/actualizar `Horario`.
  - **Inscribir**: todos los estudiantes con `Student.grade_level == clase.grade_level`.
  - **Docentes**:
    - Es normal que la misma materia tenga docentes distintos en cursos distintos (p.ej. Armonía): queda resuelto porque la `Clase` es por `grade_level`.
    - Si aparece más de un docente para la misma (materia, grade_level), se audita y se crean clases separadas por docente.

### 5) Agrupaciones: clase única por agrupación (multi-curso)
Mantener patrón:
- `Subject` único por agrupación
- `Clase` única por agrupación+ciclo
- `Enrollment` por estudiante, docente desde `asignaciones_docentes.json` (canónico)

### 6) Instrumento: clase por (instrumento, docente) + inscripción individual
Mantener patrón:
- `Subject` único por instrumento
- `Clase` por (instrumento, ciclo, docente_base)
- `Enrollment` por estudiante

### 7) Deduplicación de materias ya creadas
Comando `dedupe_subjects`:
- `--dry-run` lista candidatos
- `--apply` reasigna FKs de `Clase.subject` y borra alias
- log de reversión en `base_de_datos_json/etl_logs/`

## Comandos esperados
1) Normalizar JSON:
- `docker compose exec web python manage.py normalize_json_datasets --base-dir base_de_datos_json --out-dir base_de_datos_json/normalized`
2) Importar base (docentes/estudiantes/agrupaciones/instrumentos):
- `docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json/normalized --ciclo 2025-2026`
3) Importar teoría (horarios + matrícula por curso):
- `docker compose exec web python manage.py import_horarios_teoria --base-dir base_de_datos_json/normalized --ciclo 2025-2026`
4) (Opcional) Deduplicar materias existentes:
- `docker compose exec web python manage.py dedupe_subjects --dry-run`
- `docker compose exec web python manage.py dedupe_subjects --apply`
