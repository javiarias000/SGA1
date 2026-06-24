
import json
import os
import glob
from django.core.management.base import BaseCommand
from classes.models import GradeLevel
from utils.etl_normalization import map_grade_level

class Command(BaseCommand):
    help = 'Imports unique GradeLevels from student matriculation JSON files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path_pattern',
            type=str,
            help='Glob pattern for JSON files containing student data (e.g., base_de_datos_json/estudiantes_matriculados/*.json)',
            default='base_de_datos_json/estudiantes_matriculados/*.json'
        )

    def handle(self, *args, **options):
        path_pattern = options['path_pattern']
        json_files = glob.glob(path_pattern)

        if not json_files:
            self.stdout.write(self.style.ERROR(f'No JSON files found matching pattern: {path_pattern}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Importing grade levels from files matching {path_pattern}...'))

        unique_grade_levels = set() # Store (level, section) tuples
        
        for json_path in json_files:
            self.stdout.write(f'Processing file: {json_path}')
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Error decoding JSON from {json_path}: {e}'))
                continue
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
                continue

            if not isinstance(data, list):
                self.stdout.write(self.style.ERROR(f'Expected a list of objects in {json_path}, skipping.'))
                continue

            for entry in data:
                curso_raw = entry.get('fields', {}).get('CURSO')
                paralelo_raw = entry.get('fields', {}).get('PARALELO')
                
                parsed_grade_level = map_grade_level(curso_raw, paralelo_raw)
                
                if parsed_grade_level.level and parsed_grade_level.section:
                    unique_grade_levels.add((parsed_grade_level.level, parsed_grade_level.section))
                elif curso_raw and paralelo_raw: # Log if raw data exists but couldn't be mapped
                    self.stdout.write(self.style.WARNING(
                        f'Could not map grade level from "{curso_raw}" and "{paralelo_raw}" in {json_path}. '
                        f'Mapped to: Level={parsed_grade_level.level}, Section={parsed_grade_level.section}'
                    ))

        created_count = 0
        updated_count = 0

        for level, section in unique_grade_levels:
            grade_level_obj, created = GradeLevel.objects.get_or_create(
                level=level,
                section=section,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created GradeLevel: {grade_level_obj.get_level_display()} "{grade_level_obj.section}"'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'GradeLevel already exists: {grade_level_obj.get_level_display()} "{grade_level_obj.section}"'))
        
        self.stdout.write(self.style.SUCCESS(f'Finished importing grade levels. Created: {created_count}, Existing: {updated_count}'))
