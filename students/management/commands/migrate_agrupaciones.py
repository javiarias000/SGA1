import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Model Imports
from students.models import Student
from teachers.models import Teacher
from subjects.models import Subject
from classes.models import Clase, Enrollment # Assuming Clase and Enrollment are in classes.models


class Command(BaseCommand):
    help = 'Migrates agrupaciones subjects and assigns students and teachers based on JSON data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data migration for agrupaciones...'))

        base_de_datos_json_path = 'base_de_datos_json/asignaciones_grupales'
        agrupaciones_json_path = os.path.join(base_de_datos_json_path, 'ASIGNACIONES_agrupaciones.json')
        docentes_json_path = os.path.join(base_de_datos_json_path, 'asignaciones_docentes.json')

        try:
            with open(agrupaciones_json_path, 'r', encoding='utf-8') as f:
                agrupaciones_data = json.load(f)
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {agrupaciones_json_path}'))
        except FileNotFoundError:
            raise CommandError(f'File not found: {agrupaciones_json_path}')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from {agrupaciones_json_path}')

        try:
            with open(docentes_json_path, 'r', encoding='utf-8') as f:
                docentes_data = json.load(f)
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {docentes_json_path}'))
        except FileNotFoundError:
            raise CommandError(f'File not found: {docentes_json_path}')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from {docentes_json_path}')

        # Placeholder for further migration logic
        # 2. Process ASIGNACIONES_agrupaciones.json to create/update Subject objects
        agrupaciones_subjects = {} # To store created/retrieved Subject objects
        with transaction.atomic():
            for item in agrupaciones_data:
                # Assuming item is a dictionary and subject name is in 'nombre_materia'
                subject_name = item.get('nombre_materia') # Adjust key if different
                if not subject_name:
                    self.stdout.write(self.style.WARNING(f"Skipping agrupacion item due to missing 'nombre_materia': {item}"))
                    continue

                subject, created = Subject.objects.get_or_create(
                    name=subject_name,
                    defaults={'tipo_materia': 'AGRUPACION', 'description': f'Materia de agrupación: {subject_name}'}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Subject: {subject.name} (tipo: {subject.tipo_materia})'))
                else:
                    # If it exists, ensure its type is 'AGRUPACION'
                    if subject.tipo_materia != 'AGRUPACION':
                        subject.tipo_materia = 'AGRUPACION'
                        subject.save()
                        self.stdout.write(self.style.WARNING(f'Updated Subject: {subject.name} to tipo_materia: AGRUPACION'))
                    self.stdout.write(self.style.NOTICE(f'Found existing Subject: {subject.name}'))

                agrupaciones_subjects[subject.name] = subject
        self.stdout.write(self.style.SUCCESS('Finished processing ASIGNACIONES_agrupaciones.json'))

        # 3. Create Clase instances for agrupaciones subjects
        agrupaciones_clases = {}
        with transaction.atomic():
            for subject_name, subject in agrupaciones_subjects.items():
                # Try to find an existing Clase for this subject or create one
                # For now, let's try to get the first teacher available.
                # In a real scenario, this might be more complex,
                # e.g., if the JSON specifies teachers for these classes.
                teacher = Teacher.objects.first() # Get any teacher
                if not teacher:
                    self.stdout.write(self.style.ERROR(f"No teacher found to assign to Clase for subject: {subject.name}"))
                    raise CommandError("No teachers available in the database. Please create at least one teacher.")

                clase_name = f"Clase de {subject.name}"
                clase, created = Clase.objects.get_or_create(
                    subject=subject,
                    name=clase_name,
                    defaults={'teacher': teacher, 'description': f'Clase para la materia de agrupación: {subject.name}'}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Clase: {clase.name} for Subject: {subject.name}'))
                else:
                    self.stdout.write(self.style.NOTICE(f'Found existing Clase: {clase.name} for Subject: {subject.name}'))
                agrupaciones_clases[subject.name] = clase
        self.stdout.write(self.style.SUCCESS('Finished creating Clase instances for agrupaciones.'))

        # 4. Process asignaciones_docentes.json to assign teachers to students and enroll students in agrupaciones
        with transaction.atomic():
            for entry in docentes_data:
                student_name = entry.get('nombre_estudiante') # Assuming student name is here
                teacher_full_name = entry.get('docente_asignado') # Assuming teacher name is here
                agrupacion_subject_name = entry.get('agrupacion_materia') # Assuming agrupacion subject name is here

                if not student_name or not teacher_full_name or not agrupacion_subject_name:
                    self.stdout.write(self.style.WARNING(f"Skipping docentes entry due to missing data: {entry}"))
                    continue

                # Find the student
                # Assuming student_name is sufficient for now, ideally use a unique ID like registration_code
                try:
                    student = Student.objects.get(name=student_name) # Using 'name' for lookup
                except Student.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Student '{student_name}' not found. Skipping assignment."))
                    continue

                # Find the teacher
                try:
                    teacher = Teacher.objects.get(full_name=teacher_full_name) # Using 'full_name' for lookup
                except Teacher.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Teacher '{teacher_full_name}' not found. Skipping assignment for {student_name}."))
                    continue

                # Assign teacher to student
                if student.teacher != teacher:
                    student.teacher = teacher
                    student.save()
                    self.stdout.write(self.style.SUCCESS(f"Assigned Teacher '{teacher_full_name}' to Student '{student_name}'."))
                else:
                    self.stdout.write(self.style.NOTICE(f"Teacher '{teacher_full_name}' already assigned to Student '{student_name}'."))

                # Enroll student in the agrupacion subject
                agrupacion_clase = agrupaciones_clases.get(agrupacion_subject_name)
                if agrupacion_clase:
                    enrollment, created = Enrollment.objects.get_or_create(
                        student=student,
                        clase=agrupacion_clase,
                        defaults={'active': True}
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Enrolled Student '{student_name}' in Clase '{agrupacion_clase.name}'."))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Student '{student_name}' already enrolled in Clase '{agrupacion_clase.name}'."))
                else:
                    self.stdout.write(self.style.WARNING(f"Agrupacion Clase for subject '{agrupacion_subject_name}' not found. Skipping enrollment for '{student_name}'."))

        self.stdout.write(self.style.SUCCESS('Finished processing asignaciones_docentes.json and student enrollments.'))

        self.stdout.write(self.style.SUCCESS('Data migration for agrupaciones completed successfully.'))
