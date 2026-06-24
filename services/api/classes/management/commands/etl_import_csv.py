import csv
import os
import re
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
from academia.models import Horario
from utils.etl_normalization import (
    canonical_subject_name,
    canonical_teacher_name,
    canonical_student_name,
    load_aliases,
    map_grade_level,
    norm_key,
)

@dataclass
class ETLSummary:
    usuarios_docentes: int = 0
    usuarios_estudiantes: int = 0
    subjects: int = 0
    clases: int = 0
    enrollments: int = 0
    horarios: int = 0

class Command(BaseCommand):
    help = 'ETL for normalized CSV data in base_de_datos_json/normalizado'

    def add_arguments(self, parser):
        parser.add_argument('--ciclo', default='2025-2026')
        parser.add_argument('--base-dir', default='base_de_datos_json')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        ciclo = opts['ciclo']
        base_dir = opts['base_dir']
        dry = opts['dry_run']
        norm_dir = os.path.join(base_dir, 'normalizado')

        if not os.path.exists(norm_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {norm_dir}"))
            return

        subj_aliases, teacher_aliases, student_aliases = load_aliases(base_dir)
        summary = ETLSummary()

        with transaction.atomic():
            # 1. Import Subjects (Instruments first)
            instr_path = os.path.join(norm_dir, 'instrumento.csv')
            if os.path.exists(instr_path):
                with open(instr_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        name = canonical_subject_name(row.get('nombre'), subj_aliases)
                        if name:
                            subject, created = Subject.objects.get_or_create(
                                name=name,
                                defaults={'tipo_materia': 'INSTRUMENTO'}
                            )
                            if created: summary.subjects += 1

            # 2. Import Teachers
            docente_path = os.path.join(norm_dir, 'docente.csv')
            usuarios_docentes_map = {} # cedula -> Usuario
            if os.path.exists(docente_path):
                with open(docente_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cedula = row.get('cedula', '').strip().replace('.', '')
                        nombre = canonical_teacher_name(row.get('nombre_completo'), teacher_aliases)
                        email = row.get('correo_personal') or row.get('correo_institucional')

                        if not nombre: continue

                        # Handle email uniqueness
                        if email:
                            email = email.strip()
                            if Usuario.objects.filter(email=email).exclude(cedula=cedula).exists():
                                email = None # Avoid IntegrityError if email is shared

                        usuario, created = Usuario.objects.update_or_create(
                            cedula=cedula if cedula else None,
                            rol=Usuario.Rol.DOCENTE,
                            defaults={'nombre': nombre, 'email': email}
                        )
                        if created: summary.usuarios_docentes += 1
                        usuarios_docentes_map[cedula] = usuario
                        Teacher.objects.get_or_create(usuario=usuario)

            # 3. Import Students
            estudiante_path = os.path.join(norm_dir, 'estudiante.csv')
            usuarios_estudiantes_map = {} # cedula -> Usuario
            if os.path.exists(estudiante_path):
                with open(estudiante_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cedula = row.get('cedula', '').strip()
                        nombre = (f"{row.get('apellidos', '')} {row.get('nombres', '')}").strip()
                        nombre = canonical_student_name(nombre, student_aliases)
                        email = row.get('correo')

                        if not nombre: continue

                        # Handle email uniqueness
                        if email:
                            email = email.strip()
                            if Usuario.objects.filter(email=email).exclude(cedula=cedula).exists():
                                email = None # Avoid IntegrityError if email is shared

                        usuario, created = Usuario.objects.update_or_create(
                            cedula=cedula if cedula else None,
                            rol=Usuario.Rol.ESTUDIANTE,
                            defaults={'nombre': nombre, 'email': email}
                        )
                        if created: summary.usuarios_estudiantes += 1
                        usuarios_estudiantes_map[cedula] = usuario
                        Student.objects.get_or_create(usuario=usuario)

            # 4. Enrollments & Classes
            # First: Basic matricula (Course/Parallel)
            matricula_path = os.path.join(norm_dir, 'matricula.csv')
            if os.path.exists(matricula_path):
                with open(matricula_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        cedula = row.get('cedula_estudiante', '').strip()
                        est_u = usuarios_estudiantes_map.get(cedula)
                        if not est_u: continue

                        # Basic Enrollment (just to mark student as active in cycle)
                        curso_id = row.get('curso_id')
                        paralelo_id = row.get('paralelo_id')
                        pass

            # Second: Specific assignments (The real classes)
            assignment_files = ['asignacion_instrumento.csv', 'asignacion_agrupacion.csv', 'asignacion_complementario.csv', 'asignacion_acompanamiento.csv']
            for file in assignment_files:
                path = os.path.join(norm_dir, file)
                if not os.path.exists(path): continue

                with open(path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Match student by name if cedula is missing
                        est_cedula = row.get('cedula_estudiante', '').strip()
                        est_u = usuarios_estudiantes_map.get(est_cedula)

                        if not est_u:
                            ap = row.get('apellidos_estudiante', '').strip()
                            nom = row.get('nombres_estudiante', '').strip()
                            full_name_raw = f"{ap} {nom}".strip()
                            if full_name_raw:
                                student_name = canonical_student_name(full_name_raw, student_aliases)
                                for u in Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE):
                                    if norm_key(u.nombre) == norm_key(student_name):
                                        est_u = u
                                        break

                        if not est_u: continue

                        doc_id = row.get('docente_id', '').strip()
                        subj_name_raw = row.get('materia', '') or row.get('instrumento', '')
                        if not subj_name_raw and 'instrumento_id' in row:
                            try:
                                s_obj = Subject.objects.get(id=row.get('instrumento_id'))
                                subj_name_raw = s_obj.name
                            except:
                                pass

                        subj_name = canonical_subject_name(subj_name_raw, subj_aliases)
                        if not subj_name: continue

                        subject, created = Subject.objects.get_or_create(
                            name=subj_name,
                            defaults={'tipo_materia': 'INSTRUMENTO' if 'instrumento' in file else 'AGRUPACION'}
                        )
                        if created: summary.subjects += 1

                        doc_u = None
                        try:
                            doc_u = Usuario.objects.get(id=doc_id)
                        except:
                            pass

                        clase, created = Clase.objects.get_or_create(
                            subject=subject,
                            ciclo_lectivo=ciclo,
                            docente_base=doc_u,
                            defaults={'name': f"{subj_name} - {doc_u.nombre if doc_u else 'TBD'}", 'active': True}
                        )
                        if created: summary.clases += 1

                        enrollment, created = Enrollment.objects.get_or_create(
                            estudiante=est_u,
                            clase=clase,
                            defaults={'docente': doc_u, 'estado': 'ACTIVO'}
                        )
                        if created: summary.enrollments += 1

            if dry:
                self.stdout.write(self.style.NOTICE(f"Dry-run. Resumen: {summary}"))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS(f"Import completed: {summary}"))
