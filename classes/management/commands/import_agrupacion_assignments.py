
import os
import json
from django.core.management.base import BaseCommand, CommandError
from subjects.models import Subject
from teachers.models import Teacher
from classes.models import Clase # Asumiendo que Clase es el modelo para las asignaciones

class Command(BaseCommand):
    help = 'Import teacher assignments to groups from asignaciones_docentes.json'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Importando Asignaciones de Docentes a Agrupaciones ---'))
        
        json_file_path = 'asignaciones_docentes.json' # Ahora está en la raíz del proyecto dentro del contenedor Docker

        if not os.path.exists(json_file_path):
            raise CommandError(f'El archivo JSON de asignaciones no fue encontrado en: {json_file_path}')

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                assignments_data = json.load(f)
        except json.JSONDecodeError:
            raise CommandError(f'Error al decodificar el JSON de {json_file_path}. Asegúrese de que sea un JSON válido.')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for assignment in assignments_data:
            agrupacion_name = assignment.get('agrupacion')
            docente_name = assignment.get('docente_asignado')

            if not agrupacion_name or not docente_name:
                self.stdout.write(self.style.WARNING(f'Saltando entrada inválida: {assignment} (falta agrupación o docente)'))
                skipped_count += 1
                continue

            try:
                subject = Subject.objects.get(name__iexact=agrupacion_name)
            except Subject.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'No se encontró la materia (agrupación): "{agrupacion_name}". Saltando asignación.'))
                skipped_count += 1
                continue

            try:
                teacher = Teacher.objects.get(full_name__iexact=docente_name)
            except Teacher.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'No se encontró el docente: "{docente_name}". Saltando asignación.'))
                skipped_count += 1
                continue
            
            # Crear o actualizar la Clase
            # Usamos el nombre de la agrupación como nombre de la clase
            clase_name = f"{subject.name} - {teacher.full_name}" # Un nombre descriptivo para la clase

            clase, created = Clase.objects.update_or_create(
                subject=subject,
                teacher=teacher,
                defaults={
                    'name': clase_name,
                    'description': f'Clase de la agrupación {subject.name} dirigida por {teacher.full_name}',
                    # Puedes añadir más valores por defecto si son necesarios en Clase
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Creada asignación: "{clase.name}" (Docente: {teacher.full_name}, Agrupación: {subject.name})'))
            else:
                updated_count += 1
                self.stdout.write(self.style.NOTICE(f'Actualizada asignación: "{clase.name}" (Docente: {teacher.full_name}, Agrupación: {subject.name})'))

        self.stdout.write(self.style.SUCCESS('--- Fin de la importación de asignaciones ---'))
        self.stdout.write(self.style.SUCCESS(f'Asignaciones creadas: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Asignaciones actualizadas: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'Asignaciones saltadas (errores): {skipped_count}'))

