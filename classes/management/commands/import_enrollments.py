import json
import os
import re
from django.core.management.base import BaseCommand
from students.models import Student
from classes.models import Clase, Enrollment
from teachers.models import Teacher
from subjects.models import Subject
from .normalization import similarity_ratio, normalize_name

# Helper function to convert JSON grade and section to a comparable format
def convert_grade_and_section(grade_json, section_json):
    grade_conversion = {
        '1o': 'Primero', '2o': 'Segundo', '3o': 'Tercero', '4o': 'Cuarto', '5o': 'Quinto',
        '6o': 'Sexto', '7o': 'Septimo', '8o': 'Octavo', '9o': 'Noveno', 
        '10o': 'Decimo', '10o (2o Bachillerato)': 'Decimo',
        '11o': 'Decimo Primer', '11o (3o Bachillerato)': 'Decimo Primer',
        '12o': 'Decimo Segundo',
        'Primero': 'Primero', 'Segundo': 'Segundo', 'Tercero': 'Tercero', 'Cuarto': 'Cuarto', 'Quinto': 'Quinto',
        'Sexto': 'Sexto', 'Septimo': 'Septimo', 'Octavo': 'Octavo', 'Noveno': 'Noveno', 'Decimo': 'Decimo',
        'Decimo Primer': 'Decimo Primer', 'Decimo Segundo': 'Decimo Segundo',
        '1o Extraordinario': 'Primero Extraordinario'
    }
    
    # Clean section: remove text in parentheses and standardize
    cleaned_section = re.sub(r'\s*\(.*?\)\s*', '', section_json).strip()
    
    # Convert grade
    converted_grade = grade_conversion.get(grade_json.strip(), grade_json.strip())

    return normalize_name(f"{converted_grade} {cleaned_section}")

