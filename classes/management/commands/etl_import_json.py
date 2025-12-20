import json
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

from subjects.models import Subject
from users.models import Usuario
from teachers.models import Teacher
from students.models import Student
from classes.models import Clase, Enrollment, GradeLevel
from utils.etl_normalization import (
    canonical_subject_name,
    canonical_teacher_name,
    load_aliases,
    map_grade_level,
)


def _norm_text(s: Any) -> str:
    if s is None:
        return ''
    s = str(s)
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    # remove accents
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    return s.casefold()


def _parse_section(paralelo_raw: str) -> str:
    # examples: "B (vespertina)", "A (matutino)", "C (vespertino)"
    if not paralelo_raw:
        return ''
    return paralelo_raw.split('(')[0].strip()


def _map_level(curso_raw: str) -> Optional[str]:
    if not curso_raw:
        return None
    s = _norm_text(curso_raw)
    mapping = {
        '1o': '1',
        '2o': '2',
        '3o': '3',
        '4o': '4',
        '5o': '5',
        '6o': '6',
        '7o': '7',
        '8o': '8',
        '9o': '9',
        '10o': '10',
        '11o': '11',
        '9o (1o bachillerato)': '9',
        '10o (2o bachillerato)': '10',
        '11o (3o bachillerato)': '11',
    }
    for k, v in mapping.items():
        if k in s:
            return v
    return None


def _safe_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _valid_email(email: Optional[str]) -> bool:
    if not email:
        return False
    email = email.strip()
    if email.upper() == 'FALTANTE':
        return False
    return '@' in email


@dataclass
class ETLSummary:
    usuarios_docentes: int = 0
    usuarios_estudiantes: int = 0
    subjects: int = 0
    clases: int = 0
    enrollments: int = 0


