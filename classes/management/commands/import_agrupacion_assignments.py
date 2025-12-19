import json
from django.core.management.base import BaseCommand
from django.db.models import Q
from students.models import Student
from classes.models import Clase, Enrollment
from teachers.models import Teacher
from subjects.models import Subject # Import Subject to filter by tipo_materia

class Command(BaseCommand):
    help = 'Imports student group assignments from a JSON file and creates enrollments.'

    def add_arguments(self, parser):
        parser.add_argument('agrupacion_assignments_json_file', type=str, 
                            help='The path to the JSON file with student group assignments (ASIGNACIONES_agrupaciones.json).')
        parser.add_argument('teacher_assignments_json_file', type=str, 
                            help='The path to the JSON file with teacher group assignments (asignaciones_docentes.json).')

    def handle(self, *args, **options):
        agrupacion_assignments_json_file = options['agrupacion_assignments_json_file']
        teacher_assignments_json_file = options['teacher_assignments_json_file']
        
        self.stdout.write(self.style.SUCCESS(f'Starting import of group assignments...'))

        # --- 1. Load Teacher Assignments (asignaciones_docentes.json) ---
        agrupacion_to_teacher_map = {}
        try:
            with open(teacher_assignments_json_file, 'r', encoding='utf-8') as f:
                teacher_assignments = json.load(f)
            for entry in teacher_assignments:
                agrupacion_name = entry.get('agrupacion', '').strip()
                docente_asignado = entry.get('docente_asignado', '').strip()
                if agrupacion_name and docente_asignado:
                    agrupacion_to_teacher_map[agrupacion_name] = docente_asignado
            self.stdout.write(self.style.SUCCESS(f'Loaded {len(agrupacion_to_teacher_map)} teacher assignments.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Error: Teacher assignments JSON file not found at {teacher_assignments_json_file}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Error: Could not decode JSON from {teacher_assignments_json_file}'))
            return

        # --- 2. Load Student Group Assignments (ASIGNACIONES_agrupaciones.json) ---
        student_assignments = []
        try:
            with open(agrupacion_assignments_json_file, 'r', encoding='utf-8') as f:
                student_assignments = json.load(f)
            self.stdout.write(self.style.SUCCESS(f'Loaded {len(student_assignments)} student group assignments.'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Error: Student group assignments JSON file not found at {agrupacion_assignments_json_file}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Error: Could not decode JSON from {agrupacion_assignments_json_file}'))
            return

        processed_count = 0
        enrolled_count = 0
        skipped_count = 0

        # --- 3. Process each student assignment entry ---
        for entry in student_assignments:
            # Skip header/template rows
            if entry.get('numero') == 'No':
                skipped_count += 1
                continue

            full_name_json = entry.get('nombre_completo', '').strip()
            apellidos_json = entry.get('apellidos', '').strip()
            nombres_json = entry.get('nombres', '').strip()
            agrupacion_name_json = entry.get('agrupacion', '').strip()

            if not full_name_json or not agrupacion_name_json:
                self.stdout.write(self.style.WARNING(f"Skipping entry due to missing student name or agrupacion: {entry}"))
                skipped_count += 1
                continue

            # 3a. Find the Student (more robust matching)
            student = None
            potential_students = []
            
            # Helper function to clean student names from DB (removing grade suffix)
            def clean_db_student_name(s_name):
                return s_name.rsplit(' - ', 1)[0].strip().lower()

            # Cleaned name from JSON
            json_apellidos_lower = apellidos_json.lower()
            json_nombres_lower = nombres_json.lower()
            
            all_students_in_db = Student.objects.all()

            # Step 1: Filter by last names
            students_by_lastname = []
            for s in all_students_in_db:
                s_name_clean = clean_db_student_name(s.name)
                # Check if JSON apellidos are present in cleaned DB name
                if json_apellidos_lower in s_name_clean:
                    students_by_lastname.append(s)
            
            if not students_by_lastname:
                self.stdout.write(self.style.WARNING(f"Skipping student '{full_name_json}': No student found with matching last name."))
                skipped_count += 1
                continue

            # Step 2: Refine by first names
            students_by_fullname_match = []
            for s in students_by_lastname:
                s_name_clean = clean_db_student_name(s.name)
                # Check if JSON nombres are present in cleaned DB name
                if json_nombres_lower in s_name_clean:
                    students_by_fullname_match.append(s)
            
            if len(students_by_fullname_match) == 1:
                student = students_by_fullname_match[0]
            elif len(students_by_fullname_match) > 1:
                # Step 3: Disambiguate by grade
                ano_de_estudio_json = entry.get('ano_de_estudio', '').strip().lower()
                disambiguated_students = []

                for s in students_by_fullname_match:
                    # Clean and normalize JSON grade for comparison
                    json_grade_clean = ano_de_estudio_json
                    if '(' in json_grade_clean and ')' in json_grade_clean:
                        json_grade_clean = json_grade_clean[json_grade_clean.find('(') + 1:json_grade_clean.find(')')].strip()
                    json_grade_clean = json_grade_clean.replace('o', '').replace(' ', '')
                    
                    s_grade_clean = s.grade.lower().replace(' ', '')
                    
                    if json_grade_clean in s_grade_clean or s_grade_clean in json_grade_clean:
                        disambiguated_students.append(s)
                
                if len(disambiguated_students) == 1:
                    student = disambiguated_students[0]
                else:
                    self.stdout.write(self.style.WARNING(f"Skipping student '{full_name_json}' (Grade: {ano_de_estudio_json}): Multiple students found after all matching attempts. Please resolve manually."))
                    skipped_count += 1
                    continue
            else:
                self.stdout.write(self.style.WARNING(f"Skipping student '{full_name_json}': Student not found with matching first and last name parts."))
                skipped_count += 1
                continue
            
            # 3b. Find the assigned Teacher for this agrupacion
            teacher = None
            teacher_full_name = agrupacion_to_teacher_map.get(agrupacion_name_json)
            if teacher_full_name:
                teachers_found = Teacher.objects.filter(full_name__icontains=teacher_full_name) # Using icontains for flexibility
                if teachers_found.count() == 1:
                    teacher = teachers_found.first()
                elif teachers_found.count() > 1:
                    self.stdout.write(self.style.WARNING(f"Skipping agrupacion '{agrupacion_name_json}': Multiple teachers found for '{teacher_full_name}'. Please resolve manually."))
                    skipped_count += 1
                    continue
                else:
                    self.stdout.write(self.style.WARNING(f"Skipping agrupacion '{agrupacion_name_json}': Teacher '{teacher_full_name}' not found for agrupacion."))
                    skipped_count += 1
                    continue
            else:
                self.stdout.write(self.style.WARNING(f"Skipping '{agrupacion_name_json}': No teacher assigned in 'asignaciones_docentes.json' for this agrupacion."))
                skipped_count += 1
                continue

            # 3c. Find the Clase (agrupacion)
            clase = None
            classes_found = Clase.objects.filter(
                name__iexact=agrupacion_name_json, # Try exact match first
                teacher=teacher,
                subject__tipo_materia__iexact='AGRUPACION' # More flexible matching
            )

            if classes_found.count() == 1:
                clase = classes_found.first()
            elif classes_found.count() > 1:
                # Fallback to icontains if exact match fails
                classes_found = Clase.objects.filter(
                    name__icontains=agrupacion_name_json, # More flexible matching for class name
                    teacher=teacher,
                    subject__tipo_materia__iexact='AGRUPACION'
                )
                if classes_found.count() == 1:
                    clase = classes_found.first()
                else: # Still multiple or no match after icontains
                    self.stdout.write(self.style.WARNING(f"Skipping enrollment for '{full_name_json}' in '{agrupacion_name_json}': Multiple classes found with exact/similar name, teacher, and type 'AGRUPACION'. Please resolve manually."))
                    skipped_count += 1
                    continue
            else:
                self.stdout.write(self.style.WARNING(f"Skipping enrollment for '{full_name_json}' in '{agrupacion_name_json}': Class not found with matching name, teacher, and type 'AGRUPACION'."))
                skipped_count += 1
                continue

            # 3d. Create Enrollment
            if student and clase:
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    clase=clase
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Successfully enrolled '{student.name}' in '{clase.name}' taught by '{teacher.full_name}'"))
                    enrolled_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"'{student.name}' is already enrolled in '{clase.name}' (skipped)"))
            processed_count += 1

        self.stdout.write(self.style.SUCCESS('--- Import Summary ---'))
        self.stdout.write(self.style.SUCCESS(f'Total assignments processed: {len(student_assignments)}'))
        self.stdout.write(self.style.SUCCESS(f'New enrollments created: {enrolled_count}'))
        self.stdout.write(self.style.WARNING(f'Entries skipped (due to errors or existing data): {skipped_count}'))
        self.stdout.write(self.style.SUCCESS('Import finished.'))