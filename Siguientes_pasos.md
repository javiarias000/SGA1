# Resumen de cambios (hasta 2025-12-18)

Este documento resume los cambios aplicados en el proyecto para avanzar hacia un modelo **unificado** basado en `users.Usuario`, mantener compatibilidad con vistas/admin existentes, y dejar lista la base para un proceso de importación/ETL más consistente e idempotente.

---

## 1) Estado actual: qué se arregló / implementó

### 1.1. Se corrigió el arranque de Django (admin / imports rotos)
Había errores que impedían correr `makemigrations`/`migrate` porque el proyecto no levantaba (imports a modelos eliminados o campos inexistentes). Se corrigió:

- `classes/admin.py`
  - Se eliminaron imports a `Grade` y `Attendance` cuando esos modelos ya no estaban presentes (en ese momento).
  - Se ajustaron `search_fields`, `admin_order_field`, `select_related` para usar `student__usuario__nombre` en vez de `student__name`.
- `subjects/admin.py`
  - Fallaba porque `Teacher.subjects` no existía; se restauró la relación para compatibilidad (ver siguiente sección).

---

### 1.2. Se restauró compatibilidad en `teachers.Teacher`
Para mantener funcionando admin/ETL/partes de la UI que dependen de campos “históricos”, se reintrodujo:

- `Teacher.subjects` (ManyToMany a `subjects.Subject`)
- `Teacher.specialization` (CharField)

> Importante: esto NO vuelve a duplicar datos de persona; el “nombre/email/cedula/phone” siguen viviendo en `Usuario`.

---

### 1.3. Se reintrodujeron modelos legacy `Grade` y `Attendance` (compatibilidad)
Aunque existe el sistema nuevo (`Enrollment` + `Calificacion` / `Asistencia` + `CalificacionParcial`), varias vistas y forms seguían importando y usando `Grade` / `Attendance`.

Se reintrodujeron en `classes/models.py`:
- `Grade` (legacy)
- `Attendance` (legacy)

Esto permite:
- Mantener funcionando dashboards/vistas antiguas mientras migramos la UI al sistema nuevo.
- Seguir usando comandos de migración legacy sin romper el arranque.

---

### 1.4. Forms corregidos para el modelo unificado
Se corrigieron formularios que aún esperaban campos eliminados:

- `students/forms.py`:
  - `StudentForm` ya no usa `Student.name` (porque el nombre vive en `Usuario`).
  - Ahora el form expone campos `nombre/email/cedula` y al guardar crea/actualiza el `Usuario` asociado y lo enlaza a `Student.usuario`.

- `classes/forms.py`:
  - `TeacherProfileForm` ya no usa `Teacher.full_name`/`Teacher.phone` (porque no existen como campos).
  - Ahora edita:
    - `Teacher.specialization`, `Teacher.subjects`, `Teacher.photo`
    - y además actualiza `Usuario.nombre/email/phone/cedula` del docente.

- Ajustes adicionales:
  - `CalificacionParcial.Meta.ordering` corregido de `student__name` a `student__usuario__nombre`.

---

### 1.5. Middleware para compatibilidad `request.user.teacher_profile` / `request.user.student_profile`
Parte del proyecto (decorators/middleware/vistas) asume que `request.user` (Django auth user) tiene:
- `teacher_profile`
- `student_profile`

Con el modelo unificado, esa relación está en `request.user.usuario`.

Se agregó:
- `users.middleware.AttachUsuarioProfilesMiddleware`
  - Si `request.user.usuario` existe:
    - “inyecta” `request.user.teacher_profile = request.user.usuario.teacher_profile` (si aplica)
    - “inyecta” `request.user.student_profile = request.user.usuario.student_profile` (si aplica)

Y se activó en:
- `music_registry/settings.py` (MIDDLEWARE)

Esto reduce roturas en flujo de login y en middlewares/decoradores existentes.

---

### 1.6. Migraciones creadas y aplicadas
Se generaron y aplicaron migraciones nuevas (ya están en el repo local):

- `classes/migrations/0005_remove_deber_cursos_and_more.py`
- `students/migrations/0009_alter_student_options_remove_student_name_and_more.py`
- `teachers/migrations/0006_alter_teacher_options_remove_teacher_full_name_and_more.py`

Y se aplicaron con:
- `python manage.py migrate`

---

### 1.7. Comandos legacy de migración de datos ejecutados
Se ejecutaron:
- `python manage.py migrate_legacy_grades`
- `python manage.py migrate_legacy_attendance`

Resultado: **0 migrados / 0 omitidos** (posiblemente porque no existían datos legacy en las tablas, o porque estaban vacías en este entorno).

---

## 2) Importaciones / ETL: qué quedó mejorado

### 2.1. `etl_import_json` actualizado para no romper el modelo unificado
Se corrigieron puntos críticos en `classes/management/commands/etl_import_json.py`:

- Evitar el bug grave de `update_or_create(email=None)` en docentes:
  - Antes podía colapsar múltiples docentes sin email en **un solo Usuario**
  - Ahora el lookup es:
    1) `cedula` si existe
    2) `email` válido si existe
    3) fallback por `nombre` (último recurso)

