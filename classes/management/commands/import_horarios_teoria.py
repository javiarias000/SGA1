import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from classes.models import Clase, Enrollment, GradeLevel, Horario
from students.models import Student
from subjects.models import Subject
from users.models import Usuario
from utils.etl_normalization import (
    canonical_subject_name,
    canonical_teacher_name,
    clase_paralelo_key_for_grade,
    load_aliases,
    map_grade_level,
    norm_key,
)


_DAY_MAP = {
    'LUNES': 'Lunes',
    'MARTES': 'Martes',
    'MIERCOLES': 'Miércoles',
    'MIÉRCOLES': 'Miércoles',
    'JUEVES': 'Jueves',
    'VIERNES': 'Viernes',
    'SABADO': 'Sábado',
    'SÁBADO': 'Sábado',
    'DOMINGO': 'Domingo',
}


@dataclass
class Summary:
    subjects_created: int = 0
    clases_created: int = 0
    horarios_created: int = 0
    enrollments_created: int = 0
    horarios_rows_processed: int = 0
    horarios_rows_skipped_agrupacion: int = 0
    horarios_rows_skipped_bad_grade: int = 0


def _parse_time_range(raw: str) -> Optional[Tuple[Any, Any]]:
    # Expected: "07:30 a 08:15"
    if not raw:
        return None
    s = str(raw).strip()
    if 'a' not in s:
        return None
    left, right = [p.strip() for p in s.split('a', 1)]
    try:
        h1 = datetime.strptime(left, '%H:%M').time()
        h2 = datetime.strptime(right, '%H:%M').time()
        return h1, h2
    except Exception:
        return None


