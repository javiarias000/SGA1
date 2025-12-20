import json
import re
import difflib
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

# IMPORTS ACTUALIZADOS SEGÚN TU NUEVO MODELS.PY
from users.models import Usuario  # Usamos Usuario, no Teacher
from subjects.models import Subject
from students.models import Student
from classes.models import Clase, GradeLevel, Enrollment

# Function to clean and normalize teacher names
def clean_teacher_name(name):
    if not name:
        return ""
    name = name.strip().replace('.', '')
    # Eliminamos títulos comunes
    name = re.sub(r'^(Mgs|Lic|Dr|Prof|Msc)\.?\s*', '', name, flags=re.IGNORECASE)
    return name.strip().lower()

def find_best_match_usuario_fuzzy(cleaned_name_from_json, all_users, threshold=0.6):
    """
    Busca el mejor Usuario (Docente o Estudiante) usando coincidencia difusa.
    """
    best_match = None
    highest_ratio = 0
    
    for user in all_users:
        # Asumiendo que el modelo Usuario tiene un campo 'nombre' o 'full_name'
        # Ajusta 'nombre' si tu campo se llama diferente (ej. first_name + last_name)
        db_name = user.nombre.lower() if hasattr(user, 'nombre') else f"{user.first_name} {user.last_name}".lower()
        
        ratio = difflib.SequenceMatcher(None, cleaned_name_from_json, db_name).ratio()
        
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = user
            
    if highest_ratio >= threshold:
        return best_match
    
    return None

def find_best_match_student_profile(json_student_name, all_students):
    """
    Busca el perfil de estudiante (Student) para obtener su Usuario asociado.
    """
    # Lógica simplificada de fuzzy match para estudiantes
    best_match = None
    highest_ratio = 0
    
    # Limpieza básica del nombre del JSON
    clean_json_name = json_student_name.lower().strip()

    for student in all_students:
        # Student suele tener 'name' o relación con usuario
        if student.usuario:
            db_name = student.usuario.nombre.lower()
        else:
            db_name = student.name.lower() # Fallback

        ratio = difflib.SequenceMatcher(None, clean_json_name, db_name).ratio()
        
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = student
            
    if highest_ratio > 0.75: # Umbral más alto para estudiantes para evitar cruces
        return best_match
    return None


