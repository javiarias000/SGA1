import json
import re
import difflib
from django.core.management.base import BaseCommand
from teachers.models import Teacher
from subjects.models import Subject
from classes.models import Clase, GradeLevel
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
        
        # If there are no common parts, it's not a match
        if not common_parts:
            continue
            
        # Calculate a score based on commonality and similarity
        score = len(common_parts) * 10  # Weight common parts higher
        
        # Add similarity scores for non-common parts
        remaining_json_parts = json_name_parts - common_parts
        remaining_db_parts = db_name_parts - common_parts

        # Check for fuzzy matches between remaining parts
        if remaining_json_parts and remaining_db_parts:
            # Pairwise comparison to find best fuzzy matches
            for json_part in remaining_json_parts:
                best_part_ratio = 0
                for db_part in remaining_db_parts:
                    ratio = difflib.SequenceMatcher(None, json_part, db_part).ratio()
                    if ratio > best_part_ratio:
                        best_part_ratio = ratio
                
                if best_part_ratio > 0.7:  # Threshold for fuzzy part match
                    score += best_part_ratio * 5 # Add to score, but less than a direct match

        if score > highest_score:
            highest_score = score
            best_match = teacher
            potential_matches = [teacher]
        elif score == highest_score and score > 0:
            potential_matches.append(teacher)

    # If we have a single best match above a certain score threshold
    if len(potential_matches) == 1 and highest_score > 10: # Threshold for a confident match
        return potential_matches[0], []
    
    return None, potential_matches