class Command(BaseCommand):
    help = (
        'Importa horarios TEORÍA desde base_de_datos_json/horarios_academicos/ y crea ' 
        'Clase+Horario+Enrollment (inscripción por curso/paralelo).'
    )

    def add_arguments(self, parser):
        parser.add_argument('--base-dir', default='base_de_datos_json')
        parser.add_argument('--ciclo', default='2025-2026')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        base_dir: str = opts['base_dir']
        ciclo: str = opts['ciclo']
        dry: bool = opts['dry_run']

        subj_aliases, teacher_aliases = load_aliases(base_dir)

        logs_dir = os.path.join(base_dir, 'etl_logs')
        os.makedirs(logs_dir, exist_ok=True)

        horarios_path = os.path.join(base_dir, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json')
        if not os.path.exists(horarios_path):
            raise Exception(f'No existe horarios JSON: {horarios_path}')

        # Agrupaciones set (rule: if also in agrupaciones, treat as AGRUPACION and skip TEORIA import)
        agrupaciones_set: Set[str] = set()
        agrup_asig_path = os.path.join(base_dir, 'asignaciones_grupales', 'ASIGNACIONES_agrupaciones.json')
        if os.path.exists(agrup_asig_path):
            try:
                agrup_data = json.load(open(agrup_asig_path, 'r', encoding='utf-8'))
                for row in agrup_data:
                    agrup = canonical_subject_name(row.get('agrupacion'), subj_aliases)
                    if agrup:
                        agrupaciones_set.add(norm_key(agrup))
            except Exception:
                # best-effort
                pass

        # Pre-index docentes (Usuario.rol=DOCENTE)
        docentes_by_norm: Dict[str, List[Usuario]] = defaultdict(list)
        for u in Usuario.objects.filter(rol=Usuario.Rol.DOCENTE).only('id', 'nombre', 'rol'):
            docentes_by_norm[norm_key(u.nombre)].append(u)

        def find_docente(nombre: str) -> Optional[Usuario]:
            if not nombre:
                return None
            c = canonical_teacher_name(nombre, teacher_aliases)
            if not c:
                return None
            candidates = docentes_by_norm.get(norm_key(c), [])
            return candidates[0] if candidates else None

        unmatched_teachers: List[str] = []
        multi_teacher_conflicts: List[str] = []

        summary = Summary()

        with open(horarios_path, 'r', encoding='utf-8') as f:
            horarios_data = json.load(f)

        # Track teacher per (subject_norm, grade_level_id)
        teacher_seen: Dict[Tuple[str, int], int] = {}

        with transaction.atomic():
            for row in horarios_data:
                fields = row.get('fields', {}) or {}
                summary.horarios_rows_processed += 1

                curso = fields.get('curso')
                paralelo = fields.get('paralelo')
                parsed = map_grade_level(curso, paralelo)
                if not (parsed.level and parsed.section):
                    summary.horarios_rows_skipped_bad_grade += 1
                    continue

                grade_level, _ = GradeLevel.objects.get_or_create(level=parsed.level, section=parsed.section)

                raw_subject = fields.get('clase')
                subject_name = canonical_subject_name(raw_subject, subj_aliases)
                if not subject_name:
                    continue

                if norm_key(subject_name) in agrupaciones_set:
                    summary.horarios_rows_skipped_agrupacion += 1
                    continue

                subject, created_s = Subject.objects.get_or_create(
                    name=subject_name,
                    defaults={'tipo_materia': 'TEORIA'}
                )
                if created_s:
                    summary.subjects_created += 1
                else:
                    # If it was created earlier as OTRO, upgrade to TEORIA.
                    if subject.tipo_materia == 'OTRO':
                        subject.tipo_materia = 'TEORIA'
                        subject.save(update_fields=['tipo_materia'])

                paralelo_key = clase_paralelo_key_for_grade(parsed.level, parsed.section)
                clase_defaults = {
                    'name': f"{subject.name} ({grade_level})",
                    'active': True,
                    'grade_level': grade_level,
                }
                clase, created_c = Clase.objects.get_or_create(
                    subject=subject,
                    ciclo_lectivo=ciclo,
                    paralelo=paralelo_key,
                    docente_base=None,
                    defaults=clase_defaults,
                )
                if created_c:
                    summary.clases_created += 1
                else:
                    # keep it consistent
                    updates = {}
                    if clase.grade_level_id != grade_level.id:
                        updates['grade_level'] = grade_level
                    if clase.name != clase_defaults['name']:
                        updates['name'] = clase_defaults['name']
                    if updates:
                        for k, v in updates.items():
                            setattr(clase, k, v)
                        clase.save(update_fields=list(updates.keys()))

                # Horario
                dia_raw = (fields.get('dia') or '').upper().strip()
                dia = _DAY_MAP.get(dia_raw)
                time_range = _parse_time_range(fields.get('hora') or '')
                if dia and time_range:
                    hora_inicio, hora_fin = time_range
                    horario, created_h = Horario.objects.update_or_create(
                        clase=clase,
                        dia_semana=dia,
                        hora_inicio=hora_inicio,
                        defaults={'hora_fin': hora_fin},
                    )
                    if created_h:
                        summary.horarios_created += 1

                # Docente
                docente_name_raw = fields.get('docente')
                docente_u = find_docente(docente_name_raw)
                if docente_name_raw and not docente_u:
                    unmatched_teachers.append(str(docente_name_raw).strip())

                # Detect multi-teacher conflicts for the same subject+grade_level
                key = (norm_key(subject.name), grade_level.id)
                if docente_u:
                    prev = teacher_seen.get(key)
                    if prev is None:
                        teacher_seen[key] = docente_u.id
                    elif prev != docente_u.id:
                        multi_teacher_conflicts.append(
                            f"{subject.name} / {grade_level}: docentes distintos en horarios (prev={prev}, nuevo={docente_u.id})."
                        )
                        # Keep first-seen teacher to avoid duplicating enrollments.
                        docente_u = Usuario.objects.filter(id=prev).first() or docente_u

                # Enroll all students in that GradeLevel
                students_qs = Student.objects.filter(active=True, grade_level=grade_level).exclude(usuario__isnull=True)
                for st in students_qs.select_related('usuario'):
                    enr, created_e = Enrollment.objects.get_or_create(
                        estudiante=st.usuario,
                        clase=clase,
                        defaults={'docente': docente_u, 'estado': 'ACTIVO'},
                    )
                    if created_e:
                        summary.enrollments_created += 1
                    else:
                        # update docente/estado if needed
                        updates = []
                        if docente_u and enr.docente_id != docente_u.id:
                            enr.docente = docente_u
                            updates.append('docente')
                        if enr.estado != 'ACTIVO':
                            enr.estado = 'ACTIVO'
                            updates.append('estado')
                        if updates:
                            enr.save(update_fields=updates)

            if dry:
                raise Exception(f"Dry-run. Summary={summary}")

        def _write_list(path: str, values: Iterable[str]) -> None:
            values = [v for v in values if v and str(v).strip()]
            with open(path, 'w', encoding='utf-8') as f:
                for v in sorted(set(values), key=lambda x: norm_key(x)):
                    f.write(str(v).strip() + '\n')

        _write_list(os.path.join(logs_dir, 'unmatched_teachers_horarios_teoria.txt'), unmatched_teachers)
        _write_list(os.path.join(logs_dir, 'multi_teacher_conflicts_teoria.txt'), multi_teacher_conflicts)

        self.stdout.write(self.style.SUCCESS(
            f"OK import_horarios_teoria (ciclo={ciclo}). subjects_created={summary.subjects_created}, "
            f"clases_created={summary.clases_created}, horarios_created={summary.horarios_created}, "
            f"enrollments_created={summary.enrollments_created}, "
            f"rows_processed={summary.horarios_rows_processed}, rows_skipped_agrup={summary.horarios_rows_skipped_agrupacion}, "
            f"rows_skipped_bad_grade={summary.horarios_rows_skipped_bad_grade}."
        ))