- Se eliminó el uso de campos ya inexistentes (ej. `Student.name`, `Student.user`) dentro del ETL.
- En `--dry-run` ya no se lanza excepción (que “ensuciaba” el flujo); ahora:
  - muestra resumen
  - hace rollback de la transacción
  - retorna

- Compatibilidad UI:
  - cuando se detecta el docente (`Usuario`) en inscripciones, se intenta asignar `Student.teacher = Teacher(profile)` para que vistas legacy basadas en `Student.teacher` sigan funcionando.

---

### 2.2. Comandos `import_subjects`, `import_teachers`, `import_students` marcados como deprecados
Para evitar duplicidad y caminos distintos (y frágiles), se cambió:

- `subjects/management/commands/import_subjects.py`
- `teachers/management/commands/import_teachers.py`
- `students/management/commands/import_students.py`

Ahora **no hacen import por su cuenta**: simplemente llaman al ETL unificado:

- `etl_import_json`

Esto reduce inconsistencias y facilita que el import sea idempotente.

---

## 3) Qué falta (pasos siguientes recomendados)

> Lo ya hecho dejó el proyecto funcionando (`python manage.py check` pasó), con migraciones aplicadas y bases para un ETL unificado.  
> Lo siguiente es terminar de “alinear” la UI para que use el modelo nuevo (Enrollment/Usuario) y no dependa de campos legacy.

### 3.1. Terminar refactor de vistas (alto impacto)
Aún hay código legacy (especialmente en `teachers/views.py` y `students/views.py`) que usa:
- `Clase.teacher` (ya no existe en el modelo nuevo)
- `Enrollment.student`/`Enrollment.active` (ahora es `Enrollment.estudiante` y `Enrollment.estado`)
- consultas por `Student.name` (ahora es `Student.usuario.nombre`)

Recomendación:
1) Migrar **Student dashboard / enrollment** a:
   - `Enrollment(estudiante=student.usuario, estado='ACTIVO')`
2) Migrar **Teacher dashboard / clases** a:
   - `Clase.docente_base` y/o `Enrollment.docente`
3) Mantener `Student.teacher` solo como compatibilidad temporal (o rellenarlo vía ETL).

### 3.2. Corregir comandos que quedaron “viejos”
Ejemplo: `users/management/commands/create_default_classes.py` todavía usa:
- `teacher.clases_teoricas`
- `Clase(teacher=teacher, ...)`

Eso ya no aplica al nuevo modelo `Clase`. Hay que actualizarlo o deprecarlo.

### 3.3. Ejecutar importación “buena” (una sola vía)
Comando recomendado (dentro de docker):

- Dry run (recomendado primero):
  - `docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026 --dry-run`

- Ejecución real:
  - `docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026`

Opcional (si quieres crear logins para estudiantes con email válido):
- `docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026 --create-student-users`

### 3.4. Dedupe de materias (si hay duplicados)
Si tienes materias repetidas por variaciones de nombres (tildes/mayúsculas):
- Simulación:
  - `docker compose exec web python manage.py dedupe_subjects`
- Aplicar:
  - `docker compose exec web python manage.py dedupe_subjects --apply`

### 3.5. Decidir estrategia final: legacy vs nuevo
Hoy conviven:
- Legacy: `Grade`, `Attendance` (por Student)
- Nuevo: `Enrollment` + `Calificacion`/`Asistencia` + `CalificacionParcial`

Recomendación práctica:
1) Mantener legacy por ahora (para no romper UI).
2) Migrar UI gradualmente al sistema nuevo.
3) Cuando ya no existan dependencias, recién ahí:
   - migrar datos si aplica
   - remover modelos legacy

---

## 4) Checklist rápido para “implementar luego” en otro entorno

1) Levantar servicios:
   - `docker compose up --build`

2) Aplicar migraciones:
   - `docker compose exec web python manage.py migrate`

3) Correr checks:
   - `docker compose exec web python manage.py check`

4) Ejecutar ETL:
   - `docker compose exec web python manage.py etl_import_json --base-dir base_de_datos_json --ciclo 2025-2026`

5) (Opcional) Deduplicar materias:
   - `docker compose exec web python manage.py dedupe_subjects --apply`

6) (Opcional) Migraciones legacy (si en ese entorno sí hay datos):
   - `docker compose exec web python manage.py migrate_legacy_grades`
   - `docker compose exec web python manage.py migrate_legacy_attendance`

---

## 5) Nota importante sobre “la mejor opción”
Tu idea de normalizar hacia `users.Usuario` es correcta, pero el “mejor” camino en este repo requiere:
- **compatibilidad incremental**
- evitar borrar modelos/relaciones que aún usa la UI
- y centralizar importaciones (ETL) para no tener 3-4 scripts con reglas distintas

En este punto, el repositorio está en un estado más estable: ya migra, ya levanta, y el ETL unificado queda como camino principal.

Si quieres, en el siguiente paso puedo:
1) terminar de corregir teachers/views.py y students/views.py para que usen Enrollment(estudiante, docente, estado) y Clase.docente_base, y  
2) correr docker compose exec web python manage.py check + un smoke test de navegación (login docente/estudiante) para confirmar que no se rompió la UI.