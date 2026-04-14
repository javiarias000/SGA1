"""
Management command: migrar_desde_csv
=====================================
Importa los CSVs normalizados de base_de_datos_json/normalizado/
al modelo de datos Django (idempotente).

Orden de importación (respeta FKs):
  1. docente       → Usuario(DOCENTE) + Teacher
  2. estudiante    → Usuario(ESTUDIANTE) + Student
  3. representante → Student.parent_name/phone (mejor esfuerzo)
  4. instrumento   → Subject(INSTRUMENTO)
  5. agrupacion    → Subject(AGRUPACION)
  6. curso+paralelo→ GradeLevel
  7. matricula     → Student.grade_level
  8. asignacion_instrumento   → Clase + Enrollment(INSTRUMENTO)
  9. asignacion_agrupacion    → Clase + Enrollment(AGRUPACION)
 10. asignacion_acompanamiento→ Clase + Enrollment(AGRUPACION)
 11. asignacion_complementario→ Clase + Enrollment(INSTRUMENTO/complementario)

Uso:
  docker compose exec web python manage.py migrar_desde_csv
  docker compose exec web python manage.py migrar_desde_csv --dry-run
  docker compose exec web python manage.py migrar_desde_csv --csv-dir base_de_datos_json/normalizado --ciclo 2025-2026
"""

import csv
import os
import re
import unicodedata
import logging
from collections import defaultdict
from typing import Optional, Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import Usuario
from students.models import Student
from teachers.models import Teacher
from subjects.models import Subject
from classes.models import Clase, Enrollment, GradeLevel

logger = logging.getLogger(__name__)


# ─── normalización de texto para búsquedas ───────────────────────────────────

def _norm(s) -> str:
    """Quita acentos, pasa a minúsculas, colapsa espacios."""
    if not s:
        return ''
    s = str(s).strip()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).casefold()


def _nombre_completo(apellidos: str, nombres: str) -> str:
    return f"{(apellidos or '').strip()} {(nombres or '').strip()}".strip()


# ─── lector CSV helper ────────────────────────────────────────────────────────

def read_csv(path: str) -> List[Dict]:
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def csv_path(csv_dir: str, name: str) -> str:
    return os.path.join(csv_dir, f'{name}.csv')


