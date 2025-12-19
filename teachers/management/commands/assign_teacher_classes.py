# teachers/management/commands/assign_teacher_classes.py
import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Model Imports
from teachers.models import Teacher
from subjects.models import Subject
from classes.models import Clase # Assuming Clase is in classes.models


class Command(BaseCommand):
    help = 'Assigns teachers to classes (Subjects) based on REPORTE_DOCENTES_HORARIOS JSON data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting teacher-class assignment migration...'))

        base_de_datos_json_path = 'base_de_datos_json'
        horarios_json_path = os.path.join(base_de_datos_json_path, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json')
        # This file might not be directly used for teacher-class assignment, but loaded as requested
        # asignaciones_docentes_json_path = os.path.join(base_de_datos_json_path, 'asignaciones_grupales', 'asignaciones_docentes.json')

        horarios_data = []
        try:
            with open(horarios_json_path, 'r', encoding='utf-8') as f:
                horarios_data = json.load(f)
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {horarios_json_path}'))
        except FileNotFoundError:
            raise CommandError(f'File not found: {horarios_json_path}')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from {horarios_json_path}')

        # Process REPORTE_DOCENTES_HORARIOS_0858.json
        teachers_to_update = {} # To keep track of teachers and their subjects

        with transaction.atomic():
            for entry in horarios_data:
                fields = entry.get('fields', {})
                docente_name_raw = fields.get('docente')
                clase_name_raw = fields.get('clase')
                curso = fields.get('curso', '')
                paralelo = fields.get('paralelo', '')
                dia = fields.get('dia', '')
                hora = fields.get('hora', '')
                aula = fields.get('aula', '')

                if not docente_name_raw or docente_name_raw.strip().upper() == 'ND':
                    self.stdout.write(self.style.WARNING(f"Skipping entry due to missing or 'ND' docente: {entry}"))
                    continue
                if not clase_name_raw:
                    self.stdout.write(self.style.WARNING(f"Skipping entry due to missing 'clase' name: {entry}"))
                    continue

                # 1. Clean teacher name
                docente_name = docente_name_raw.replace('.', '').strip()

                # 2. Determine tipo_materia and get/create Subject
                tipo_materia = 'OTRO' # Default
                clase_name_lower = clase_name_raw.lower()

                if 'agrupacion' in clase_name_lower:
                    tipo_materia = 'AGRUPACION'
                elif 'instrumento' in clase_name_lower:
                    tipo_materia = 'INSTRUMENTO'
                # Add more rules for 'TEORIA' if specific keywords are found
                # For now, anything not 'agrupacion' or 'instrumento' could be 'teoria' or 'otro'

                subject, created = Subject.objects.get_or_create(
                    name=clase_name_raw,
                    defaults={'tipo_materia': tipo_materia, 'description': f'Materia de {clase_name_raw}'}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Subject: {subject.name} (tipo: {subject.tipo_materia})'))
                else:
                    # If it exists, ensure its type is correct, but only if it's not already set
                    if subject.tipo_materia == 'OTRO' and tipo_materia != 'OTRO':
                        subject.tipo_materia = tipo_materia
                        subject.save()
                        self.stdout.write(self.style.WARNING(f'Updated Subject: {subject.name} to tipo_materia: {tipo_materia}'))
                    self.stdout.write(self.style.NOTICE(f'Found existing Subject: {subject.name}'))

                # 3. Find Teacher
                teacher = None
                try:
                    # We might need a more robust way to find teachers,
                    # as names might not be perfectly unique or formatted.
                    # User model linked to Teacher has first_name, last_name
                    # Teacher model has full_name
                    teacher = Teacher.objects.get(full_name__icontains=docente_name)
                except Teacher.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Teacher '{docente_name}' not found. Cannot assign class '{clase_name_raw}'."))
                    continue
                except Teacher.MultipleObjectsReturned:
                    self.stdout.write(self.style.ERROR(f"Multiple teachers found for '{docente_name}'. Cannot assign class '{clase_name_raw}'."))
                    continue

                # 4. Get/Create Clase
                # A Clase needs to be unique. Using a combination of subject, course, parallel, day, time.
                clase_unique_name = f"{subject.name} - {curso} {paralelo} ({dia} {hora})"
                clase, created = Clase.objects.get_or_create(
                    subject=subject,
                    name=clase_unique_name,
                    defaults={
                        'teacher': teacher,
                        'description': f'Clase de {subject.name} para {curso} {paralelo}',
                        'schedule': f'{dia} {hora}',
                        'room': aula if aula.strip().upper() != 'ND' else '',
                        # You might want to add 'fecha' or other defaults here if applicable
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Clase: {clase.name} ({clase.teacher.full_name})'))
                else:
                    # If existing, ensure the teacher is correct
                    if clase.teacher != teacher:
                        clase.teacher = teacher
                        clase.save()
                        self.stdout.write(self.style.WARNING(f'Updated Clase {clase.name} teacher to {teacher.full_name}'))
                    self.stdout.write(self.style.NOTICE(f'Found existing Clase: {clase.name} ({clase.teacher.full_name})'))

                # 5. Assign Teacher to Subject (M2M)
                if teacher and subject:
                    if subject not in teacher.subjects.all():
                        teacher.subjects.add(subject)
                        self.stdout.write(self.style.SUCCESS(f"Assigned Subject '{subject.name}' to Teacher '{teacher.full_name}'."))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Subject '{subject.name}' already assigned to Teacher '{teacher.full_name}'."))

        self.stdout.write(self.style.SUCCESS('Finished processing REPORTE_DOCENTES_HORARIOS_0858.json data.'))

        self.stdout.write(self.style.SUCCESS('Teacher-class assignment migration completed successfully.'))
