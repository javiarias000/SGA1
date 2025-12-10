import os
import json
from django.core.management.base import BaseCommand
from subjects.models import Subject
from django.conf import settings

class Command(BaseCommand):
    help = 'Import subjects from JSON file names and horarios file'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Importando Materias ---'))
        
        created_count = 0
        
        json_base_dir = '/usr/src/base_de_datos_json'
        horarios_file_path = os.path.join(json_base_dir, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json')

        # --- Import subjects from horarios JSON file ---
        if os.path.exists(horarios_file_path):
            self.stdout.write(self.style.NOTICE(f'Procesando materias desde: {horarios_file_path}'))
            with open(horarios_file_path, 'r', encoding='utf-8') as f:
                horarios_data = json.load(f)
            
            for item in horarios_data:
                fields = item.get('fields', {})
                subject_name = fields.get('asignatura', '').strip()
                if subject_name:
                    # Simple cleaning, assuming manual correction of source JSON
                    cleaned_name = subject_name.strip()
                    # Capitalize first letter and remove multiple spaces
                    cleaned_name = ' '.join(cleaned_name.split()).capitalize()

                    if cleaned_name:
                        subject, created = Subject.objects.get_or_create(name__iexact=cleaned_name, defaults={'name': cleaned_name})
                        if created:
                            created_count += 1
                            self.stdout.write(self.style.SUCCESS(f'Creado desde horarios: "{subject.name}"'))

        else:
            self.stdout.write(self.style.WARNING(f"Archivo de horarios no encontrado: {horarios_file_path}"))
        
        # --- Import subjects from ASIGNACIONES_agrupaciones.json ---
        agrupaciones_file_path = os.path.join(json_base_dir, 'asignaciones_grupales', 'ASIGNACIONES_agrupaciones.json')
        if os.path.exists(agrupaciones_file_path):
            self.stdout.write(self.style.NOTICE(f'Procesando agrupaciones desde: {agrupaciones_file_path}'))
            try:
                with open(agrupaciones_file_path, 'r', encoding='utf-8') as f:
                    agrupaciones_data = json.load(f)
                
                unique_agrupaciones = set()
                for item in agrupaciones_data:
                    agrupacion_name = item.get('agrupacion', '').strip()
                    if agrupacion_name and agrupacion_name != "Agrupación": # Filter out header row if present
                        unique_agrupaciones.add(agrupacion_name)
                
                for cleaned_name in sorted(list(unique_agrupaciones)):
                    # Simple cleaning, similar to what's already in the script
                    # Capitalize first letter and remove multiple spaces
                    cleaned_name = ' '.join(cleaned_name.split()).capitalize()
                    
                    subject, created = Subject.objects.get_or_create(name__iexact=cleaned_name, defaults={'name': cleaned_name})
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Creado desde agrupaciones JSON: "{subject.name}"'))
            except (json.JSONDecodeError, IOError) as e:
                self.stdout.write(self.style.ERROR(f"Error al leer el archivo {agrupaciones_file_path}: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"Archivo de agrupaciones JSON no encontrado: {agrupaciones_file_path}"))

        # Subdirectories to scan for subject names

        
        # Subdirectories to scan for subject names
        subject_dirs = [
            'Instrumento_Agrupaciones',
            'asignaciones_grupales'
        ]

        
        for subject_dir in subject_dirs:
            dir_path = os.path.join(json_base_dir, subject_dir)
            if not os.path.exists(dir_path):
                self.stdout.write(self.style.WARNING(f"Directorio no encontrado: {dir_path}"))
                continue

            for filename in os.listdir(dir_path):
                if filename.endswith('.json') and filename != 'ESTUDIANTES_CON_REPRESENTANTES.json' and filename != 'ASIGNACIONES_instrumento_que_estudia_en_el_conservatorio_bolívar.json':
                    # Clean up the filename to get the subject name
                    name = filename.replace('ASIGNACIONES_', '').replace('.json', '')
                    
                    # Further cleaning
                    name = name.replace('acompañamiento', 'Acompañamiento')
                    name = name.replace('conj._inst', 'Conjunto instrumental')
                    name = name.replace('instrumento_que_estudia_en_el_conservatorio_bolívar', 'Instrumento Principal')

                    # General cleaning
                    name = name.replace('_', ' ').strip().capitalize()

                    # Create subject if it does not exist
                    subject, created = Subject.objects.get_or_create(name=name)
                    
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Creado: "{subject.name}"'))
        
        self.stdout.write(self.style.SUCCESS(f'--- Fin de la importación ---'))
        self.stdout.write(self.style.SUCCESS(f'Total de nuevas materias creadas: {created_count}'))