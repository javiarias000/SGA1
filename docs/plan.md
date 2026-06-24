Problema
Actualmente la data en base_de_datos_json/ genera materias duplicadas (variantes por mayúsculas/acentos/abreviaturas) y la lógica de inscripción no está alineada con el modelo deseado:
Teoría: inscripción por curso (GradeLevel/paralelo), no por estudiante.
Agrupaciones: inscripción multi-curso (estudiantes de distintos niveles/paralelos).
Instrumento: inscripción individual (estudiante ↔ docente) por instrumento.
Además, las fuentes JSON contienen inconsistencias de nombres (materias y docentes), lo que dificulta una migración confiable.
Estado actual (lo relevante)
Catálogo de materias: subjects.models.Subject tiene name único y tipo_materia (TEORIA, AGRUPACION, INSTRUMENTO, OTRO).
Clases/inscripción (modelo unificado):
classes.models.Clase: instancia académica por materia+ciclo; para instrumento se usa docente_base.
classes.models.Enrollment: relación estudiante (Usuario) ↔ clase, con docente asignado.
classes.models.GradeLevel: nivel/paralelo.
classes.models.Horario: horario por clase.
ETL existente: classes/management/commands/etl_import_json.py importa:
docentes desde base_de_datos_json/personal_docente/DOCENTES.json
estudiantes desde base_de_datos_json/estudiantes_matriculados/*.json
agrupaciones desde base_de_datos_json/asignaciones_grupales/*.json
instrumentos desde base_de_datos_json/Instrumento_Agrupaciones/ASIGNACIONES_*.json
No importa horarios teóricos desde base_de_datos_json/horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json.
Propuesta (diseño + cambios)
1) Normalización canónica (materias/docentes/cursos)
Crear un módulo de normalización reutilizable (por ejemplo utils/etl_normalization.py o classes/etl/normalization.py) con:
norm_key(text): recorta, colapsa espacios, elimina acentos, casefold.
canonical_subject_name(raw): aplica reglas + alias conocidos para retornar un nombre canónico (con tildes/Title Case si corresponde).
canonical_teacher_name(raw): normaliza y resuelve alias contra el listado oficial (desde DOCENTES.json).
map_grade_level(curso_raw, paralelo_raw): extender el mapeo actual para soportar formatos como "Primero", "Segundo", etc. (además de "1o", "9o (1o Bachillerato)", etc.).
Para no hardcodear todo en Python, agregar archivos de mapeo versionados:
base_de_datos_json/etl_mappings/subjects_aliases.json
base_de_datos_json/etl_mappings/teachers_aliases.json
La idea es que el normalizador:
1) busque en aliases, 2) si no hay alias, use normalización “simple”, 3) reporte candidatos ambiguos a un log.
2) Paso “Normalize-first” sobre base_de_datos_json/
Agregar un comando de management dedicado (p.ej. python manage.py normalize_json_datasets):
Lee todos los JSON relevantes:
asignaciones_grupales/ASIGNACIONES_agrupaciones.json + asignaciones_grupales/asignaciones_docentes.json
Instrumento_Agrupaciones/ASIGNACIONES_*.json
horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json
estudiantes_matriculados/*.json
personal_docente/DOCENTES.json
Produce una salida normalizada en una carpeta nueva (sin romper los originales):
base_de_datos_json/normalized/...
Genera auditoría:
base_de_datos_json/etl_logs/unmatched_subjects.txt
base_de_datos_json/etl_logs/unmatched_teachers.txt
base_de_datos_json/etl_logs/ambiguous_matches.json
Esto reduce “magia” dentro del ETL: primero limpiamos/estandarizamos, luego importamos.
3) Importación/ETL idempotente usando la data normalizada
Actualizar etl_import_json.py para soportar:
--base-dir base_de_datos_json/normalized (o un flag --use-normalized).
Reutilizar el normalizador para garantizar que Subject.name siempre use el nombre canónico.
Regla de clasificación tipo_materia:
Si viene de ASIGNACIONES_*.json → INSTRUMENTO
Si viene de ASIGNACIONES_agrupaciones.json → AGRUPACION
Si viene de REPORTE_DOCENTES_HORARIOS_0858.json → TEORIA (salvo que el nombre canónico exista en el set de agrupaciones; en ese caso queda como AGRUPACION para evitar dobles catálogos).
4) Teoría: clases por curso (GradeLevel) + matrícula masiva
Agregar un importador nuevo (o extender el ETL) para horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json:
Crear/obtener GradeLevel(level, section) usando curso+paralelo.
Para cada combinación (ciclo, materia canónica, grade_level):
Crear/obtener una Clase con:
subject=<TEORIA> (Subject único por nombre canónico)
grade_level=<nivel/paralelo>
paralelo consistente (por ejemplo "A", "B", etc.)
docente_base=None
Crear/actualizar Horario para esa Clase (día/hora/aula) a partir del JSON.
Inscripción por curso: por cada Clase teórica, inscribir a todos los estudiantes cuyo students.Student.grade_level == clase.grade_level (usando Student.usuario como Enrollment.estudiante).
Docentes en teoría:
Es normal que una misma materia (p.ej. Armonía) tenga docentes distintos en cursos distintos; eso se resuelve naturalmente porque la Clase se crea por grade_level.
Si aparece más de un docente para la misma combinación (materia, grade_level), registrar el conflicto en auditoría y crear clases separadas por docente (p.ej. sufijando name o agregando un discriminante interno), para no mezclar matrícula/horarios.
5) Agrupaciones: clase única por agrupación (multi-curso)
Mantener el patrón actual (una Clase por agrupación+ciclo), pero con normalización fuerte para:
Unificar nombres como "Ensamble de Guitarras" vs "Ensamble de guitarras".
Asegurar que la asignación de docente por agrupación (asignaciones_docentes.json) también use nombre canónico.
6) Instrumento: clase por (instrumento, docente) + inscripción individual
Mantener el patrón actual del ETL:
Subject por instrumento (único)
Clase por (subject, ciclo, docente_base)
Enrollment por estudiante (individual), con Enrollment.docente == docente_base
Pero reforzar:
Normalización de nombres de instrumento desde filename + fields.clase.
Validación de que fields.clase coincida con el instrumento esperado del filename (auditar si no).
7) De-duplicación de materias ya creadas en la DB
Agregar un comando seguro (p.ej. python manage.py dedupe_subjects --apply):
Detecta grupos de Subjects que deberían colapsar al mismo canónico (por norm_key).
En modo --dry-run imprime qué se movería.
En modo --apply:
Reasigna FKs (Clase.subject) al Subject canónico
Borra Subjects alias
Escribe un “plan de reversión” (JSON) con IDs y cambios realizados en base_de_datos_json/etl_logs/dedupe_subjects_YYYYMMDD_HHMM.json
8) Pruebas mínimas
Agregar tests Django para:
normalización de materias/docentes (acentos, mayúsculas, abreviaturas)
mapeo de curso/paralelo a GradeLevel
idempotencia básica (correr el import 2 veces no duplica Clase/Enrollment)
Ejecución prevista (cómo se usaría)
1) Normalizar JSON:
docker compose exec web python manage.py normalize_json_datasets --base-dir base_de_datos_json --out-dir base_de_datos_json/normalized
2) Importar (idempotente) desde normalizado:
docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json/normalized --ciclo 2025-2026
3) Importar horarios teóricos + matrícula por curso:
docker compose exec web python manage.py import_horarios_teoria --base-dir base_de_datos_json/normalized --ciclo 2025-2026
4) (Opcional) Deduplicar Subjects preexistentes en DB:
docker compose exec web python manage.py dedupe_subjects --dry-run
docker compose exec web python manage.py dedupe_subjects --apply
Riesgos y decisiones abiertas
Clasificación TEORIA vs AGRUPACION: hay nombres que aparecen en ambos datasets (p.ej. Coro/Orquesta). La regla propuesta prioriza AGRUPACION si el nombre aparece en el set de agrupaciones.
En horarios teóricos puede haber múltiples docentes para la misma materia+curso+paralelo. Se debe decidir si eso implica múltiples Clase o si se prioriza un docente (con auditoría).
Los estudiantes deben tener Student.usuario para poder inscribir vía Enrollment. El ETL ya crea Usuario para estudiantes; pero debe auditar si hay registros sin match.







Mapeo 1:1 con el código actual

1) materias
Tu tabla: materias (id, nombre, tipo)  
En el repo: subjects.Subject
•  name = nombre (ya es unique=True, o sea: no deberían repetirse)
•  tipo_materia = tipo (TEORIA, AGRUPACION, INSTRUMENTO)

Archivo: subjects/models.py



2) usuarios
Tu tabla: usuarios (id, nombre, rol)  
En el repo: users.Usuario
•  nombre
•  rol (DOCENTE / ESTUDIANTE)
•  opcional: auth_user para login (Django User)

Archivo: users/models.py



3) clases
Tu tabla: clases (materia_id, paralelo, ciclo_lectivo)  
En el repo: classes.Clase
•  subject = materia
•  ciclo_lectivo
•  paralelo (string)
•  extra importante: grade_level (FK a GradeLevel) para modelar “curso/paralelo” de forma estructurada
•  extra para instrumento: docente_base (FK a Usuario) para representar “Instrumento es individual y depende del docente”

Archivo: classes/models.py

Nota clave: en tu modelo “paralelo” es parte de la clase. En el repo eso se soporta de 2 formas:
•  grade_level (recomendado para Teoría por curso)
•  paralelo (string), usado en restricciones/compatibilidad



4) inscripciones
Tu tabla: inscripciones (clase_id, estudiante_id, docente_id, estado)  
En el repo: classes.Enrollment
•  clase
•  estudiante (FK a users.Usuario)
•  docente (FK a users.Usuario)
•  estado (ACTIVO/RETIRADO)

Archivo: classes/models.py

Esto soporta perfecto tu regla:
•  Teoría: docente y estudiantes dependen del grade_level/curso
•  Agrupación: estudiantes de distintos cursos a una misma clase
•  Instrumento: inscripción individual, docente = docente_base



5) calificaciones (por inscripción)
Tu tabla: calificaciones (inscripcion_id, descripcion, nota, fecha)  
En el repo: classes.Calificacion
•  inscripcion (Enrollment)
•  descripcion, nota, fecha

Archivo: classes/models.py

Importante: también existe CalificacionParcial (sistema “unificado” de parciales/aportes) que hoy usa fuerte el dashboard docente. Esto convive con tu esquema, pero si tu objetivo final es el que escribiste, en el plan debemos:
•  mantener compatibilidad con CalificacionParcial por ahora
•  pero migrar progresivamente a que “la fuente de verdad” sea Enrollment + Calificacion (o al menos que puedan coexistir sin duplicar materias/clases)



6) asistencia (por inscripción)
Tu tabla: asistencia (inscripcion_id, fecha, estado, observacion)  
En el repo: classes.Asistencia
•  inscripcion, fecha, estado, observacion

Archivo: classes/models.py

También existe Attendance legacy (por Student directo), igual que con notas.

Ajuste importante a tu requerimiento de la pregunta 2 (Armonía / varios docentes)
Lo que describes se logra así (sin duplicar la materia):
•  Materia única: Subject(name="Armonía", tipo_materia="TEORIA")
•  Clases distintas por curso/paralelo: una Clase por (Subject, ciclo_lectivo, grade_level)  
◦  Ej: Armonía + 8vo A, Armonía + 9no B, etc.
•  Docente asignado en la inscripción (Enrollment.docente) de esos estudiantes (del curso correspondiente)

O sea: no agregamos “docentes” a la materia directamente; los docentes viven en la relación operativa:
•  por Clase (teoría por curso) y/o
•  por Enrollment.docente y/o
•  en instrumento por Clase.docente_base

Eso preserva “materia única” y permite múltiples docentes distribuidos por curso.

Sobre el plan
•  Ya actualicé el plan para reflejar tu decisión: misma materia, docentes distintos por curso (resuelto porque la clase es por grade_level).
•  Y te dejé el plan en archivo: PLAN_NORMALIZACION_MIGRACION.md.

Si quieres, el siguiente paso práctico (ya para implementar) es que yo adapte import_horarios.py (que hoy crea clases “viejas” con Teacher) y lo reemplace por el nuevo comando import_horarios_teoria que cree Clase/Horario/Enrollment con Usuario, respetando esta estructura.