class Command(BaseCommand):
    help = 'Assigns instrument classes to teachers and enrolls students based on JSON files.'

    def handle(self, *args, **options):
        json_folder_path = 'base_de_datos_json/Instrumento_Agrupaciones/'
        
        # Logs
        inconsistencies = []
        unmatched_teachers = set()
        unmatched_students = set()
        
        self.stdout.write(self.style.SUCCESS(f'Starting import from {json_folder_path}...'))

        # 1. Cargar Usuarios Docentes y Perfiles de Estudiantes
        # Filtramos solo usuarios que son docentes para la búsqueda de profesores
        all_docentes = list(Usuario.objects.filter(rol='DOCENTE'))
        all_students = list(Student.objects.select_related('usuario').all())

        unique_classes = set()

        # 2. Leer Archivos JSON
        try:
            json_files = [f for f in os.listdir(json_folder_path) if f.endswith('.json')]
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Directory not found: {json_folder_path}'))
            return

        # Nombres inválidos a ignorar
        invalid_teacher_names = {'piano', 'maestro de instrumento', 'nulo', 'violín', 'nd', 'sin docente'}

        # --- FASE 1: Identificar Clases Únicas ---
        for json_file in json_files:
            json_path = os.path.join(json_folder_path, json_file)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                inconsistencies.append(f"Error reading {json_file}: {e}")
                continue

            for entry in data:
                fields = entry.get('fields', {})
                raw_teacher = fields.get('docente_nombre')
                
                if not raw_teacher or clean_teacher_name(raw_teacher) in invalid_teacher_names:
                    continue

                subject_name = fields.get('clase', 'Sin Asignatura').strip()
                grado = fields.get('grado', '').strip()
                paralelo = fields.get('paralelo', '').strip()
                
                # Tupla única para crear la clase
                unique_classes.add((clean_teacher_name(raw_teacher), subject_name, grado, paralelo))

        # --- FASE 2: Crear Materias y Clases ---
        self.stdout.write(f"Procesando {len(unique_classes)} clases potenciales...")
        
        with transaction.atomic():
            for cleaned_teacher_name, subject_name, grado, paralelo in unique_classes:
                
                # Buscar Docente (Usuario)
                docente_usuario = find_best_match_usuario_fuzzy(cleaned_teacher_name, all_docentes)

                if not docente_usuario:
                    unmatched_teachers.add(cleaned_teacher_name)
                    continue

                # Crear/Obtener Materia (Subject) con tipo INSTRUMENTO
                subject, _ = Subject.objects.get_or_create(
                    name=subject_name, 
                    defaults={'tipo_materia': 'INSTRUMENTO'} # Importante para tu lógica nueva
                )

                # Determinar Nivel (GradeLevel)
                level_key = None
                normalized_curso = grado.lower()
                level_map = {
                    r'11': '11', r'10': '10', r'9': '9', r'8': '8', 
                    r'7': '7', r'6': '6', r'5': '5', r'4': '4', 
                    r'3': '3', r'2': '2', r'1': '1'
                }
                # Lógica simple de mapeo (puedes mantener tu regex compleja si prefieres)
                for key, val in level_map.items():
                    if key in normalized_curso: # Simplificado
                        level_key = val
                        break
                
                paralelo_clean = paralelo.split('(')[0].strip() or "A" # Default A si vacío

                if not level_key:
                    inconsistencies.append(f"No se pudo determinar nivel para {grado}")
                    continue

                grade_level, _ = GradeLevel.objects.get_or_create(level=level_key, section=paralelo_clean)

                # Crear Clase
                # IMPORTANTE: Usamos 'docente_base' según tu nuevo modelo
                clase_name = f"{subject.name} - {docente_usuario.nombre}" # Convención Conservatorio
                
                try:
                    clase_obj, created = Clase.objects.update_or_create(
                        subject=subject,
                        docente_base=docente_usuario, # CAMBIO CLAVE
                        grade_level=grade_level,      # Asignamos el nivel
                        ciclo_lectivo='2025-2026',    # Aseguramos ciclo
                        defaults={
                            'name': clase_name,
                            'active': True
                        }
                    )
                    if created:
                        self.stdout.write(f"Creada Clase: {clase_obj}")
                except Exception as e:
                    inconsistencies.append(f"Error creando clase {clase_name}: {e}")

        # --- FASE 3: Matricular Estudiantes ---
        self.stdout.write(self.style.SUCCESS('--- Iniciando Matriculación de Estudiantes ---'))
        enrollment_count = 0

        for json_file in json_files:
            json_path = os.path.join(json_folder_path, json_file)
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for entry in data:
                fields = entry.get('fields', {})
                student_name = fields.get('full_name', '').strip()
                raw_teacher = fields.get('docente_nombre')
                subject_name = fields.get('clase', '').strip()
                
                if not student_name or not raw_teacher:
                    continue

                # 1. Buscar Estudiante (Student Profile -> Usuario)
                student_profile = find_best_match_student_profile(student_name, all_students)
                
                if not student_profile or not student_profile.usuario:
                    unmatched_students.add(student_name)
                    continue
                
                estudiante_usuario = student_profile.usuario # Obtenemos el USUARIO

                # 2. Buscar Docente (Usuario)
                cleaned_teacher = clean_teacher_name(raw_teacher)
                docente_usuario = find_best_match_usuario_fuzzy(cleaned_teacher, all_docentes)
                
                if not docente_usuario:
                    continue

                # 3. Encontrar la Clase creada anteriormente
                # Filtramos por materia y docente base
                clase_qs = Clase.objects.filter(
                    subject__name=subject_name,
                    docente_base=docente_usuario
                )
                
                if not clase_qs.exists():
                    inconsistencies.append(f"No existe clase para {subject_name} con {docente_usuario}")
                    continue
                
                clase_obj = clase_qs.first()

                # 4. Crear Inscripción (Enrollment)
                try:
                    enrollment, created = Enrollment.objects.get_or_create(
                        estudiante=estudiante_usuario, # CAMBIO: Usamos Usuario
                        clase=clase_obj,
                        defaults={
                            'docente': docente_usuario,    # CAMBIO: Obligatorio para instrumento
                            'tipo_materia': 'INSTRUMENTO', # CAMBIO: Obligatorio
                            'estado': 'ACTIVO'
                        }
                    )
                    if created:
                        enrollment_count += 1
                        print(f"Inscrito: {estudiante_usuario} con {docente_usuario}")
                except Exception as e:
                    inconsistencies.append(f"Error inscribiendo a {student_name}: {e}")

        # Reporte Final
        self.stdout.write(self.style.SUCCESS(f'Importación finalizada. Nuevas inscripciones: {enrollment_count}'))
        
        if unmatched_teachers:
            self.stdout.write(self.style.WARNING(f"Docentes no encontrados: {len(unmatched_teachers)} (ver logs)"))
            # Guardar logs...