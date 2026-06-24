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

# Function to clean and normalize teacher names (reused for general name cleaning)
def clean_name(name):
    name = name.strip().replace('.', '')
    name = re.sub(r'^(Mgs|Lic|Dr)\s*', '', name, flags=re.IGNORECASE)
    return name.strip().lower()

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

        len_diff = abs(len(json_name_parts) - len(db_name_parts))
        score -= len_diff * 2
        
        if score > highest_score:
            highest_score = score
            best_match = student
            
    if highest_score > 15: # Tunable threshold
        return best_match
    
    return None

class Command(BaseCommand):
    help = 'Enrolls students into theoretical (agrupacion) classes based on the ASIGNACIONES_agrupaciones.json file.'

    def handle(self, *args, **options):
        json_file_path = 'base_de_datos_json/asignaciones_grupales/ASIGNACIONES_agrupaciones.json'
        log_file_path = 'agrupaciones_enrollment_inconsistencies.log'
        unmatched_students_log_path = 'unmatched_students_agrupaciones.log'

        self.stdout.write(self.style.SUCCESS(f'Starting student enrollment for agrupaciones from {json_file_path}...'))
        inconsistencies = []
        unmatched_students = set()
        enrollment_count = 0
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                agrupaciones_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_file_path}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Could not decode JSON from {json_file_path}'))
            return

        all_students = list(Student.objects.all())

        # Mapping for subject names from agrupaciones JSON to existing Subject names
        subject_mapping = {
            "Banda Sinfónica Edison Chiluisa": "Agrupacion: Orquesta, Banda, Ensamble De Guitarra O Coro",
            "Coro Vespertino": "Coro",
            "Ensamble de Guitarras": "Conjunto Instrumental/Vocal O Mixto",
            "Coro Matutino": "Coro",
            "Orquesta Matutina": "Orquesta Pedagógica",
            # Add other mappings as identified from REPORTE_DOCENTES_HORARIOS_0858.json
        }

        # level_map for parsing grade levels, copied from import_horarios.py
        level_map = {
            r'1o': '1', r'2o': '2', r'3o': '3', r'4o': '4',
            r'5o': '5', r'6o': '6', r'7o': '7', r'8o': '8',
            r'9o \(1o bachillerato\)': '9', r'9o': '9',
            r'10o \(2o bachillerato\)': '10', r'10o': '10',
            r'11o \(3o bachillerato\)': '11', r'11o': '11',
            r'primero': '1', r'segundo': '2', r'tercero': '3', r'cuarto': '4',
            r'quinto': '5', r'sexto': '6', r'septimo': '7', r'séptimo': '7',
            r'octavo': '8', r'noveno': '9', r'décimo': '10', r'decimo': '10', r'onceavo': '11'
        }
        
        with transaction.atomic():
            for entry in agrupaciones_data:
                fields = entry
                
                # Skip header-like entries
                if fields.get('numero') == 'No':
                    continue

                student_full_name = fields.get('nombre_completo', '').strip()
                if not student_full_name or student_full_name.lower() == "apellidos del estudiante nombres del estudiante":
                    continue

                agrupacion_name = fields.get('agrupacion', '').strip()
                ano_de_estudio = fields.get('ano_de_estudio', '').strip()
                paralelo = fields.get('paralelo_senalar_el_mismo_paralelo_en_el_que_estuvieron_el_ano_anterior', '').strip()

                if not (agrupacion_name and ano_de_estudio and paralelo):
                    inconsistencies.append(f"Missing data for entry: {fields}")
                    continue
                
                # Use mapping for subject name
                mapped_subject_name = subject_mapping.get(agrupacion_name, agrupacion_name)

                # --- Find Student ---
                student = find_best_match_student_by_parts(student_full_name, all_students)
                if not student:
                    unmatched_students.add(student_full_name)
                    continue

                # --- Find GradeLevel ---
                level_key = None
                normalized_curso = ano_de_estudio.lower()
                for pattern, key in level_map.items():
                    if re.search(pattern, normalized_curso):
                        level_key = key
                        break
                
                paralelo_clean = paralelo.split('(')[0].strip() # 'B (vespertina)' -> 'B'

                if not (level_key and paralelo_clean):
                    inconsistencies.append(f"Could not determine Grade/Section for student {student_full_name} from ano_de_estudio='{ano_de_estudio}', paralelo='{paralelo}'.")
                    continue
                
                grade_level = GradeLevel.objects.filter(level=level_key, section=paralelo_clean).first()
                if not grade_level:
                    inconsistencies.append(f"GradeLevel not found for {ano_de_estudio} {paralelo_clean} (student: {student_full_name}).")
                    continue

                # --- Find or Create Subject ---
                subject, _ = Subject.objects.get_or_create(name=mapped_subject_name, defaults={'tipo_materia': 'AGRUPACION'})

                # --- Find all relevant Clase objects and enroll student ---
                # A student is enrolled in all classes that match the subject and grade level
                expected_clase_name = f"{subject.name} ({grade_level})"
                matching_clases = Clase.objects.filter(
                    subject=subject,
                    name=expected_clase_name
                )
                
                if not matching_clases.exists():
                    inconsistencies.append(f"No Clase found for subject '{subject.name}' and expected name '{expected_clase_name}' (student: {student_full_name}).")
                    continue
                
                for clase in matching_clases:
                    try:
                        _, created = Enrollment.objects.get_or_create(student=student, clase=clase)
                        if created:
                            enrollment_count += 1
                            self.stdout.write(self.style.SUCCESS(f"ENROLLED {student.name} in {clase.name}"))
                    except Exception as e:
                        inconsistencies.append(f"Error enrolling student {student.name} in class {clase.name}: {e}")

        self.stdout.write(self.style.SUCCESS(f'--- Finished Student Enrollment for Agrupaciones: {enrollment_count} new enrollments ---'))
        
        if unmatched_students:
            with open(unmatched_students_log_path, 'w', encoding='utf-8') as log_file:
                for s_name in sorted(list(unmatched_students)):
                    log_file.write(f"{s_name}\n")
            self.stdout.write(self.style.WARNING(f"Found {len(unmatched_students)} unmatched students. See '{unmatched_students_log_path}' for details."))

        if inconsistencies:
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                for line in inconsistencies:
                    log_file.write(f"{line}\n")
            self.stdout.write(self.style.WARNING(f"\nFound {len(inconsistencies)} inconsistencies. See '{log_file_path}' for details."))
        
        self.stdout.write(self.style.SUCCESS('Agrupaciones student enrollment process finished.'))
