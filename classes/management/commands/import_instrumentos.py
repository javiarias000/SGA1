import json
import re
import difflib
import os
from django.core.management.base import BaseCommand
from teachers.models import Teacher
from subjects.models import Subject
from students.models import Student
from classes.models import Clase, GradeLevel, Enrollment
from django.db import transaction

# Function to clean and normalize teacher names
def clean_teacher_name(name):
    name = name.strip().replace('.', '')
    name = re.sub(r'^(Mgs|Lic|Dr)\s*', '', name, flags=re.IGNORECASE)
    return name.strip().lower()

def find_best_match_teacher_fuzzy(cleaned_name_from_json, all_teachers, threshold=0.6):
    """
    Finds the best matching teacher using fuzzy string matching.
    """
    best_match = None
    highest_ratio = 0
    
    for teacher in all_teachers:
        db_name = teacher.full_name.lower()
        ratio = difflib.SequenceMatcher(None, cleaned_name_from_json, db_name).ratio()
        
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = teacher
            
    if highest_ratio >= threshold:
        return best_match, []
    
    return None, []

def find_best_match_teacher_by_parts(cleaned_name_from_json, all_teachers):
    """
    Finds the best matching teacher using a scoring system based on shared and similar name parts.
    """
    json_name_parts = set([p for p in cleaned_name_from_json.split() if len(p) > 1])
    
    if not json_name_parts:
        return None, []

    best_match = None
    highest_score = 0
    potential_matches = []

    for teacher in all_teachers:
        db_name_parts = set([p for p in teacher.full_name.lower().split() if len(p) > 1])
        
        common_parts = json_name_parts.intersection(db_name_parts)
        
        if not common_parts:
            continue
            
        score = len(common_parts) * 10
        
        remaining_json_parts = json_name_parts - common_parts
        remaining_db_parts = db_name_parts - common_parts

        if remaining_json_parts and remaining_db_parts:
            for json_part in remaining_json_parts:
                best_part_ratio = 0
                for db_part in remaining_db_parts:
                    ratio = difflib.SequenceMatcher(None, json_part, db_part).ratio()
                    if ratio > best_part_ratio:
                        best_part_ratio = ratio
                
                if best_part_ratio > 0.7:
                    score += best_part_ratio * 5

        if score > highest_score:
            highest_score = score
            best_match = teacher
            potential_matches = [teacher]
        elif score == highest_score and score > 0:
            potential_matches.append(teacher)

    if len(potential_matches) == 1 and highest_score > 10:
        return potential_matches[0], []
    
    return None, potential_matches

def find_best_match_student_by_parts(json_student_name, all_students):
    """
    Finds the best matching student using a scoring system based on shared and similar name parts.
    """
    json_name_parts = set([p for p in json_student_name.lower().split() if len(p) > 1])
    
    if not json_name_parts:
        return None
    
    best_match = None
    highest_score = 0
    
    for student in all_students:
        db_name_parts = set([p for p in student.name.lower().split() if len(p) > 1])
        
        common_parts = json_name_parts.intersection(db_name_parts)
        
        if not common_parts:
            continue
            
        score = len(common_parts) * 10
        
        remaining_json_parts = json_name_parts - common_parts
        remaining_db_parts = db_name_parts - common_parts

        if remaining_json_parts and remaining_db_parts:
            for json_part in remaining_json_parts:
                best_part_ratio = 0
                for db_part in remaining_db_parts:
                    ratio = difflib.SequenceMatcher(None, json_part, db_part).ratio()
                    if ratio > best_part_ratio:
                        best_part_ratio = ratio
                
                if best_part_ratio > 0.7:
                    score += best_part_ratio * 5

        # Consider the length difference, penalize large differences
        len_diff = abs(len(json_name_parts) - len(db_name_parts))
        score -= len_diff * 2
        
        if score > highest_score:
            highest_score = score
            best_match = student
            
    # Require a minimum score for a confident match
    if highest_score > 15: # Tunable threshold
        return best_match
    
    return None

