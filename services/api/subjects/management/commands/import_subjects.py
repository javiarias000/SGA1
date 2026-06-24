import json
import os
from django.core.management.base import BaseCommand
from subjects.models import Subject
from utils.etl_normalization import canonical_subject_name

class Command(BaseCommand):
    help = 'Imports subjects from JSON files.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help='Path to the JSON file containing subject data (e.g., asignaciones_grupales/ASIGNACIONES_agrupaciones.json)',
            default='base_de_datos_json/asignaciones_grupales/ASIGNACIONES_agrupaciones.json'
        )

    def handle(self, *args, **options):
        json_path = options['path']
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'JSON file not found at {json_path}'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stdout.write(self.style.ERROR(f'Expected a list of objects in {json_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Importing subjects from {json_path}...'))

        # Assuming subjects can be found in 'instrumento' and 'agrupacion' fields
        unique_subjects = set()
        for entry in data:
            instrumento = entry.get('instrumento')
            if instrumento:
                unique_subjects.add(canonical_subject_name(instrumento))
            agrupacion = entry.get('agrupacion')
            if agrupacion:
                unique_subjects.add(canonical_subject_name(agrupacion))
        
        created_count = 0
        updated_count = 0

        for subject_name in unique_subjects:
            if not subject_name:
                continue
            
            subject, created = Subject.objects.get_or_create(
                name=subject_name,
                defaults={'description': f'Materia importada: {subject_name}'} # Default description
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created subject: {subject.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Subject already exists: {subject.name}'))

        self.stdout.write(self.style.SUCCESS(f'Finished importing subjects. Created: {created_count}, Existing: {updated_count}'))