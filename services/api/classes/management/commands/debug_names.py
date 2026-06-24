import os
import json
from django.core.management.base import BaseCommand
from teachers.models import Teacher
from subjects.models import Subject

class Command(BaseCommand):
    help = 'Debugs teacher and subject names from horarios JSON and database'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Debugging Names ---'))

        json_base_dir = '/usr/src/base_de_datos_json'
        horarios_file_path = os.path.join(json_base_dir, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json')

        if not os.path.exists(horarios_file_path):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {horarios_file_path}'))
            return

        # 1. Extract all unique teacher names and subject names from horarios JSON
        json_teacher_names = set()
        json_subject_names = set()
        with open(horarios_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            fields = item.get('fields', {})
            teacher_name = fields.get('docente', '').strip()
            subject_name = fields.get('asignatura', '').strip()

            if teacher_name and teacher_name != 'ND':
                json_teacher_names.add(teacher_name)
            if subject_name:
                json_subject_names.add(subject_name)

        self.stdout.write(self.style.NOTICE('\n--- Unique Teacher Names from Horarios JSON ---'))
        for name in sorted(list(json_teacher_names)):
            self.stdout.write(f'- {name}')

        self.stdout.write(self.style.NOTICE('\n--- Unique Subject Names from Horarios JSON ---'))
        for name in sorted(list(json_subject_names)):
            self.stdout.write(f'- {name}')

        # 2. Extract all existing teacher full names from the database
        db_teacher_names = {t.full_name for t in Teacher.objects.all()}
        self.stdout.write(self.style.NOTICE('\n--- Existing Teacher Full Names in DB ---'))
        for name in sorted(list(db_teacher_names)):
            self.stdout.write(f'- {name}')

        # 3. Extract all existing subject names from the database
        db_subject_names = {s.name for s in Subject.objects.all()}
        self.stdout.write(self.style.NOTICE('\n--- Existing Subject Names in DB ---'))
        for name in sorted(list(db_subject_names)):
            self.stdout.write(f'- {name}')

        # 4. Compare and find mismatches
        self.stdout.write(self.style.NOTICE('\n--- Teacher Names in JSON but NOT in DB ---'))
        for name in sorted(list(json_teacher_names - db_teacher_names)):
            self.stdout.write(f'- {name}')
        
        self.stdout.write(self.style.NOTICE('\n--- Subject Names in JSON but NOT in DB ---'))
        for name in sorted(list(json_subject_names - db_subject_names)):
            self.stdout.write(f'- {name}')

        self.stdout.write(self.style.SUCCESS('\n--- Debugging Names Finished ---'))
