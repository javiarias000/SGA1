import json
import os
import glob
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import models
from django.db.models import Q, F, Func, Value, ExpressionWrapper, fields
from django.db.models.functions import Replace
import difflib # For fuzzy matching

# Model Imports
from teachers.models import Teacher
from students.models import Student
from subjects.models import Subject
from classes.models import Clase, Enrollment

# Helper function (from previous script)
def normalize_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().replace('.', '').strip()
    titles = ["mgs", "lic", "dr", "ing"]
    for title in titles:
        name = name.replace(title + ' ', '')
    return ' '.join(name.split())

# Known non-teacher names (from previous script)
KNOWN_NON_TEACHER_NAMES = [
    "piano", "violín", "nulo", "maestro de instrumento",
    "rendí prueba de ubicación no tengo maestro asignado",
    "violín", "contrabajo", "flauta traversa", "guitarra",
    "percusión", "saxofón", "trombón", "trompeta", "viola", "violonchelo",
    "acompañamiento", "complementario", "conj. inst",
    "instrumento que estudia en el conservatorio bolívar"
]

class Command(BaseCommand):
    help = 'Identifies and suggests corrections for data inconsistencies in student and teacher names from JSON files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.7,
            help='Similarity threshold for fuzzy matching (0.0 to 1.0). Higher means stricter matching.'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Path to an output file to write the report to (e.g., inconsistencies_report.txt).'
        )

    def handle(self, *args, **options):
        output_file_path = options['output_file']
        output_file = None

        if output_file_path:
            try:
                output_file = open(output_file_path, 'w', encoding='utf-8')
                self.stdout.write(self.style.NOTICE(f'El reporte también se escribirá en: {output_file_path}'))
            except IOError as e:
                self.stdout.write(self.style.ERROR(f'No se pudo abrir el archivo de salida {output_file_path}: {e}. El reporte solo se mostrará en consola.'))
                output_file = None

        def write_output(message, style_func=self.style.HTTP_INFO):
            self.stdout.write(style_func(message))
            if output_file:
                output_file.write(message + '\n')

        # Replace self.stdout.write with write_output
        self.stdout.write = write_output

        self.stdout.write(self.style.SUCCESS('Iniciando el proceso de identificación y sugerencia de correcciones de datos...'))

        threshold = options['threshold']

        instrumento_agrupaciones_path = 'base_de_datos_json/Instrumento_Agrupaciones/'
        json_files = glob.glob(os.path.join(instrumento_agrupaciones_path, 'ASIGNACIONES_*.json'))
        
        if not json_files:
            raise CommandError(f"No se encontraron archivos JSON en {instrumento_agrupaciones_path}")

        self.stdout.write(self.style.NOTICE(f'Analizando {len(json_files)} archivos JSON de instrumentos.'))

        all_db_students = {normalize_name(s.name): s for s in Student.objects.all() if s.name}
        all_db_teachers = {normalize_name(t.full_name): t for t in Teacher.objects.all() if t.full_name}

        unmatched_students_json = set()
        unmatched_teachers_json = set()
        ambiguous_teachers_json = set()

        for json_file_path in json_files:
            file_name = os.path.basename(json_file_path)
            
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    instrument_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.stdout.write(self.style.ERROR(f'Error leyendo {file_name}: {e}. Saltando.'))
                continue
            
            for entry in instrument_data:
                fields = entry.get('fields', {})
                student_full_name_json = fields.get('full_name')
                teacher_full_name_json = fields.get('docente_nombre')

                if student_full_name_json:
                    normalized_student_json = normalize_name(student_full_name_json)
                    if normalized_student_json not in all_db_students:
                        unmatched_students_json.add(student_full_name_json)
                
                if teacher_full_name_json:
                    normalized_teacher_json = normalize_name(teacher_full_name_json)
                    if normalized_teacher_json in KNOWN_NON_TEACHER_NAMES:
                        continue # Already handled as non-teacher
                    
                    if normalized_teacher_json not in all_db_teachers:
                        unmatched_teachers_json.add(teacher_full_name_json)
                    else:
                        # Check for ambiguity if fuzzy matching was used
                        matches = [t_name for t_name in all_db_teachers.keys() if normalized_teacher_json in t_name]
                        if len(matches) > 1:
                            ambiguous_teachers_json.add(teacher_full_name_json)


        self.stdout.write(self.style.SUCCESS('\n--- SUGERENCIAS DE CORRECCIÓN ---'))

        # --- Sugerencias para Estudiantes ---
        self.stdout.write(self.style.NOTICE('\nEstudiantes No Coincididos / Inconsistentes:'))
        if not unmatched_students_json:
            self.stdout.write('  No se encontraron estudiantes no coincidentes en los archivos JSON.')
        else:
            for student_json_name in sorted(list(unmatched_students_json)):
                self.stdout.write(f'\n  Nombre JSON: {student_json_name}')
                suggestions = []
                for db_norm_name, db_student_obj in all_db_students.items():
                    similarity = difflib.SequenceMatcher(None, normalize_name(student_json_name), db_norm_name).ratio()
                    if similarity >= threshold:
                        suggestions.append((similarity, db_student_obj))
                
                if suggestions:
                    suggestions.sort(key=lambda x: x[0], reverse=True)
                    self.stdout.write('    Posibles coincidencias en la DB:')
                    for sim, db_student in suggestions:
                        self.stdout.write(f"      - {db_student.name} (ID: {db_student.id}, Código: {db_student.registration_code}, Similitud: {sim:.2f})")
                        self.stdout.write(f"        Comando sugerido: Student.objects.filter(id={db_student.id}).update(name='{student_json_name.replace("'", "\\'")}') # A Confirmar")
                else:
                    self.stdout.write('    No se encontraron coincidencias cercanas en la base de datos.')
                    self.stdout.write(f"    Acción sugerida: Crear el estudiante en la DB o verificar el nombre en JSON. (Comando: Student.objects.create(name='{student_json_name.replace("'", "\\'")}', ...))")
        # --- Sugerencias para Docentes ---
        self.stdout.write(self.style.NOTICE('\nDocentes No Coincididos / Inconsistentes:'))
        if not unmatched_teachers_json and not ambiguous_teachers_json:
            self.stdout.write('  No se encontraron docentes no coincidentes o ambiguos en los archivos JSON.')
        else:
            for teacher_json_name in sorted(list(unmatched_teachers_json)):
                self.stdout.write(f'\n  Nombre JSON: {teacher_json_name}')
                suggestions = []
                for db_norm_name, db_teacher_obj in all_db_teachers.items():
                    similarity = difflib.SequenceMatcher(None, normalize_name(teacher_json_name), db_norm_name).ratio()
                    if similarity >= threshold:
                        suggestions.append((similarity, db_teacher_obj))
                
                if suggestions:
                    suggestions.sort(key=lambda x: x[0], reverse=True)
                    self.stdout.write('    Posibles coincidencias en la DB:')
                    for sim, db_teacher in suggestions:
                        self.stdout.write(f"      - {db_teacher.full_name} (ID: {db_teacher.id}, Similitud: {sim:.2f})")
                        self.stdout.write(f"        Comando sugerido: Teacher.objects.filter(id={db_teacher.id}).update(full_name='{teacher_json_name.replace("'", "\\'")}') # A Confirmar")
                else:
                    self.stdout.write('    No se encontraron coincidencias cercanas en la base de datos.')
                    self.stdout.write(f"    Acción sugerida: Crear el docente en la DB o verificar el nombre en JSON. (Comando: Teacher.objects.create(full_name='{teacher_json_name.replace("'", "\\'")}', user=...))")
            for teacher_json_name in sorted(list(ambiguous_teachers_json)):
                self.stdout.write(f'\n  Nombre JSON (Ambiguo): {teacher_json_name}')
                self.stdout.write('    Múltiples docentes en la DB coinciden con este nombre JSON de forma flexible. Se requiere revisión manual.')
                self.stdout.write('    Posibles coincidencias en la DB:')
                for db_norm_name, db_teacher_obj in all_db_teachers.items():
                    if normalize_name(teacher_json_name) in db_norm_name: # Simple substring match for ambiguity
                         self.stdout.write(f"      - {db_teacher_obj.full_name} (ID: {db_teacher_obj.id})")

        self.stdout.write(self.style.SUCCESS('\nProceso de sugerencias de corrección finalizado. Por favor, revise las sugerencias.'))