class Command(BaseCommand):
    help = 'Imports student enrollments from JSON files.'

    def handle(self, *args, **options):
        # Optional: Clear all previous enrollments
        # Enrollment.objects.all().delete()
        # self.stdout.write(self.style.SUCCESS('Previous enrollments deleted.'))

        json_folder = 'base_de_datos_json/Instrumento_Agrupaciones/'
        
        students_in_db = list(Student.objects.all())
        teachers_in_db = list(Teacher.objects.all())
        subjects_in_db = list(Subject.objects.all())
        classes_in_db = list(Clase.objects.all())

        enrollment_count = 0
        
        # Mapping for JSON subject names to DB subject names
        subject_name_mapping = {
            'Acompañamiento': 'Acompañamiento',
            'Clarinete': 'Clarinete',
            'Complementario': 'Complementario',
            'Conj. Inst': 'Conj. Inst',
            'Contrabajo': 'Contrabajo',
            'Flauta Traversa': 'Flauta Traversa',
            'Guitarra': 'Guitarra',
            'Percusión': 'Percusión',
            'Piano': 'Piano',
            'Saxofón': 'Saxofón',
            'Saxofon': 'Saxofón', # Handle typo in JSON
            'Trombón': 'Trombón',
            'Trompeta': 'Trompeta',
            'Viola': 'Viola',
            'Violonchelo': 'Violonchelo',
            'Violín': 'Violín',
            # "Instrumento Que Estudia En El Conservatorio Bolívar" should be ignored as per user
        }


        for filename in os.listdir(json_folder):
            if filename.startswith('ASIGNACIONES_') and filename.endswith('.json'):
                # Ignore the template file
                if filename == 'ASIGNACIONES_instrumento_que_estudia_en_el_conservatorio_bolívar.json':
                    self.stdout.write(self.style.NOTICE(f"Skipping template file: {filename}"))
                    continue

                file_path = os.path.join(json_folder, filename)
                
                with open(file_path, 'r') as f:
                    data = json.load(f)

                self.stdout.write(self.style.SUCCESS(f'Processing file: {filename}'))

                for entry in data:
                    fields = entry.get('fields', {})
                    if not fields:
                        continue

                    student_full_name = fields.get('full_name')
                    if not student_full_name or student_full_name == 'Apellidos Del Estudiante Nombres Del Estudiante':
                        continue
                        
                    # 1. Find Student
                    normalized_student_name = normalize_name(student_full_name)
                    
                    best_match_student = None
                    highest_ratio = 0.0
                    
                    for student in students_in_db:
                        normalized_db_name = normalize_name(student.name)
                        ratio = similarity_ratio(normalized_student_name, normalized_db_name)
                        if ratio > highest_ratio:
                            highest_ratio = ratio
                            best_match_student = student
                    
                    if not best_match_student or highest_ratio < 0.65: # Lowered threshold
                        self.stdout.write(self.style.WARNING(f"Could not find a unique student for: '{student_full_name}' (best match: {best_match_student.name if best_match_student else 'None'}, ratio: {highest_ratio:.2f})"))
                        continue
                    
                    student = best_match_student

                    # 2. Find Teacher
                    teacher_name = fields.get('docente_nombre')
                    if not teacher_name:
                        self.stdout.write(self.style.WARNING(f"No teacher name found for student '{student_full_name}' in file {filename}"))
                        continue
                    
                    normalized_teacher_name = normalize_name(teacher_name)
                    
                    best_match_teacher = None
                    highest_ratio = 0.0

                    for teacher in teachers_in_db:
                        normalized_db_name = normalize_name(teacher.full_name)
                        ratio = similarity_ratio(normalized_teacher_name, normalized_db_name)
                        if ratio > highest_ratio:
                            highest_ratio = ratio
                            best_match_teacher = teacher

                    if not best_match_teacher or highest_ratio < 0.7:
                        self.stdout.write(self.style.WARNING(f"Could not find a unique teacher for: '{teacher_name}' (best match: {best_match_teacher.full_name if best_match_teacher else 'None'}, ratio: {highest_ratio:.2f})"))
                        continue
                        
                    teacher = best_match_teacher

                    # 3. Find Subject
                    json_subject_name = fields.get('clase')
                    if not json_subject_name:
                        self.stdout.write(self.style.WARNING(f"No subject name found for student '{student_full_name}' in file {filename}"))
                        continue
                    
                    db_subject_name = subject_name_mapping.get(json_subject_name, json_subject_name)
                    
                    try:
                        subject = Subject.objects.get(name=db_subject_name)
                    except Subject.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Subject '{db_subject_name}' not found in DB (from JSON: '{json_subject_name}'). Skipping student '{student.name}'"))
                        continue

                    # 4. Find Class - now multiple classes are possible
                    grade_json = fields.get('grado')
                    section_json = fields.get('paralelo')

                    if not grade_json or not section_json:
                        self.stdout.write(self.style.WARNING(f"Incomplete grade/section for student '{student_full_name}' in file {filename}. Skipping."))
                        continue
                        
                    normalized_grade_section_json = convert_grade_and_section(grade_json, section_json)

                    # Find all classes that match the teacher and subject
                    potential_classes = [c for c in classes_in_db if c.teacher == teacher and c.subject == subject]
                    
                    matched_classes_for_student = []
                    
                    self.stdout.write(self.style.NOTICE(f"\n--- Debugging Class Matching for Student: '{student.name}' ---"))
                    self.stdout.write(self.style.NOTICE(f"  JSON Grade/Section: '{grade_json} {section_json}'"))
                    self.stdout.write(self.style.NOTICE(f"  Normalized JSON Grade/Section: '{normalized_grade_section_json}'"))
                    self.stdout.write(self.style.NOTICE(f"  Teacher: '{teacher.full_name}', Subject: '{subject.name}'"))
                    self.stdout.write(self.style.NOTICE(f"  Potential Classes ({len(potential_classes)}): {[c.name for c in potential_classes]}"))


                    for clase_obj in potential_classes:
                        normalized_clase_name = normalize_name(clase_obj.name)
                        normalized_clase_name_parts = normalized_clase_name.split(' - ')
                        
                        class_grade_section_part = ""
                        if len(normalized_clase_name_parts) > 1:
                            class_grade_section_part = normalized_clase_name_parts[1]
                        else:
                            # If class name is not in expected format, try matching entire name
                            class_grade_section_part = normalized_clase_name
                            
                        # Fuzzy match the parsed JSON grade/section against the class's grade/section part
                        ratio = similarity_ratio(normalized_grade_section_json, class_grade_section_part)
                        
                        self.stdout.write(self.style.NOTICE(f"    - Clase DB: '{clase_obj.name}' (Normalized: '{normalized_clase_name}')"))
                        self.stdout.write(self.style.NOTICE(f"      Comparing against: '{class_grade_section_part}'"))
                        self.stdout.write(self.style.NOTICE(f"      Ratio: {ratio:.2f}"))

                        # Use a reasonable threshold for class matching
                        if ratio > 0.6: # Lowered threshold due to potential variations in grade/section naming
                            matched_classes_for_student.append((clase_obj, ratio))
                    
                    if not matched_classes_for_student:
                        self.stdout.write(self.style.WARNING(f"  Could not find any suitable class for student '{student.name}' with subject '{subject.name}', teacher '{teacher.full_name}', grade '{grade_json}', section '{section_json}'"))
                        continue
                        
                    # Sort by ratio to get the best match first
                    matched_classes_for_student.sort(key=lambda x: x[1], reverse=True)
                    best_match_clase, best_match_ratio = matched_classes_for_student[0]

                    # Check for multiple equally good matches at the top ratio
                    if len(matched_classes_for_student) > 1 and matched_classes_for_student[0][1] == matched_classes_for_student[1][1]:
                         self.stdout.write(self.style.WARNING(f"Multiple equally good classes found for '{subject.name} - {grade_json} {section_json}' (best ratio: {best_match_ratio:.2f}). Skipping enrollment for student '{student.name}'"))
                         continue
                        
                    # 5. Create Enrollment
                    enrollment, created = Enrollment.objects.get_or_create(
                        student=student,
                        clase=best_match_clase
                    )
                    if created:
                        enrollment_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Enrolled '{student.name}' in '{best_match_clase.name}'"))
                    else:
                        self.stdout.write(self.style.NOTICE(f"'{student.name}' was already enrolled in '{best_match_clase.name}'"))

        self.stdout.write(self.style.SUCCESS(f'\nFinished processing enrollments. Total enrollments created/found: {enrollment_count}'))
