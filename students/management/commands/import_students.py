from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'DEPRECADO: usa el ETL unificado etl_import_json (idempotente) para docentes/estudiantes/materias/clases.'

    def add_arguments(self, parser):
        parser.add_argument('--ciclo', default='2025-2026')
        parser.add_argument('--base-dir', default='base_de_datos_json')
        parser.add_argument('--create-student-users', action='store_true')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        self.stdout.write(self.style.WARNING('import_students está deprecado. Ejecutando etl_import_json...'))
        call_command(
            'etl_import_json',
            ciclo=opts['ciclo'],
            base_dir=opts['base_dir'],
            create_student_users=opts['create_student_users'],
            dry_run=opts['dry_run'],
        )