class Command(BaseCommand):
    help = 'Assigns schedules to teachers based on the provided JSON file.'

    def handle(self, *args, **options):
        json_path = 'base_de_datos_json/horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json'
        log_file_path = 'horarios_inconsistencies.log'
        unmatched_teachers_log_path = 'unmatched_teachers.log'

        self.stdout.write(self.style.SUCCESS(f'Starting schedule import from {json_path}...'))
        inconsistencies = []
        unmatched_teachers = set()
        
        try:
            with open(json_path, 'r') as f:
                horarios_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Could not decode JSON from {json_path}'))
            return

        all_teachers = list(Teacher.objects.all())

        with transaction.atomic():
            for entry in horarios_data:
                fields = entry.get('fields', {})
                
                subject_name = fields.get('clase', 'Sin Asignatura').strip()
                dia = fields.get('dia', '').upper()
                
                # Common data for the class
                curso = fields.get('curso', '').strip()
                paralelo = fields.get('paralelo', '').strip()
                grade_level = None
                level_key = None
                normalized_curso = curso.lower()
                
                level_map = {
                    r'decimo primer año \(3o bachillerato\)': '11',
                    r'decimo año \(2o bachillerato\)': '10',
                    'primero': '1', 'segundo': '2', 'tercero': '3', 'cuarto': '4',
                    'quinto': '5', 'sexto': '6', 'septimo': '7', 'séptimo': '7',
                    'octavo': '8', 'noveno': '9', 'décimo': '10', 'decimo': '10'
                }

                for pattern, key in level_map.items():
                    if re.search(pattern, normalized_curso):
                        level_key = key
                        break
                
                if level_key and paralelo:
                    grade_level, _ = GradeLevel.objects.get_or_create(level=level_key, section=paralelo)
                else:
                    msg = f"Could not determine Grade/Section from curso='{curso}', paralelo='{paralelo}' for record pk={entry.get('pk')}. Skipping."
                    self.stdout.write(self.style.WARNING(msg))
                    inconsistencies.append(msg)
                    continue

                # Special handling for "Agrupacion"
                if subject_name == "Agrupacion: Orquesta, Banda, Ensamble De Guitarra O Coro":
                    teacher_names = []
                    if dia in ["MARTES", "JUEVES"]:
                        teacher_names = [
                            "Peralta Aponte Christian Hernán", "Arias Cuenca Jorge Javier", 
                            "Erazo Moreno Carlos Efrén", "Obando Mayorga Byron Geovanny"
                        ]
                    elif dia in ["MIERCOLES", "VIERNES"]:
                        teacher_names = [
                            "Villena Cárdenas Maria Isabel", "Guananga Aizabucha Javier Santiago", 
                            "Larreátegui Feijoó Inés María", "Pérez Toapanta Diego Armando", 
                            "Cumbicos Macas José Luis", "Laura Guamán Christian Daniel", 
                            "Quinapanta Tibán Angel Rodrigo"
                        ]

                    if teacher_names:
                        subject, _ = Subject.objects.get_or_create(name=subject_name)
                        
                        for teacher_name in teacher_names:
                            cleaned_name = clean_teacher_name(teacher_name)
                            teacher, _ = find_best_match_teacher_fuzzy(cleaned_name, all_teachers)
                            if not teacher:
                                teacher, _ = find_best_match_teacher_by_parts(cleaned_name, all_teachers)

                            if not teacher:
                                msg = f"Special Case: Teacher '{teacher_name}' not found for Agrupacion. Skipping."
                                self.stdout.write(self.style.WARNING(msg))
                                inconsistencies.append(msg)
                                unmatched_teachers.add(teacher_name)
                                continue
                            
                            try:
                                clase_name = f"{subject.name} ({grade_level})"
                                schedule = f"{fields.get('dia', '')}: {fields.get('hora', '')}"
                                room = fields.get('aula', '')
                                
                                clase_obj, created = Clase.objects.update_or_create(
                                    teacher=teacher,
                                    subject=subject,
                                    name=clase_name,
                                    schedule=schedule,
                                    defaults={'room': room}
                                )
                                
                                if created:
                                    self.stdout.write(self.style.SUCCESS(f"CREATED Special Clase: {clase_obj}"))

                            except Exception as e:
                                msg = f"Error creating Special Clase for teacher '{teacher.full_name}': {e}"
                                self.stdout.write(self.style.ERROR(msg))
                                inconsistencies.append(msg)
                        continue # Move to next entry in horarios_data

                # Normal processing for other classes
                raw_teacher_name = fields.get('docente')
                if not raw_teacher_name or raw_teacher_name.upper() == 'ND':
                    msg = f"Skipping record pk={entry.get('pk')}: Teacher name is 'ND' or missing."
                    inconsistencies.append(msg)
                    continue

                cleaned_name = clean_teacher_name(raw_teacher_name)
                
                teacher, _ = find_best_match_teacher_fuzzy(cleaned_name, all_teachers)
                if not teacher:
                    teacher, potential_matches = find_best_match_teacher_by_parts(cleaned_name, all_teachers)

                if not teacher:
                    msg = f"Teacher '{cleaned_name}' (from raw: '{raw_teacher_name}') not found. Skipping."
                    self.stdout.write(self.style.WARNING(msg))
                    inconsistencies.append(msg)
                    unmatched_teachers.add(raw_teacher_name)
                    continue

                if not subject_name:
                    msg = f"Record pk={entry.get('pk')} for teacher {teacher.full_name} has no subject name. Skipping."
                    self.stdout.write(self.style.WARNING(msg))
                    inconsistencies.append(msg)
                    continue
                
                subject, _ = Subject.objects.get_or_create(name=subject_name)

                try:
                    clase_name = f"{subject.name} ({grade_level})"
                    schedule = f"{fields.get('dia', '')}: {fields.get('hora', '')}"
                    room = fields.get('aula', '')
                    
                    clase_obj, created = Clase.objects.update_or_create(
                        teacher=teacher,
                        subject=subject,
                        name=clase_name,
                        schedule=schedule,
                        defaults={'room': room}
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"CREATED Clase: {clase_obj}"))

                except Exception as e:
                    msg = f"Error creating or updating Clase for teacher '{teacher.full_name}': {e}"
                    self.stdout.write(self.style.ERROR(msg))
                    inconsistencies.append(msg)

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
        
        self.stdout.write(self.style.SUCCESS('Schedule import process finished.'))