class Command(BaseCommand):
    help = 'Assigns instrument classes to teachers and enrolls students based on the JSON files in Instrumento_Agrupaciones.'

    def handle(self, *args, **options):
        json_folder_path = 'base_de_datos_json/Instrumento_Agrupaciones/'
        log_file_path = 'instrumentos_inconsistencies.log'
        unmatched_teachers_log_path = 'unmatched_teachers_instrumentos.log'
        unmatched_students_log_path = 'unmatched_students_instrumentos.log'

        self.stdout.write(self.style.SUCCESS(f'Starting instrument class import from {json_folder_path}...'))
        inconsistencies = []
        unmatched_teachers = set()
        
        # Set to store unique classes to avoid duplicates
        unique_classes = set()

        # Get all JSON files in the directory
        try:
            json_files = [f for f in os.listdir(json_folder_path) if f.startswith('ASIGNACIONES_') and f.endswith('.json')]
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Directory not found: {json_folder_path}'))
            return

        all_teachers = list(Teacher.objects.all())
        all_students = list(Student.objects.all())

        invalid_teacher_names = {'piano', 'maestro de instrumento', 'rendí prueba de ubicación no tengo maestro asignado', 'nulo', 'violín'}
        for json_file in json_files:
            json_path = os.path.join(json_folder_path, json_file)
            try:
                with open(json_path, 'r') as f:
                    instrumento_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                inconsistencies.append(f"Could not read or decode {json_file}: {e}")
                continue

            for entry in instrumento_data:
                fields = entry.get('fields', {})
                
                raw_teacher_name = fields.get('docente_nombre')
                if not raw_teacher_name or raw_teacher_name.upper() == 'ND' or raw_teacher_name.lower() in invalid_teacher_names:
                    continue

                subject_name = fields.get('clase', 'Sin Asignatura').strip()
                grado = fields.get('grado', '').strip()
                paralelo = fields.get('paralelo', '').strip()
                
                cleaned_teacher_name = clean_teacher_name(raw_teacher_name)

                # Use a tuple to identify a unique class
                class_key = (cleaned_teacher_name, subject_name, grado, paralelo)
                unique_classes.add(class_key)

        with transaction.atomic():
            for cleaned_teacher_name, subject_name, grado, paralelo in unique_classes:
                
                teacher, _ = find_best_match_teacher_fuzzy(cleaned_teacher_name, all_teachers)
                if not teacher:
                    teacher, _ = find_best_match_teacher_by_parts(cleaned_teacher_name, all_teachers)

                if not teacher:
                    msg = f"Teacher '{cleaned_teacher_name}' not found in database. Skipping class creation."
                    inconsistencies.append(msg)
                    unmatched_teachers.add(cleaned_teacher_name)
                    continue

                subject, _ = Subject.objects.get_or_create(name=subject_name, defaults={'tipo_materia': 'INSTRUMENTO'})

                level_key = None
                normalized_curso = grado.lower()
                
                level_map = {
                    r'11o \(3o bachillerato\)': '11',
                    r'10o \(2o bachillerato\)': '10',
                    r'9o \(1o bachillerato\)': '9',
                    '1o': '1', '2o': '2', '3o': '3', '4o': '4',
                    '5o': '5', '6o': '6', '7o': '7',
                    '8o': '8', '9o': '9', '10o': '10', '11o': '11'
                }

                for pattern, key in level_map.items():
                    if re.search(pattern, normalized_curso):
                        level_key = key
                        break
                
                # Clean up paralelo
                paralelo_clean = paralelo.split('(')[0].strip()

                if level_key and paralelo_clean:
                    grade_level, _ = GradeLevel.objects.get_or_create(level=level_key, section=paralelo_clean)
                else:
                    msg = f"Could not determine Grade/Section from grado='{grado}', paralelo='{paralelo}'. Skipping."
                    inconsistencies.append(msg)
                    continue

                try:
                    clase_name = f"{subject.name} - {grade_level}"
                    
                    clase_obj, created = Clase.objects.update_or_create(
                        teacher=teacher,
                        subject=subject,
                        name=clase_name,
                        defaults={'schedule': 'Por definir', 'room': 'Por definir'}
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"CREATED Instrumento Clase: {clase_obj}"))

                except Exception as e:
                    msg = f"Error creating or updating Clase for teacher '{teacher.full_name}' and subject '{subject.name}': {e}"
                    inconsistencies.append(msg)

        # --- Student Enrollment ---
        self.stdout.write(self.style.SUCCESS('--- Starting Student Enrollment ---'))
        enrollment_count = 0
        unmatched_students = set()

        for json_file in json_files:
            json_path = os.path.join(json_folder_path, json_file)
            try:
                with open(json_path, 'r') as f:
                    instrumento_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                continue

            for entry in instrumento_data:
                fields = entry.get('fields', {})
                
                student_name = fields.get('full_name', '').strip()
                if not student_name:
                    continue

                student = find_best_match_student_by_parts(student_name, all_students)
                if not student:
                    unmatched_students.add(student_name)
                    self.stdout.write(self.style.WARNING(f"Student '{student_name}' not found in database. Skipping enrollment."))
                    continue

                # Find class
                raw_teacher_name = fields.get('docente_nombre')
                if not raw_teacher_name or raw_teacher_name.upper() == 'ND' or raw_teacher_name.lower() in invalid_teacher_names:
                    continue

                subject_name = fields.get('clase', '').strip()
                grado = fields.get('grado', '').strip()
                paralelo = fields.get('paralelo', '').strip()
                
                cleaned_teacher_name = clean_teacher_name(raw_teacher_name)
                
                teacher, _ = find_best_match_teacher_fuzzy(cleaned_teacher_name, all_teachers)
                if not teacher:
                    teacher, _ = find_best_match_teacher_by_parts(cleaned_teacher_name, all_teachers)
                
                if not teacher:
                    continue
                
                level_key = None
                normalized_curso = grado.lower()
                level_map = {
                    r'11o \(3o bachillerato\)': '11',
                    r'10o \(2o bachillerato\)': '10',
                    r'9o \(1o bachillerato\)': '9',
                    '1o': '1', '2o': '2', '3o': '3', '4o': '4',
                    '5o': '5', '6o': '6', '7o': '7',
                    '8o': '8', '9o': '9', '10o': '10', '11o': '11'
                }

                for pattern, key in level_map.items():
                    if re.search(pattern, normalized_curso):
                        level_key = key
                        break
                
                paralelo_clean = paralelo.split('(')[0].strip()

                if level_key and paralelo_clean:
                    grade_level = GradeLevel.objects.filter(level=level_key, section=paralelo_clean).first()
                else:
                    continue
                
                if not grade_level:
                    continue
                
                clase_name = f"{subject_name} - {grade_level}"

                try:
                    clase = Clase.objects.get(name=clase_name, teacher=teacher, subject__name=subject_name)
                    
                    _, created = Enrollment.objects.get_or_create(student=student, clase=clase)
                    if created:
                        enrollment_count += 1
                except Clase.DoesNotExist:
                    inconsistencies.append(f"Clase not found for enrollment: {clase_name}")
                    continue
        
        self.stdout.write(self.style.SUCCESS(f'--- Finished Student Enrollment: {enrollment_count} new enrollments ---'))
        
        if unmatched_students:
            with open(unmatched_students_log_path, 'w') as log_file:
                for s_name in sorted(list(unmatched_students)):
                    log_file.write(f"{s_name}\n")
            self.stdout.write(self.style.WARNING(f"Found {len(unmatched_students)} unmatched students. See '{unmatched_students_log_path}' for details."))

        if inconsistencies:
            with open(log_file_path, 'w') as log_file:
                for line in inconsistencies:
                    log_file.write(f"{line}\n")
            self.stdout.write(self.style.WARNING(f"\nFound {len(inconsistencies)} inconsistencies. See '{log_file_path}' for details."))

        if unmatched_teachers:
            with open(unmatched_teachers_log_path, 'w') as log_file:
                for teacher_name in sorted(list(unmatched_teachers)):
                    log_file.write(f"{teacher_name}\n")
            self.stdout.write(self.style.WARNING(f"Found {len(unmatched_teachers)} unmatched teachers. See '{unmatched_teachers_log_path}' for details."))
        
        self.stdout.write(self.style.SUCCESS('Instrument class import process finished.'))
