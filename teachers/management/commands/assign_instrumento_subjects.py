# teachers/management/commands/assign_instrumento_subjects.py
import json
import os
import glob
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import models # Correct way to import models module
from django.db.models import Q, F, Func, Value, ExpressionWrapper # Removed fields
from django.db.models.functions import Replace # Import Replace

# Model Imports
from teachers.models import Teacher
from students.models import Student
from subjects.models import Subject
from classes.models import Clase, Enrollment # Assuming Clase and Enrollment are in classes.models

def normalize_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().replace('.', '').strip()
    # Remove common titles if present
    titles = ["mgs", "lic", "dr", "ing"]
    for title in titles:
        name = name.replace(title + ' ', '')
    return ' '.join(name.split()) # Remove multiple spaces

KNOWN_NON_TEACHER_NAMES = [
    "piano", "violín", "nulo", "maestro de instrumento",
    "rendí prueba de ubicación no tengo maestro asignado",
    "violín", "contrabajo", "flauta traversa", "guitarra",
    "percusión", "saxofón", "trombón", "trompeta", "viola", "violonchelo",
    "acompañamiento", "complementario", "conj. inst",
    "instrumento que estudia en el conservatorio bolívar"
]

class Command(BaseCommand):
    help = 'Assigns instrumento subjects to teachers and enrolls students based on JSON files.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting instrumento subject assignment migration...'))

        # --- PRE-PROCESSING STEPS ---

        # 0. Load ESTUDIANTES_CON_REPRESENTANTES.json for student name completion
        estudiantes_con_rep_path = os.path.join('base_de_datos_json', 'Instrumento_Agrupaciones', 'ESTUDIANTES_CON_REPRESENTANTES.json')
        estudiantes_con_rep_data = []
        try:
            with open(estudiantes_con_rep_path, 'r', encoding='utf-8') as f:
                estudiantes_con_rep_data = json.load(f)
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {estudiantes_con_rep_path} for student name completion.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {estudiantes_con_rep_path}. Student name completion may be limited.'))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Error decoding JSON from {estudiantes_con_rep_path}. Student name completion may be limited.'))

        # Create a list of full names from ESTUDIANTES_CON_REPRESENTANTES.json for matching
        json_student_full_names = [normalize_name(entry.get('fields', {}).get('full_name', '')) for entry in estudiantes_con_rep_data if entry.get('fields', {}).get('full_name')]
        json_student_full_names = list(set(json_student_full_names)) # Get unique names

        # 1. Delete Student records with empty names
        with transaction.atomic():
            empty_name_students = Student.objects.filter(name='')
            if empty_name_students.exists():
                count = empty_name_students.count()
                empty_name_students.delete()
                self.stdout.write(self.style.WARNING(f"Deleted {count} Student records with empty names."))
            else:
                self.stdout.write(self.style.NOTICE("No Student records with empty names found to delete."))

            # 2. Attempt to complete incomplete student names
            # Heuristic: consider names with less than 3 words as potentially incomplete
            incomplete_students = Student.objects.annotate(
                num_words=ExpressionWrapper(
                    Func(F('name'), function='LENGTH') - Func(Replace(F('name'), Value(' '), Value('')), function='LENGTH') + Value(1),
                    output_field=models.IntegerField()
                )
            ).filter(
                Q(num_words__lt=3) | Q(name__regex=r'^\s*\w+\s*\w+\s*$')
            ).exclude(name__exact='').exclude(name__regex=r'^\s*$') # Exclude already empty names
            



            self.stdout.write(self.style.NOTICE(f"Found {incomplete_students.count()} potentially incomplete student names in DB to attempt completion."))

            for db_student in incomplete_students:
                normalized_db_name = normalize_name(db_student.name)
                
                if not normalized_db_name: # Should not happen after deleting empty names, but as a safeguard
                    continue

                matching_full_names = []
                for json_full_name in json_student_full_names:
                    # Check if the incomplete DB name is a substring of a JSON full name
                    if normalized_db_name in json_full_name:
                        matching_full_names.append(json_full_name)
                
                if len(matching_full_names) == 1:
                    matched_full_name = matching_full_names[0]
                    # Update DB student's name
                    if normalize_name(db_student.name) != matched_full_name: # db_student.name is now a property
                        # Update the Usuario's name
                        if db_student.usuario:
                            db_student.usuario.nombre = matched_full_name.title()
                            db_student.usuario.save(update_fields=['nombre'])
                            self.stdout.write(self.style.SUCCESS(f"Updated Student '{normalized_db_name}' (via Usuario) to '{db_student.name}'.")) # db_student.name will reflect the change
                        else:
                            self.stdout.write(self.style.WARNING(f"Student '{db_student.name}' has no associated Usuario. Cannot update name. (original: {normalized_db_name})"))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Student '{db_student.name}' already complete."))
                elif len(matching_full_names) > 1:
                    self.stdout.write(self.style.WARNING(f"Multiple potential full names found for '{db_student.name}'. Not updating to avoid ambiguity."))
                else:
                    self.stdout.write(self.style.WARNING(f"No matching full name found in JSON for '{db_student.name}'. Not updating."))

        self.stdout.write(self.style.SUCCESS("Finished pre-processing student names."))
        
        instrumento_agrupaciones_path = 'base_de_datos_json/Instrumento_Agrupaciones/'
        
        # 1. Get list of all ASIGNACIONES_*.json files
        json_files = glob.glob(os.path.join(instrumento_agrupaciones_path, 'ASIGNACIONES_*.json'))
        
        if not json_files:
            raise CommandError(f"No JSON files found in {instrumento_agrupaciones_path}")

        self.stdout.write(self.style.SUCCESS(f'Found {len(json_files)} instrument JSON files.'))

        with transaction.atomic():
            for json_file_path in json_files:
                file_name = os.path.basename(json_file_path)
                # Extract instrument name from file name, e.g., "ASIGNACIONES_clarinete.json" -> "clarinete"
                instrument_name = file_name.replace('ASIGNACIONES_', '').replace('.json', '').replace('_', ' ').strip().title()

                self.stdout.write(self.style.NOTICE(f'\nProcessing file: {file_name} (Instrumento: {instrument_name})'))

                try:
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        instrument_data = json.load(f)
                    self.stdout.write(self.style.SUCCESS(f'Successfully loaded {file_name}'))
                except FileNotFoundError:
                    self.stdout.write(self.style.ERROR(f'File not found: {json_file_path}. Skipping.'))
                    continue
                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f'Error decoding JSON from {json_file_path}. Skipping.'))
                    continue
                
                if not instrument_data:
                    self.stdout.write(self.style.WARNING(f'JSON file {file_name} is empty. Skipping.'))
                    continue

                # Get/Create the Subject for this instrument
                instrumento_subject, created = Subject.objects.get_or_create(
                    name=instrument_name,
                    defaults={'tipo_materia': 'INSTRUMENTO', 'description': f'Materia de instrumento: {instrument_name}'}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Subject: {instrumento_subject.name} (tipo: {instrumento_subject.tipo_materia})'))
                else:
                    if instrumento_subject.tipo_materia != 'INSTRUMENTO':
                        instrumento_subject.tipo_materia = 'INSTRUMENTO'
                        instrumento_subject.save()
                        self.stdout.write(self.style.WARNING(f'Updated Subject: {instrumento_subject.name} to tipo_materia: INSTRUMENTO'))
                    self.stdout.write(self.style.NOTICE(f'Found existing Subject: {instrumento_subject.name}'))

                # Process each entry in the instrument JSON data
                for entry in instrument_data:
                    fields = entry.get('fields', {})
                    student_full_name = fields.get('full_name')
                    teacher_full_name = fields.get('docente_nombre')
                    clase_name_in_json = fields.get('clase') # Should be the same as instrument_name

                    if not student_full_name or not teacher_full_name:
                        self.stdout.write(self.style.WARNING(f"Skipping entry in {file_name} due to missing student or teacher name: {entry}"))
                        continue

                    # Find Teacher
                    teacher = None
                    normalized_teacher_full_name = normalize_name(teacher_full_name)
                    
                    if normalized_teacher_full_name in KNOWN_NON_TEACHER_NAMES:
                        self.stdout.write(self.style.WARNING(f"Skipping entry for non-teacher name '{teacher_full_name}' in {file_name}."))
                        continue
                    
                    if not normalized_teacher_full_name:
                        self.stdout.write(self.style.WARNING(f"Skipping entry in {file_name} due to invalid teacher name: '{teacher_full_name}'"))
                        continue

                    try:
                        # Attempt to find by exact match first, then by icontains
                        teachers = Teacher.objects.filter(usuario__nombre__iexact=teacher_full_name)
                        if not teachers.exists():
                            teachers = Teacher.objects.filter(usuario__nombre__icontains=normalized_teacher_full_name)
                        
                        if teachers.count() == 1:
                            teacher = teachers.first()
                        elif teachers.count() > 1:
                            self.stdout.write(self.style.ERROR(f"Multiple teachers found for flexible search '{normalized_teacher_full_name}' (original: '{teacher_full_name}'). Skipping assignment."))
                            continue
                        else:
                            self.stdout.write(self.style.ERROR(f"Teacher matching '{normalized_teacher_full_name}' (original: '{teacher_full_name}') not found. Skipping assignment."))
                            continue

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error finding teacher '{teacher_full_name}': {e}. Skipping assignment."))
                        continue

                    # Assign Instrumento Subject to Teacher (M2M)
                    if teacher and instrumento_subject not in teacher.subjects.all():
                        teacher.subjects.add(instrumento_subject)
                        self.stdout.write(self.style.SUCCESS(f"Assigned Subject '{instrumento_subject.name}' to Teacher '{teacher.full_name}'."))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Subject '{instrumento_subject.name}' already assigned to Teacher '{teacher.full_name}'."))

                    # Find Student
                    student = None
                    normalized_student_full_name = normalize_name(student_full_name)
                    if not normalized_student_full_name:
                        self.stdout.write(self.style.WARNING(f"Skipping entry in {file_name} due to invalid student name: '{student_full_name}'"))
                        continue

                    try:
                        students = Student.objects.filter(usuario__nombre__iexact=student_full_name)
                        if not students.exists():
                             students = Student.objects.filter(usuario__nombre__icontains=normalized_student_full_name)

                        if students.count() == 1:
                            student = students.first()
                        elif students.count() > 1:
                            self.stdout.write(self.style.ERROR(f"Multiple students found for flexible search '{normalized_student_full_name}' (original: '{student_full_name}'). Skipping enrollment for instrument '{instrument_name}'."))
                            continue
                        else:
                            self.stdout.write(self.style.ERROR(f"Student matching '{normalized_student_full_name}' (original: '{student_full_name}') not found. Skipping enrollment for instrument '{instrument_name}'."))
                            continue

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error finding student '{student_full_name}': {e}. Skipping enrollment for instrument '{instrument_name}'."))
                        continue

                    # Get/Create Clase for this instrument, teacher, and subject
                    # Clase name could be "Instrumento Name - Teacher Name" or "Instrumento Name - Grade Parallel"
                    # For uniqueness and clarity, let's use "Instrumento Name - Teacher Name" for the Clase name
                    clase_name = f"{instrumento_subject.name} - {teacher.full_name}"
                    
                    instrumento_clase, created = Clase.objects.get_or_create(
                        subject=instrumento_subject,
                        name=clase_name,
                        defaults={
                            'docente_base': teacher.usuario, # Use docente_base
                            'description': f'Clase individual de {instrumento_subject.name} con {teacher.full_name}',
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created Clase: {instrumento_clase.name}'))
                    else:
                        # If existing, ensure docente_base is correct
                        if instrumento_clase.docente_base != teacher.usuario:
                            instrumento_clase.docente_base = teacher.usuario
                            instrumento_clase.save()
                            self.stdout.write(self.style.WARNING(f'Updated Clase {instrumento_clase.name} docente_base to {teacher.full_name}'))
                        self.stdout.write(self.style.NOTICE(f'Found existing Clase: {instrumento_clase.name}'))

                    # Create Enrollment for the student in this Clase
                    enrollment, created = Enrollment.objects.get_or_create(
                        estudiante=student.usuario, # Link to Usuario
                        clase=instrumento_clase,
                        defaults={'estado': 'ACTIVO', 'docente': teacher.usuario} # Set estado and docente
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Enrolled Student '{student.name}' in Clase '{instrumento_clase.name}'."))
                    else:
                        self.stdout.write(self.style.NOTICE(f"Student '{student.name}' already enrolled in Clase '{instrumento_clase.name}'."))

        self.stdout.write(self.style.SUCCESS('Instrumento subject assignment migration completed successfully.'))
