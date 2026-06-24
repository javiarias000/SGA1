import json
import os
import re
from django.core.management.base import BaseCommand
from teachers.models import Teacher
from subjects.models import Subject
from classes.models import Clase
from .normalization import normalize_name, similarity_ratio # Import similarity_ratio as well

# Helper function to convert JSON grade and section to a comparable format
def convert_grade_and_section_for_class_name(grade_json, section_json):
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

    return f"{converted_grade} {cleaned_section}".strip()


class Command(BaseCommand):
    help = 'Assigns classes to teachers from JSON files (horarios_academicos and Instrumento_Agrupaciones).'

    def handle(self, *args, **options):
        # Clear all previous classes
        Clase.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Previous classes deleted.'))

        teachers_in_db = list(Teacher.objects.all())
        created_classes_count = 0
        created_classes_cache = set() # To avoid creating the same class multiple times

        # --- Phase 1: Build generic schedule slots lookup from REPORTE_DOCENTES_HORARIOS_0858.json ---
        self.stdout.write(self.style.SUCCESS('\nBuilding generic schedule slots lookup from horarios_academicos...'))
        horarios_file_path = 'base_de_datos_json/horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json'
        # Key: (normalized_curso_paralelo, normalized_generic_clase_category)
        # Value: List of {'teacher_raw_name', 'dia', 'hora', 'aula', 'original_clase_name'}
        horarios_lookup = {} 

        generic_class_category_mapping = {
            'Instrumento': 'Instrumento', # For specific instrument subjects
            'Agrupacion: Orquesta, Banda, Ensamble De Guitarra O Coro': 'Agrupacion', # For specific agrupacion subjects
            'Conjunto Instrumental/Vocal O Mixto': 'Agrupacion', # For specific agrupacion subjects
            'Coro': 'Agrupacion', # Coro is an agrupacion
            'Orquesta Pedagógica': 'Agrupacion', # Orquesta is an agrupacion
            'Educación Rítmica Audioperceptiva': 'Teoria', # Teoria
            'Lenguaje Musical': 'Teoria', # Teoria
            'Lenguaje Musica': 'Teoria', # Teoria (typo)
            'Piano Complementario': 'Instrumento' # Though it says complementario, it's a specific instrument
            # Add other generic categories from horarios_academicos and map them to a simple category name
        }
        
        # Mapping for JSON subject names to DB subject names (for ASIGNACIONES files)
        specific_subject_name_mapping = {
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
        }


        with open(horarios_file_path, 'r') as f:
            horarios_data = json.load(f)

        for entry in horarios_data:
            fields = entry['fields']
            json_teacher_name_raw = fields['docente'].strip()
            curso_raw = fields['curso'].strip()
            paralelo_raw = fields['paralelo'].strip()
            generic_clase_raw = fields['clase'].strip()

            normalized_curso_paralelo = normalize_name(f"{curso_raw} {paralelo_raw}")
            
            generic_category_name = generic_class_category_mapping.get(generic_clase_raw, normalize_name(generic_clase_raw))
            
            # Key with generic category and grade/section
            horarios_lookup_key = (normalized_curso_paralelo, generic_category_name)
            
            if horarios_lookup_key not in horarios_lookup:
                horarios_lookup[horarios_lookup_key] = []
            
            horarios_lookup[horarios_lookup_key].append({
                'teacher_raw_name': json_teacher_name_raw, # Store raw teacher name for matching later
                'dia': fields['dia'].strip(),
                'hora': fields['hora'].strip(),
                'aula': fields['aula'].strip(),
                'original_clase_name': generic_clase_raw # For potential debugging/context
            })
        
        self.stdout.write(self.style.SUCCESS(f'Finished building generic schedule slots lookup. Found {len(horarios_lookup)} unique generic slots combinations.'))

        # --- Phase 2: Create Specific Clase objects from ASIGNACIONES_*.json files ---
        self.stdout.write(self.style.SUCCESS('\nCreating specific instrument/agrupacion classes from ASIGNACIONES_*.json files...'))
        asignaciones_folder = 'base_de_datos_json/Instrumento_Agrupaciones/'
        
        # Files to ignore during this class creation phase, as per user's instruction
        files_to_ignore = [
            'ASIGNACIONES_acompañamiento.json',
            'ASIGNACIONES_complementario.json',
            'ASIGNACIONES_conj._inst.json',
            'ESTUDIANTES_CON_REPRESENTANTES.json',
            'ASIGNACIONES_instrumento_que_estudia_en_el_conservatorio_bolívar.json' # Template file
        ]
        
        # Map DB subject names to their generic categories for lookup
        # This will allow matching a specific subject (e.g., 'Clarinete') to its category ('Instrumento')
        db_subject_to_generic_category = {}
        for sub in Subject.objects.all():
            if sub.tipo_materia == 'INSTRUMENTO':
                db_subject_to_generic_category[normalize_name(sub.name)] = normalize_name('Instrumento')
            elif sub.tipo_materia == 'AGRUPACION':
                db_subject_to_generic_category[normalize_name(sub.name)] = normalize_name('Agrupacion')
            elif sub.tipo_materia == 'TEORIA':
                db_subject_to_generic_category[normalize_name(sub.name)] = normalize_name('Teoria') # Need to map specific theory subjects in ASIGNACIONES files to generic 'Teoria'

        for filename in os.listdir(asignaciones_folder):
            if filename.startswith('ASIGNACIONES_') and filename.endswith('.json') and filename not in files_to_ignore:
                file_path = os.path.join(asignaciones_folder, filename)
                
                with open(file_path, 'r') as f:
                    data = json.load(f)

                self.stdout.write(self.style.SUCCESS(f'Processing file: {filename} for specific classes.'))

                for entry in data:
                    fields = entry.get('fields', {})
                    if not fields:
                        continue
                    
                    json_teacher_name_raw = fields.get('docente_nombre')
                    if not json_teacher_name_raw or json_teacher_name_raw == 'FALTANTE':
                        self.stdout.write(self.style.WARNING(f"Skipping class creation for an entry in {filename} due to missing docente_nombre."))
                        continue
                    
                    json_subject_name_raw = fields.get('clase')
                    if not json_subject_name_raw or json_subject_name_raw == 'FALTANTE':
                        self.stdout.write(self.style.WARNING(f"Skipping class creation for an entry in {filename} due to missing clase (subject)."))
                        continue
                    
                    grado_raw = fields.get('grado')
                    paralelo_raw = fields.get('paralelo')

                    if not grado_raw or not paralelo_raw:
                        self.stdout.write(self.style.WARNING(f"Skipping class creation for an entry in {filename} due to incomplete grade/paralelo."))
                        continue

                    # --- Find Teacher (fuzzy match) ---
                    cleaned_json_teacher_name = re.sub(r'\b(mgs|dr|lic)\b', '', json_teacher_name_raw, flags=re.IGNORECASE)
                    cleaned_json_teacher_name = re.sub(r'[.\s]+', ' ', cleaned_json_teacher_name).strip().lower()
                    json_name_parts = set(cleaned_json_teacher_name.split(' '))

                    found_teachers = []
                    for teacher_db in teachers_in_db:
                        normalized_db_name = normalize_name(teacher_db.full_name)
                        db_name_parts = set(normalized_db_name.split(' '))
                        if json_name_parts.issubset(db_name_parts):
                            found_teachers.append(teacher_db)
                    
                    # Handle teacher names that are subjects (bad data) by skipping
                    if json_teacher_name_raw in specific_subject_name_mapping.keys():
                        self.stdout.write(self.style.WARNING(f"Skipping class creation for '{json_subject_name_raw} - {grado_raw} {paralelo_raw}' because docente_nombre '{json_teacher_name_raw}' is a subject name. (File: {filename})"))
                        continue

                    if len(found_teachers) != 1:
                        self.stdout.write(self.style.WARNING(f'Skipping class creation for "{json_subject_name_raw} - {grado_raw} {paralelo_raw}" due to teacher matching issue: "{json_teacher_name_raw}" (Found: {len(found_teachers)} teachers). (File: {filename})'))
                        continue
                    teacher = found_teachers[0]
                    
                    # --- Find Subject (exact match using mapping) ---
                    db_specific_subject_name = specific_subject_name_mapping.get(json_subject_name_raw, json_subject_name_raw)
                    try:
                        subject = Subject.objects.get(name=db_specific_subject_name)
                    except Subject.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Subject '{db_specific_subject_name}' not found in DB (from JSON: '{json_subject_name_raw}'). Skipping class creation. (File: {filename})"))
                        continue
                    
                    # --- Find matching schedule slot in horarios_lookup ---
                    normalized_curso_paralelo = normalize_name(f"{grado_raw} {paralelo_raw}")
                    generic_category_for_subject = db_subject_to_generic_category.get(normalize_name(subject.name))

                    if not generic_category_for_subject:
                        self.stdout.write(self.style.WARNING(f"Could not determine generic category for subject '{subject.name}'. Skipping class creation. (File: {filename})"))
                        continue
                    
                    horarios_lookup_key = (normalized_curso_paralelo, generic_category_for_subject)
                    
                    potential_slots = horarios_lookup.get(horarios_lookup_key, [])
                    
                    matching_slots_for_teacher = []
                    for slot in potential_slots:
                        # Match teacher from ASIGNACIONES with teacher in the slot from horarios_academicos
                        slot_teacher_name_raw = slot['teacher_raw_name']
                        
                        cleaned_slot_teacher_name = re.sub(r'\b(mgs|dr|lic)\b', '', slot_teacher_name_raw, flags=re.IGNORECASE)
                        cleaned_slot_teacher_name = re.sub(r'[.\s]+', ' ', cleaned_slot_teacher_name).strip().lower()
                        slot_teacher_name_parts = set(cleaned_slot_teacher_name.split(' '))

                        found_slot_teachers = []
                        for teacher_db in teachers_in_db:
                            normalized_db_name = normalize_name(teacher_db.full_name)
                            db_name_parts = set(normalized_db_name.split(' '))
                            if slot_teacher_name_parts.issubset(db_name_parts):
                                found_slot_teachers.append(teacher_db)

                        if len(found_slot_teachers) == 1 and found_slot_teachers[0].id == teacher.id:
                            matching_slots_for_teacher.append(slot)
                        elif slot_teacher_name_raw == 'ND':
                            # If the horarios_academicos slot has ND for teacher, it means any teacher can use it.
                            # We take the teacher from the ASIGNACIONES file.
                            matching_slots_for_teacher.append(slot)
                            
                    if not matching_slots_for_teacher:
                        self.stdout.write(self.style.WARNING(f"No matching schedule slot found in horarios_academicos for Subject '{subject.name}', Teacher '{teacher.full_name}', Grade '{grado_raw}', Section '{paralelo_raw}', Generic Category '{generic_category_for_subject}'. Skipping class creation. (File: {filename})"))
                        continue
                    
                    if len(matching_slots_for_teacher) > 1:
                        self.stdout.write(self.style.WARNING(f"Multiple matching schedule slots found in horarios_academicos for Subject '{subject.name}', Teacher '{teacher.full_name}', Grade '{grado_raw}', Section '{paralelo_raw}', Generic Category '{generic_category_for_subject}'. Skipping class creation due to ambiguity. (File: {filename})"))
                        continue
                    
                    # Found a unique matching slot
                    slot_details = matching_slots_for_teacher[0]
                    schedule = f"{slot_details['dia']} {slot_details['hora']}"
                    room = slot_details['aula']

                    # --- Create Class ---
                    class_name_for_db = f"{subject.name} - {convert_grade_and_section_for_class_name(grado_raw, paralelo_raw)}"
                    
                    class_identifier = (teacher.id, subject.id, class_name_for_db, schedule, room)

                    if class_identifier not in created_classes_cache:
                        clase, created = Clase.objects.get_or_create(
                            teacher=teacher,
                            subject=subject,
                            name=class_name_for_db,
                            defaults={
                                'schedule': schedule,
                                'room': room,
                                'description': f"Clase de {subject.name} para el {grado_raw} {paralelo_raw}"
                            }
                        )
                        if created:
                            created_classes_count += 1
                            created_classes_cache.add(class_identifier)
                            self.stdout.write(self.style.SUCCESS(f'Created class: "{class_name_for_db}" for teacher "{teacher.full_name}"'))
            
        self.stdout.write(self.style.SUCCESS(f'\nFinished processing all classes. Total unique classes created: {created_classes_count}'))