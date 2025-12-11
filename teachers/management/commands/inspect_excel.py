import pandas as pd
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Inspects the columns of the teacher data Excel file'

    def handle(self, *args, **kwargs):
        file_path = '/usr/src/archivos_formularios/DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx'
        try:
            df = pd.read_excel(file_path, nrows=5)
            self.stdout.write(self.style.SUCCESS('--- Excel File Columns ---'))
            self.stdout.write(str(df.columns))
            self.stdout.write(self.style.SUCCESS('--- First 5 Rows ---'))
            self.stdout.write(str(df.head()))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
