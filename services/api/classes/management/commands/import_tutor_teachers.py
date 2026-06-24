import json
import os
import re
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from classes.models import GradeLevel
from teachers.models import Teacher
from users.models import Usuario

def _norm_text(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    return s.casefold()

class Command(BaseCommand):
    help = 'Imports tutor teachers from a JSON file and assigns them to GradeLevel objects.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='base_de_datos_json/personal_docente/REPORTE_TUTORES_CURSOS_20251204_165037.json',
            help='Path to the JSON file containing tutor data.'
        )

    def handle(self, *args, **options):
        file_path = options['file']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            tutor_data = json.load(f)

        self.stdout.write(self.style.SUCCESS(f"Processing {len(tutor_data)} tutor entries..."))

        # Cache for Teachers
        teachers_cache = {}
        for teacher in Teacher.objects.all().select_related('usuario'):
            if teacher.usuario:
                teachers_cache[_norm_text(teacher.usuario.nombre)] = teacher

        # Cache for GradeLevels
        grade_levels_cache = {}
        for gl in GradeLevel.objects.all():
            grade_levels_cache[(_norm_text(gl.level), _norm_text(gl.section))] = gl

        updated_grade_levels_count = 0
        skipped_entries_count = 0

        with transaction.atomic():
            for entry in tutor_data:
                fields = entry.get('fields', {})
                curso_raw = fields.get('curso', '').replace('Año (', '(').replace('O Bachillerato)', '') # Normalize name
                paralelo_raw = fields.get('paralelo', '')
                tutor_name_raw = fields.get('tutor', '')

                if not (curso_raw and paralelo_raw and tutor_name_raw):
                    self.stdout.write(self.style.WARNING(f"Skipping entry due to missing data: {entry}"))
                    skipped_entries_count += 1
                    continue

                # Normalize grade level names to match GradeLevel.level choices
                level_map = {
                    _norm_text("Primero"): "1",
                    _norm_text("Segundo"): "2",
                    _norm_text("Tercero"): "3",
                    _norm_text("Cuarto"): "4",
                    _norm_text("Quinto"): "5",
                    _norm_text("Sexto"): "6",
                    _norm_text("Septimo"): "7",
                    _norm_text("Octavo"): "8",
                    _norm_text("Noveno (1"): "9", # "Noveno Año (1O Bachillerato)"
                    _norm_text("Decimo (2"): "10", # "Decimo Año (2O Bachillerato)"
                    _norm_text("Decimo Primer (3"): "11", # "Decimo Primer Año (3O Bachillerato)"
                }
                
                normalized_curso_key = None
                for k, v in level_map.items():
                    if k in _norm_text(curso_raw):
                        normalized_curso_key = v
                        break
                
                if not normalized_curso_key:
                    self.stdout.write(self.style.WARNING(f"Skipping entry: Could not map curso '{curso_raw}' to a GradeLevel level. Entry: {entry}"))
                    skipped_entries_count += 1
                    continue

                # Find GradeLevel
                grade_level = grade_levels_cache.get((_norm_text(normalized_curso_key), _norm_text(paralelo_raw)))
                
                if not grade_level:
                    # Try to create if not found (assuming level and section are required and have defaults if not provided)
                    # Note: GradeLevel.level is a CharField, needs value from choices
                    try:
                        grade_level, created = GradeLevel.objects.get_or_create(
                            level=normalized_curso_key,
                            section=paralelo_raw,
                            defaults={} # No other defaults needed for creation if level/section are sufficient
                        )
                        if created:
                            self.stdout.write(self.style.NOTICE(f"Created GradeLevel: {grade_level}"))
                            grade_levels_cache[(_norm_text(grade_level.level), _norm_text(grade_level.section))] = grade_level
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error creating GradeLevel for {curso_raw} {paralelo_raw}: {e}. Skipping entry: {entry}"))
                        skipped_entries_count += 1
                        continue


                # Find Teacher
                normalized_tutor_name = _norm_text(tutor_name_raw)
                teacher = teachers_cache.get(normalized_tutor_name)

                if not teacher:
                    self.stdout.write(self.style.WARNING(f"Skipping entry: Teacher '{tutor_name_raw}' not found. Entry: {entry}"))
                    skipped_entries_count += 1
                    continue

                # Assign tutor to GradeLevel
                if grade_level.docente_tutor != teacher:
                    grade_level.docente_tutor = teacher
                    grade_level.save()
                    updated_grade_levels_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Assigned {teacher.full_name} as tutor for GradeLevel: {grade_level}"
                    ))
                else:
                    self.stdout.write(self.style.NOTICE(
                        f"Teacher {teacher.full_name} already assigned as tutor for GradeLevel: {grade_level}. Skipping update."
                    ))

        self.stdout.write(self.style.SUCCESS(
            f"Tutor import completed. Updated {updated_grade_levels_count} GradeLevels. Skipped {skipped_entries_count} entries."
        ))