# ─── command ─────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Migra CSVs normalizados a la base de datos Django (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-dir',
            default='base_de_datos_json/normalizado',
            help='Directorio con los CSVs normalizados'
        )
        parser.add_argument('--ciclo', default='2025-2026')
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Muestra lo que se haría sin escribir en DB'
        )

    def handle(self, *args, **opts):
        csv_dir: str = opts['csv_dir']
        ciclo: str = opts['ciclo']
        dry: bool = opts['dry_run']

        if not os.path.isdir(csv_dir):
            self.stderr.write(f'No existe: {csv_dir}')
            return

        self.dry = dry
        self.ciclo = ciclo
        self.csv_dir = csv_dir

        # contadores globales
        self.created = defaultdict(int)
        self.updated = defaultdict(int)
        self.skipped = defaultdict(int)
        self.errors: List[str] = []

        # caches en memoria (nombre_norm → obj)
        self._docentes_by_norm: Dict[str, Usuario] = {}
        self._estudiantes_by_norm: Dict[str, Usuario] = {}
        self._subjects_by_norm: Dict[str, Subject] = {}
        self._gradelevels: Dict[Tuple, GradeLevel] = {}  # (level_code, section) → GL

        if dry:
            self.stdout.write(self.style.WARNING('--- DRY RUN (sin escritura) ---'))

        with transaction.atomic():
            self._step1_docentes()
            self._step2_estudiantes()
            self._step3_representantes()
            self._step4_instrumentos()
            self._step5_agrupaciones()
            self._step6_gradelevels()
            self._step7_matriculas()
            self._step8_asignaciones_instrumento()
            self._step9_asignaciones_agrupacion()
            self._step10_asignaciones_acompanamiento()
            self._step11_asignaciones_complementario()

            if dry:
                transaction.set_rollback(True)

        self._print_summary()

    # ── helpers de log ────────────────────────────────────────────────────────

    def _ok(self, entity, action, detail=''):
        self.created[entity] += (1 if action == 'created' else 0)
        self.updated[entity] += (1 if action == 'updated' else 0)
        self.skipped[entity] += (1 if action == 'skipped' else 0)

    def _err(self, msg):
        self.errors.append(msg)

    def _head(self, title):
        self.stdout.write(self.style.HTTP_INFO(f'\n▶ {title}'))

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 1: DOCENTES → Usuario(DOCENTE) + Teacher
    # ─────────────────────────────────────────────────────────────────────────

    def _step1_docentes(self):
        self._head('Paso 1: Docentes')
        rows = read_csv(csv_path(self.csv_dir, 'docente'))

        for r in rows:
            nombre_completo = r.get('nombre_completo', '').strip()
            if not nombre_completo:
                continue

            cedula = r.get('cedula') or None
            email = r.get('correo_institucional') or r.get('correo_personal') or None
            if email:
                email = email.strip() or None
            phone = r.get('celular') or None

            # Busca por cedula primero, luego por nombre normalizado
            usuario = None
            if cedula:
                try:
                    usuario = Usuario.objects.get(cedula=cedula)
                    action = 'skipped'
                except Usuario.DoesNotExist:
                    pass

            if not usuario:
                norm = _norm(nombre_completo)
                try:
                    usuario = Usuario.objects.get(
                        nombre=nombre_completo, rol=Usuario.Rol.DOCENTE
                    )
                    action = 'skipped'
                except Usuario.DoesNotExist:
                    action = 'created'

            if not self.dry and action == 'created':
                usuario = Usuario.objects.create(
                    nombre=nombre_completo,
                    rol=Usuario.Rol.DOCENTE,
                    cedula=cedula,
                    email=email if email and '@' in email else None,
                    phone=phone,
                )
                Teacher.objects.get_or_create(usuario=usuario)
            elif not self.dry and usuario:
                # actualizar campos faltantes
                changed = False
                if cedula and not usuario.cedula:
                    usuario.cedula = cedula
                    changed = True
                if email and '@' in email and not usuario.email:
                    usuario.email = email
                    changed = True
                if phone and not usuario.phone:
                    usuario.phone = phone
                    changed = True
                if changed:
                    usuario.save()
                    action = 'updated'
                Teacher.objects.get_or_create(usuario=usuario)

            if usuario:
                self._docentes_by_norm[_norm(nombre_completo)] = usuario

            self._ok('docente', action)
            if action == 'created':
                self.stdout.write(f'  + Docente: {nombre_completo}')

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 2: ESTUDIANTES → Usuario(ESTUDIANTE) + Student
    # ─────────────────────────────────────────────────────────────────────────

    def _step2_estudiantes(self):
        self._head('Paso 2: Estudiantes')
        rows = read_csv(csv_path(self.csv_dir, 'estudiante'))

        for r in rows:
            apellidos = r.get('apellidos', '').strip()
            nombres   = r.get('nombres', '').strip()
            cedula    = r.get('cedula', '').strip() or None
            email     = r.get('correo', '').strip() or None
            genero    = r.get('genero', '').strip() or None
            fecha_nac = r.get('fecha_nacimiento', '').strip() or None

            nombre_completo = _nombre_completo(apellidos, nombres)
            if not nombre_completo:
                continue

            # Email inválido → no guardar (viola unique=True con None diferente)
            email_ok = email and '@' in email

            usuario = None
            action  = 'created'

            # Busca por cédula (PK natural)
            if cedula:
                try:
                    usuario = Usuario.objects.get(cedula=cedula)
                    action = 'skipped'
                except Usuario.DoesNotExist:
                    pass

            # Busca por email si no encontró por cédula
            if not usuario and email_ok:
                try:
                    usuario = Usuario.objects.get(email=email)
                    action = 'skipped'
                except Usuario.DoesNotExist:
                    pass

            if not usuario and not self.dry:
                try:
                    usuario = Usuario.objects.create(
                        nombre=nombre_completo,
                        rol=Usuario.Rol.ESTUDIANTE,
                        cedula=cedula,
                        email=email if email_ok else None,
                        phone=None,
                    )
                    action = 'created'
                except Exception as e:
                    self._err(f'Estudiante {nombre_completo} ({cedula}): {e}')
                    continue

            if usuario:
                if not self.dry:
                    # Garantizar Student profile
                    Student.objects.get_or_create(usuario=usuario)
                    # Actualizar rol si era PENDIENTE
                    if usuario.rol != Usuario.Rol.ESTUDIANTE:
                        usuario.rol = Usuario.Rol.ESTUDIANTE
                        usuario.save()

                self._estudiantes_by_norm[_norm(nombre_completo)] = usuario

            self._ok('estudiante', action)
            if action == 'created':
                self.stdout.write(f'  + Estudiante: {nombre_completo} ({cedula})')

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 3: REPRESENTANTES → Student.parent_name / parent_phone
    # ─────────────────────────────────────────────────────────────────────────

    def _step3_representantes(self):
        self._head('Paso 3: Representantes → Student')

        # Cargar join estudiante-representante
        est_rep = {
            r['cedula_estudiante']: r
            for r in read_csv(csv_path(self.csv_dir, 'estudiante_representante'))
        }
        representantes = {
            r['cedula']: r
            for r in read_csv(csv_path(self.csv_dir, 'representante'))
        }
        # primer teléfono celular del representante
        telefonos: Dict[str, str] = {}
        for r in read_csv(csv_path(self.csv_dir, 'telefono')):
            ced = r.get('cedula_representante', '')
            if ced not in telefonos and 'CELULAR' in r.get('tipo', ''):
                telefonos[ced] = r.get('numero', '')

        for est_csv in read_csv(csv_path(self.csv_dir, 'estudiante')):
            cedula_est = (est_csv.get('cedula') or '').strip()
            if not cedula_est:
                continue

            try:
                usuario = Usuario.objects.get(cedula=cedula_est)
                student = usuario.student_profile
            except (Usuario.DoesNotExist, Student.DoesNotExist, AttributeError):
                continue

            link = est_rep.get(cedula_est)
            if not link:
                continue

            cedula_rep = link.get('cedula_representante', '')
            rep = representantes.get(cedula_rep, {})

            parent_name = _nombre_completo(
                rep.get('apellidos', ''), rep.get('nombres', '')
            )
            parent_phone = telefonos.get(cedula_rep, '')
            direccion = link.get('direccion', '') or ''

            if not self.dry:
                changed = False
                if parent_name and not student.parent_name:
                    student.parent_name = parent_name
                    changed = True
                if parent_phone and not student.parent_phone:
                    student.parent_phone = parent_phone
                    changed = True
                if direccion and 'Dirección' not in student.notes:
                    student.notes = (student.notes + f'\nDirección: {direccion}').strip()
                    changed = True
                if changed:
                    student.save()
                    self._ok('representante', 'updated')
                else:
                    self._ok('representante', 'skipped')
            else:
                self._ok('representante', 'skipped')

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 4: INSTRUMENTOS → Subject(INSTRUMENTO)
    # ─────────────────────────────────────────────────────────────────────────

    def _step4_instrumentos(self):
        self._head('Paso 4: Instrumentos → Subject')
        for r in read_csv(csv_path(self.csv_dir, 'instrumento')):
            nombre = r.get('nombre', '').strip()
            if not nombre:
                continue
            if not self.dry:
                subj, created = Subject.objects.get_or_create(
                    name=nombre,
                    defaults={'tipo_materia': 'INSTRUMENTO'}
                )
                if not created and subj.tipo_materia != 'INSTRUMENTO':
                    subj.tipo_materia = 'INSTRUMENTO'
                    subj.save()
            self._subjects_by_norm[_norm(nombre)] = None  # placeholder
            action = 'created' if not self.dry else 'skipped'
            self._ok('instrumento', action)

        # Re-indexar desde DB para tener los objetos reales
        if not self.dry:
            for s in Subject.objects.filter(tipo_materia='INSTRUMENTO'):
                self._subjects_by_norm[_norm(s.name)] = s

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 5: AGRUPACIONES → Subject(AGRUPACION)
    # ─────────────────────────────────────────────────────────────────────────

    def _step5_agrupaciones(self):
        self._head('Paso 5: Agrupaciones → Subject')
        for r in read_csv(csv_path(self.csv_dir, 'agrupacion')):
            nombre = r.get('nombre', '').strip()
            if not nombre:
                continue
            if not self.dry:
                subj, created = Subject.objects.get_or_create(
                    name=nombre,
                    defaults={'tipo_materia': 'AGRUPACION'}
                )
            action = 'created' if not self.dry else 'skipped'
            self._ok('agrupacion', action)

        if not self.dry:
            for s in Subject.objects.filter(tipo_materia='AGRUPACION'):
                self._subjects_by_norm[_norm(s.name)] = s

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 6: CURSO + PARALELO + JORNADA → GradeLevel
    # ─────────────────────────────────────────────────────────────────────────

    def _step6_gradelevels(self):
        self._head('Paso 6: GradeLevel (Curso + Paralelo + Jornada)')

        # Cargar lookup tables del CSV
        jornadas = {
            r['id']: r['nombre']
            for r in read_csv(csv_path(self.csv_dir, 'jornada'))
        }
        cursos = {
            r['id']: r['anio']
            for r in read_csv(csv_path(self.csv_dir, 'curso'))
        }

        # Mapa anio_str → level_code (1o → '1', 11o → '11')
        ANIO_MAP = {
            '1o': '1', '2o': '2', '3o': '3', '4o': '4',
            '5o': '5', '6o': '6', '7o': '7', '8o': '8',
            '9o': '9', '10o': '10', '11o': '11',
        }

        for r in read_csv(csv_path(self.csv_dir, 'paralelo')):
            letra      = r.get('letra', '').strip()
            jornada_id = str(r.get('jornada_id', '')).replace('.0', '').strip()
            jornada_nombre = jornadas.get(jornada_id, '')

            # section = letra (compatible con ETL existente)
            section = letra

            # Crear un GradeLevel por cada combinación (level, section)
            for curso_id, anio in cursos.items():
                level_code = ANIO_MAP.get(anio)
                if not level_code:
                    continue

                key = (level_code, section)
                if key in self._gradelevels:
                    continue

                if not self.dry:
                    gl, created = GradeLevel.objects.get_or_create(
                        level=level_code,
                        section=section,
                    )
                    self._gradelevels[key] = gl
                    self._ok('gradelevel', 'created' if created else 'skipped')
                else:
                    self._gradelevels[key] = None
                    self._ok('gradelevel', 'skipped')

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 7: MATRICULA → Student.grade_level
    # ─────────────────────────────────────────────────────────────────────────

    def _step7_matriculas(self):
        self._head('Paso 7: Matrículas → Student.grade_level')

        cursos   = {r['id']: r['anio'] for r in read_csv(csv_path(self.csv_dir, 'curso'))}
        paralelos = {r['id']: r for r in read_csv(csv_path(self.csv_dir, 'paralelo'))}

        ANIO_MAP = {
            '1o':'1','2o':'2','3o':'3','4o':'4','5o':'5',
            '6o':'6','7o':'7','8o':'8','9o':'9','10o':'10','11o':'11',
        }

        for r in read_csv(csv_path(self.csv_dir, 'matricula')):
            cedula_est = (r.get('cedula_estudiante') or '').strip()
            curso_id   = str(r.get('curso_id', '')).replace('.0', '').strip()
            paralelo_id = str(r.get('paralelo_id', '')).replace('.0', '').strip()

            if not cedula_est:
                continue

            anio    = cursos.get(curso_id, '')
            level_code = ANIO_MAP.get(anio)
            paralelo_r = paralelos.get(paralelo_id, {})
            section = (paralelo_r.get('letra') or '').strip()

            if not level_code or not section:
                self._err(f'Matrícula sin nivel/paralelo: est={cedula_est}')
                continue

            gl = self._gradelevels.get((level_code, section))

            if not self.dry and gl:
                try:
                    usuario = Usuario.objects.get(cedula=cedula_est)
                    student = usuario.student_profile
                    if student.grade_level != gl:
                        student.grade_level = gl
                        student.save()
                        self._ok('matricula', 'updated')
                    else:
                        self._ok('matricula', 'skipped')
                except (Usuario.DoesNotExist, Student.DoesNotExist, AttributeError):
                    self._err(f'Matrícula: no se encontró estudiante cedula={cedula_est}')
            else:
                self._ok('matricula', 'skipped')

    # ─────────────────────────────────────────────────────────────────────────
    # Helper: buscar Usuario estudiante por nombre normalizado
    # ─────────────────────────────────────────────────────────────────────────

    def _find_estudiante(self, apellidos: str, nombres: str) -> Optional[Usuario]:
        nombre_completo = _nombre_completo(apellidos, nombres)
        norm = _norm(nombre_completo)

        # Búsqueda exacta
        u = self._estudiantes_by_norm.get(norm)
        if u:
            return u

        # Búsqueda parcial: apellidos
        norm_apellidos = _norm(apellidos)
        for key, usuario in self._estudiantes_by_norm.items():
            if norm_apellidos and norm_apellidos in key:
                return usuario

        return None

    def _find_docente(self, nombre_raw: str) -> Optional[Usuario]:
        if not nombre_raw:
            return None
        norm = _norm(nombre_raw)
        u = self._docentes_by_norm.get(norm)
        if u:
            return u
        # Búsqueda parcial
        for key, usuario in self._docentes_by_norm.items():
            if norm and norm in key:
                return usuario
        return None

    def _get_or_create_clase(
        self,
        subject: Subject,
        docente: Optional[Usuario],
        tipo_materia: str,
    ) -> Optional[Clase]:
        if not subject:
            return None
        try:
            if docente:
                clase, _ = Clase.objects.get_or_create(
                    subject=subject,
                    ciclo_lectivo=self.ciclo,
                    docente_base=docente,
                    defaults={
                        'name': f'{subject.name} - {docente.nombre}',
                        'paralelo': '',
                    }
                )
            else:
                clase, _ = Clase.objects.get_or_create(
                    subject=subject,
                    ciclo_lectivo=self.ciclo,
                    docente_base=None,
                    paralelo='',
                    defaults={'name': subject.name}
                )
            return clase
        except Exception as e:
            self._err(f'Clase {subject.name}: {e}')
            return None

    def _enroll(self, estudiante_u: Usuario, clase: Clase, docente: Optional[Usuario], tipo: str):
        if not estudiante_u or not clase:
            return
        try:
            enroll, created = Enrollment.objects.get_or_create(
                estudiante=estudiante_u,
                clase=clase,
                defaults={
                    'docente': docente,
                    'tipo_materia': tipo,
                    'estado': Enrollment.Estado.ACTIVO,
                }
            )
            self._ok('enrollment', 'created' if created else 'skipped')
        except Exception as e:
            self._err(f'Enrollment {estudiante_u.nombre} → {clase.name}: {e}')

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 8: asignacion_instrumento → Clase + Enrollment(INSTRUMENTO)
    # ─────────────────────────────────────────────────────────────────────────

    def _step8_asignaciones_instrumento(self):
        self._head('Paso 8: Asignaciones Instrumento → Clase + Enrollment')

        instrumentos_csv = {r['id']: r['nombre'] for r in read_csv(csv_path(self.csv_dir, 'instrumento'))}
        docentes_csv     = {r['id']: r['nombre_completo'] for r in read_csv(csv_path(self.csv_dir, 'docente'))}

        unmatched = []
        for r in read_csv(csv_path(self.csv_dir, 'asignacion_instrumento')):
            apellidos   = r.get('apellidos_estudiante', '')
            nombres     = r.get('nombres_estudiante', '')
            instr_id    = str(r.get('instrumento_id', '')).replace('.0', '').strip()
            docente_id  = str(r.get('docente_id', '')).replace('.0', '').strip()

            instr_nombre  = instrumentos_csv.get(instr_id, '')
            docente_nombre = docentes_csv.get(docente_id, '')

            subject = self._subjects_by_norm.get(_norm(instr_nombre))
            docente = self._find_docente(docente_nombre)
            estudiante = self._find_estudiante(apellidos, nombres)

            if not estudiante:
                unmatched.append(f'{apellidos} {nombres}')
                self._ok('enrollment', 'skipped')
                continue

            if not self.dry:
                clase = self._get_or_create_clase(subject, docente, 'INSTRUMENTO')
                if clase:
                    self._enroll(estudiante, clase, docente, 'INSTRUMENTO')
                    self._ok('clase', 'skipped')  # contamos creación en get_or_create
            else:
                self._ok('enrollment', 'skipped')

        if unmatched:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ {len(unmatched)} estudiantes sin match en instrumento: '
                + ', '.join(unmatched[:5]) + ('...' if len(unmatched) > 5 else '')
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 9: asignacion_agrupacion → Clase + Enrollment(AGRUPACION)
    # ─────────────────────────────────────────────────────────────────────────

    def _step9_asignaciones_agrupacion(self):
        self._head('Paso 9: Asignaciones Agrupación → Clase + Enrollment')

        agrupaciones_csv = {r['id']: r['nombre'] for r in read_csv(csv_path(self.csv_dir, 'agrupacion'))}

        unmatched = []
        for r in read_csv(csv_path(self.csv_dir, 'asignacion_agrupacion')):
            apellidos  = r.get('apellidos_estudiante', '')
            nombres    = r.get('nombres_estudiante', '')
            agrup_id   = str(r.get('agrupacion_id', '')).replace('.0', '').strip()

            agrup_nombre = agrupaciones_csv.get(agrup_id, '')
            subject      = self._subjects_by_norm.get(_norm(agrup_nombre))
            estudiante   = self._find_estudiante(apellidos, nombres)

            if not estudiante:
                unmatched.append(f'{apellidos} {nombres}')
                self._ok('enrollment', 'skipped')
                continue

            if not self.dry:
                clase = self._get_or_create_clase(subject, None, 'AGRUPACION')
                if clase:
                    self._enroll(estudiante, clase, None, 'AGRUPACION')
            else:
                self._ok('enrollment', 'skipped')

        if unmatched:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ {len(unmatched)} sin match en agrupación: '
                + ', '.join(unmatched[:5]) + ('...' if len(unmatched) > 5 else '')
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 10: asignacion_acompanamiento
    # ─────────────────────────────────────────────────────────────────────────

    def _step10_asignaciones_acompanamiento(self):
        self._head('Paso 10: Asignaciones Acompañamiento → Clase + Enrollment')

        docentes_csv = {r['id']: r['nombre_completo'] for r in read_csv(csv_path(self.csv_dir, 'docente'))}

        # Busca o crea Subject "Piano Acompañamiento"
        if not self.dry:
            subj_acom, _ = Subject.objects.get_or_create(
                name='Piano Acompañamiento',
                defaults={'tipo_materia': 'INSTRUMENTO'}
            )
        else:
            subj_acom = None

        unmatched = []
        for r in read_csv(csv_path(self.csv_dir, 'asignacion_acompanamiento')):
            apellidos = r.get('apellidos_estudiante', '')
            nombres   = r.get('nombres_estudiante', '')
            doc_instr_id = str(r.get('docente_instrumento_id', '')).replace('.0', '').strip()
            doc_acom_id  = str(r.get('docente_acompanamiento_id', '')).replace('.0', '').strip()

            docente_acom = self._find_docente(docentes_csv.get(doc_acom_id, ''))
            estudiante   = self._find_estudiante(apellidos, nombres)

            if not estudiante:
                unmatched.append(f'{apellidos} {nombres}')
                self._ok('enrollment', 'skipped')
                continue

            if not self.dry:
                clase = self._get_or_create_clase(subj_acom, docente_acom, 'INSTRUMENTO')
                if clase:
                    self._enroll(estudiante, clase, docente_acom, 'INSTRUMENTO')
            else:
                self._ok('enrollment', 'skipped')

        if unmatched:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ {len(unmatched)} sin match en acompañamiento: '
                + ', '.join(unmatched[:5]) + ('...' if len(unmatched) > 5 else '')
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 11: asignacion_complementario
    # ─────────────────────────────────────────────────────────────────────────

    def _step11_asignaciones_complementario(self):
        self._head('Paso 11: Asignaciones Piano Complementario → Clase + Enrollment')

        docentes_csv = {r['id']: r['nombre_completo'] for r in read_csv(csv_path(self.csv_dir, 'docente'))}

        if not self.dry:
            subj_comp, _ = Subject.objects.get_or_create(
                name='Piano Complementario',
                defaults={'tipo_materia': 'INSTRUMENTO'}
            )
        else:
            subj_comp = None

        unmatched = []
        for r in read_csv(csv_path(self.csv_dir, 'asignacion_complementario')):
            apellidos = r.get('apellidos_estudiante', '')
            nombres   = r.get('nombres_estudiante', '')
            doc_comp_id = str(r.get('docente_complementario_id', '')).replace('.0', '').strip()

            docente_comp = self._find_docente(docentes_csv.get(doc_comp_id, ''))
            estudiante   = self._find_estudiante(apellidos, nombres)

            if not estudiante:
                unmatched.append(f'{apellidos} {nombres}')
                self._ok('enrollment', 'skipped')
                continue

            if not self.dry:
                clase = self._get_or_create_clase(subj_comp, docente_comp, 'INSTRUMENTO')
                if clase:
                    self._enroll(estudiante, clase, docente_comp, 'INSTRUMENTO')
            else:
                self._ok('enrollment', 'skipped')

        if unmatched:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ {len(unmatched)} sin match en complementario: '
                + ', '.join(unmatched[:5]) + ('...' if len(unmatched) > 5 else '')
            ))

    # ─────────────────────────────────────────────────────────────────────────
    # RESUMEN
    # ─────────────────────────────────────────────────────────────────────────

    def _print_summary(self):
        self.stdout.write(self.style.SUCCESS('\n═══ RESUMEN ═══'))
        headers = ['Entidad', 'Creados', 'Actualizados', 'Omitidos']
        entities = sorted(set(list(self.created.keys()) + list(self.updated.keys()) + list(self.skipped.keys())))
        row_fmt = '  {:<25} {:>8} {:>13} {:>9}'
        self.stdout.write(row_fmt.format(*headers))
        self.stdout.write('  ' + '-' * 55)
        for e in entities:
            self.stdout.write(row_fmt.format(
                e,
                self.created.get(e, 0),
                self.updated.get(e, 0),
                self.skipped.get(e, 0),
            ))

        if self.errors:
            self.stdout.write(self.style.ERROR(f'\n⚠ {len(self.errors)} errores:'))
            for err in self.errors[:20]:
                self.stdout.write(f'  - {err}')
            if len(self.errors) > 20:
                self.stdout.write(f'  ... y {len(self.errors) - 20} más')

        if self.dry:
            self.stdout.write(self.style.WARNING('\n(DRY RUN — ningún cambio guardado)'))