class Command(BaseCommand):
    help = 'ETL idempotente: importa base_de_datos_json y normaliza Materias/Clases/Inscripciones (ciclo por defecto 2025-2026).'

    def add_arguments(self, parser):
        parser.add_argument('--ciclo', default='2025-2026')
        parser.add_argument('--base-dir', default='base_de_datos_json')
        parser.add_argument('--create-student-users', action='store_true', help='Crea auth_user para estudiantes (si el email es válido).')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        ciclo: str = opts['ciclo']
        base_dir: str = opts['base_dir']
        create_student_users: bool = opts['create_student_users']
        dry: bool = opts['dry_run']

        docentes_path = os.path.join(base_dir, 'personal_docente', 'DOCENTES.json')
        estudiantes_dir = os.path.join(base_dir, 'estudiantes_matriculados')
        agrup_docentes_path = os.path.join(base_dir, 'asignaciones_grupales', 'asignaciones_docentes.json')
        agrup_asignaciones_path = os.path.join(base_dir, 'asignaciones_grupales', 'ASIGNACIONES_agrupaciones.json')
        instrumentos_dir = os.path.join(base_dir, 'Instrumento_Agrupaciones')

        if not os.path.exists(base_dir):
            raise Exception(f"No existe base-dir: {base_dir}")

        subj_aliases, teacher_aliases = load_aliases(base_dir)

        summary = ETLSummary()
        unmatched_students: List[str] = []
        unmatched_teachers: List[str] = []

        # Cache de usuarios por nombre normalizado
        usuarios_by_normname: Dict[str, List[Usuario]] = {}

        def index_usuario(u: Usuario):
            key = _norm_text(u.nombre)
            usuarios_by_normname.setdefault(key, []).append(u)

        # Pre-index por si ya existen
        for u in Usuario.objects.all().only('id', 'nombre', 'rol'):
            index_usuario(u)

        with transaction.atomic():
            # 1) DOCENTES
            if os.path.exists(docentes_path):
                with open(docentes_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        full_name = (data.get('full_name') or '').strip()
                        email = _safe_str(data.get('email'))
                        username = _safe_str(data.get('username')) or email
                        cedula = _safe_str(data.get('cedula'))
                        phone = _safe_str(data.get('phone'))
                        password = _safe_str(data.get('password_plano'))

                        if not full_name:
                            continue

                        # IMPORTANTE: no usar email=None como clave en update_or_create,
                        # porque colapsa a TODOS los docentes sin email en un solo registro.
                        lookup: Dict[str, Any] = {'rol': Usuario.Rol.DOCENTE}
                        if cedula:
                            lookup['cedula'] = str(cedula)
                        elif _valid_email(email):
                            lookup['email'] = email
                        else:
                            # último recurso: nombre (puede no ser único)
                            lookup['nombre'] = full_name

                        usuario, created_u = Usuario.objects.update_or_create(
                            **lookup,
                            defaults={
                                'rol': Usuario.Rol.DOCENTE,
                                'nombre': full_name,
                                'email': email if _valid_email(email) else None,
                                'phone': phone,
                                'cedula': str(cedula) if cedula else None,
                            }
                        )
                        if created_u:
                            summary.usuarios_docentes += 1
                            index_usuario(usuario)

                        if not dry and username:
                            user, created_user = User.objects.update_or_create(
                                username=username,
                                defaults={
                                    'email': email or '',
                                    'first_name': full_name.split(' ')[0] if full_name else '',
                                    'last_name': ' '.join(full_name.split(' ')[1:]) if full_name else '',
                                    'is_staff': True,
                                }
                            )
                            if password:
                                user.set_password(password)
                                user.save()

                            # Ensure Usuario's auth_user is linked to this User
                            if usuario.auth_user_id != user.id:
                                usuario.auth_user = user
                                usuario.save(update_fields=['auth_user'])

                            # Teacher profile is now created/updated via signal from Usuario save
                            # or can be directly get_or_created via usuario field
                            Teacher.objects.get_or_create(usuario=usuario)

            # 2) ESTUDIANTES
            if os.path.exists(estudiantes_dir):
                for filename in sorted(os.listdir(estudiantes_dir)):
                    if not filename.endswith('.json'):
                        continue
                    if 'Total' in filename:
                        continue

                    path = os.path.join(estudiantes_dir, filename)
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    for item in data:
                        fields = item.get('fields', {})
                        apellidos = (fields.get('Apellidos') or '').strip()
                        nombres = (fields.get('Nombres') or '').strip()
                        full_name = (f"{apellidos} {nombres}").strip() or (fields.get('nombre_completo') or '').strip()
                        if not full_name:
                            continue

                        email = _safe_str(fields.get('email'))
                        cedula = _safe_str(fields.get('Número de Cédula del Estudiante'))

                        usuario = None
                        if cedula:
                            usuario = Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE, cedula=str(cedula)).first()
                        if not usuario and _valid_email(email):
                            usuario = Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE, email=email).first()

                        if not usuario:
                            usuario = Usuario.objects.create(
                                rol=Usuario.Rol.ESTUDIANTE,
                                nombre=full_name,
                                email=email if _valid_email(email) else None,
                                cedula=str(cedula) if cedula else None,
                            )
                            summary.usuarios_estudiantes += 1
                            index_usuario(usuario)

                        # GradeLevel
                        curso_raw = _safe_str(fields.get('CURSO')) or _safe_str(fields.get('Año de estudio'))
                        paralelo_raw = _safe_str(fields.get('PARALELO'))
                        parsed_gl = map_grade_level(curso_raw or '', paralelo_raw or '')
                        grade_level = None
                        if parsed_gl.level and parsed_gl.section:
                            grade_level, _ = GradeLevel.objects.get_or_create(level=parsed_gl.level, section=parsed_gl.section)

                        # Student profile
                        student, _ = Student.objects.update_or_create(
                            usuario=usuario,
                            defaults={
                                'grade_level': grade_level,
                                'active': True,
                            }
                        )

                        # Crear auth_user opcional para estudiantes
                        if create_student_users and not dry and _valid_email(email):
                            username = email
                            user, created_user = User.objects.get_or_create(
                                username=username,
                                defaults={
                                    'email': email,
                                    'first_name': nombres.split(' ')[0] if nombres else '',
                                    'last_name': apellidos,
                                    'is_staff': False,
                                }
                            )
                            if created_user:
                                # contraseña temporal; el middleware forzará cambio si se marca
                                user.set_password('password123')
                                user.save()
                            if usuario.auth_user_id != user.id:
                                usuario.auth_user = user
                                usuario.save(update_fields=['auth_user'])

            # Re-index después de estudiantes/docentes
            usuarios_by_normname = {}
            for u in Usuario.objects.all().only('id', 'nombre', 'rol'):
                index_usuario(u)

            # Helper: encontrar usuario estudiante por nombre
            def find_student_usuario_by_name(full_name: str) -> Optional[Usuario]:
                candidates = usuarios_by_normname.get(_norm_text(full_name), [])
                candidates = [c for c in candidates if c.rol == Usuario.Rol.ESTUDIANTE]
                if not candidates:
                    return None
                # si hay múltiples, elegimos la primera (se loguea en auditoría más adelante si se necesita)
                return candidates[0]

            def find_teacher_usuario_by_name(full_name: str) -> Optional[Usuario]:
                candidates = usuarios_by_normname.get(_norm_text(full_name), [])
                candidates = [c for c in candidates if c.rol == Usuario.Rol.DOCENTE]
                if not candidates:
                    return None
                return candidates[0]

            # 3) AGRUPACIONES: docentes asignados
            agrupacion_to_docente: Dict[str, Usuario] = {}
            if os.path.exists(agrup_docentes_path):
                with open(agrup_docentes_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for row in data:
                    agrup_raw = (row.get('agrupacion') or '').strip()
                    doc_raw = (row.get('docente_asignado') or '').strip()
                    if not agrup_raw or not doc_raw:
                        continue
                    agrup = canonical_subject_name(agrup_raw, subj_aliases)
                    doc = canonical_teacher_name(doc_raw, teacher_aliases)
                    docente_u = find_teacher_usuario_by_name(doc)
                    if not docente_u:
                        unmatched_teachers.append(doc)
                        continue
                    agrupacion_to_docente[_norm_text(agrup)] = docente_u

            # 4) Crear clases + inscripciones de AGRUPACIONES
            if os.path.exists(agrup_asignaciones_path):
                with open(agrup_asignaciones_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for row in data:
                    # algunos JSON ya vienen como dict sin 'fields'
                    fields = row.get('fields') if isinstance(row, dict) and 'fields' in row else row
                    student_name = (fields.get('nombre_completo') or '').strip()
                    agrupacion_raw = (fields.get('agrupacion') or '').strip()
                    agrupacion = canonical_subject_name(agrupacion_raw, subj_aliases)
                    if not student_name or not agrupacion:
                        continue

                    estudiante_u = find_student_usuario_by_name(student_name)
                    if not estudiante_u:
                        unmatched_students.append(student_name)
                        continue
                    
                    # Get the Student profile from the Usuario
                    student_profile = Student.objects.filter(usuario=estudiante_u).first()
                    if not student_profile:
                        self.stdout.write(self.style.WARNING(f"Skipping enrollment for {student_name}: Student profile not found for Usuario {estudiante_u.nombre}."))
                        unmatched_students.append(student_name)
                        continue

                    subject, created_s = Subject.objects.get_or_create(
                        name=agrupacion,
                        defaults={'tipo_materia': 'AGRUPACION'}
                    )
                    if created_s:
                        summary.subjects += 1

                    docente_u = agrupacion_to_docente.get(_norm_text(agrupacion))
                    if not docente_u:
                        # puede existir agrupación sin docente asignado
                        docente_u = None

                    clase, created_c = Clase.objects.get_or_create(
                        subject=subject,
                        ciclo_lectivo=ciclo,
                        paralelo='',
                        docente_base=None,
                        defaults={
                            'name': agrupacion,
                            'active': True,
                        }
                    )
                    if created_c:
                        summary.clases += 1

                    enrollment, created_e = Enrollment.objects.get_or_create(
                        estudiante=estudiante_u, # Pass the Usuario instance here
                        clase=clase,
                        defaults={
                            'docente': docente_u,
                            'estado': 'ACTIVO',
                        }
                    )
                    if not created_e:
                        # update docente si faltaba
                        if docente_u and enrollment.docente_id != docente_u.id:
                            enrollment.docente = docente_u
                            enrollment.estado = 'ACTIVO'
                            enrollment.save(update_fields=['docente', 'estado'])
                    else:
                        summary.enrollments += 1

                    # Compatibilidad legacy: mantener Student.teacher (si existe perfil)
                    if docente_u:
                        teacher_profile = Teacher.objects.filter(usuario=docente_u).first()
                        if teacher_profile:
                            Student.objects.filter(usuario=estudiante_u).update(teacher=teacher_profile)

            # 5) INSTRUMENTOS
            if os.path.exists(instrumentos_dir):
                for filename in sorted(os.listdir(instrumentos_dir)):
                    if not filename.startswith('ASIGNACIONES_') or not filename.endswith('.json'):
                        continue

                    path = os.path.join(instrumentos_dir, filename)
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    for row in data:
                        fields = row.get('fields', {})
                        student_name = (fields.get('full_name') or '').strip()
                        teacher_name_raw = (fields.get('docente_nombre') or '').strip()
                        subject_name_raw = (fields.get('clase') or '').strip()
                        teacher_name = canonical_teacher_name(teacher_name_raw, teacher_aliases)
                        subject_name = canonical_subject_name(subject_name_raw, subj_aliases)
                        if not (student_name and teacher_name and subject_name):
                            continue

                        estudiante_u = find_student_usuario_by_name(student_name)
                        if not estudiante_u:
                            unmatched_students.append(student_name)
                            continue

                        # Get the Student profile from the Usuario
                        student_profile = Student.objects.filter(usuario=estudiante_u).first()
                        if not student_profile:
                            self.stdout.write(self.style.WARNING(f"Skipping enrollment for {student_name}: Student profile not found for Usuario {estudiante_u.nombre}."))
                            unmatched_students.append(student_name)
                            continue

                        docente_u = find_teacher_usuario_by_name(teacher_name)
                        if not docente_u:
                            unmatched_teachers.append(teacher_name)
                            continue

                        subject, created_s = Subject.objects.get_or_create(
                            name=subject_name,
                            defaults={'tipo_materia': 'INSTRUMENTO'}
                        )
                        if created_s:
                            summary.subjects += 1

                        clase_name = f"{subject_name} - {docente_u.nombre}"
                        clase, created_c = Clase.objects.get_or_create(
                            subject=subject,
                            ciclo_lectivo=ciclo,
                            docente_base=docente_u,
                            defaults={
                                'name': clase_name,
                                'active': True,
                                'paralelo': '',
                            }
                        )
                        if created_c:
                            summary.clases += 1

                    enrollment, created_e = Enrollment.objects.get_or_create(
                        estudiante=estudiante_u, # Pass the Usuario instance here
                        clase=clase,
                        defaults={
                            'docente': docente_u,
                            'estado': 'ACTIVO',
                        }
                    )
                    if not created_e:
                        # update docente si faltaba
                        if docente_u and enrollment.docente_id != docente_u.id:
                            enrollment.docente = docente_u
                            enrollment.estado = 'ACTIVO'
                            enrollment.save(update_fields=['docente', 'estado'])
                    else:
                        summary.enrollments += 1

                        # Compatibilidad legacy: mantener Student.teacher (si existe perfil)
                        teacher_profile = Teacher.objects.filter(usuario=docente_u).first()
                        if teacher_profile:
                            Student.objects.filter(usuario=estudiante_u).update(teacher=teacher_profile)

            if dry:
                # Mantener transacción (para poder rollback) y reportar resumen.
                self.stdout.write(self.style.NOTICE(f"Dry-run. Resumen: {summary}"))
                transaction.set_rollback(True)
                return

        # Logs
        logs_dir = os.path.join(base_dir, 'etl_logs')
        os.makedirs(logs_dir, exist_ok=True)

        def _write_list(path: str, values: Iterable[str]):
            with open(path, 'w', encoding='utf-8') as f:
                for v in sorted(set(values)):
                    f.write(v + "\n")

        _write_list(os.path.join(logs_dir, 'unmatched_students.txt'), unmatched_students)
        _write_list(os.path.join(logs_dir, 'unmatched_teachers.txt'), unmatched_teachers)

        self.stdout.write(self.style.SUCCESS(
            f"ETL OK (ciclo={ciclo}). Usuarios docentes nuevos={summary.usuarios_docentes}, estudiantes nuevos={summary.usuarios_estudiantes}, subjects nuevos={summary.subjects}, clases nuevas={summary.clases}, inscripciones nuevas={summary.enrollments}. "
            f"Unmatched estudiantes={len(set(unmatched_students))}, docentes={len(set(unmatched_teachers))}."))
