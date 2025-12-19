import openpyxl
import os
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Solicita una ruta relativa a un archivo Excel y extrae los encabezados de la Fila 1.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando extractor de encabezados...'))

        # --- 1. Solicitar la ruta del archivo ---
        # Usamos input() para pedir la ruta de forma interactiva
        relative_path = input("Por favor, introduce la RUTA RELATIVA del archivo Excel (ej: archivos_formularios/nombre.xlsx): ")
        
        # Obtener el directorio base de tu proyecto Django
        # Esto asume que el comando se ejecuta desde la raíz del proyecto (donde está manage.py)
        project_root = os.getcwd()
        
        # Combinar la ruta base con la ruta relativa proporcionada
        excel_file_path = os.path.join(project_root, relative_path)
        
        self.stdout.write(self.style.SUCCESS(f"Buscando archivo en: {excel_file_path}"))
        
        # --- 2. Cargar y Extraer Encabezados ---
        try:
            # Verificar si el archivo existe antes de intentar cargarlo
            if not os.path.exists(excel_file_path):
                raise FileNotFoundError(f"El archivo no existe en la ruta: {excel_file_path}")

            # Cargar el libro de trabajo (Workbook)
            workbook = openpyxl.load_workbook(excel_file_path)
            sheet = workbook.active
            
            # Extraer los datos de la Fila 1 (encabezados)
            fila_encabezado = 1
            # Iteramos sobre las celdas de la fila 1 y obtenemos su valor.
            encabezados = [cell.value for cell in sheet[fila_encabezado]]
            
            # --- 3. Mostrar los resultados ---
            self.stdout.write(self.style.SUCCESS("\n--- Encabezados Encontrados (Fila 1) ---"))
            for i, header in enumerate(encabezados, 1):
                display_header = str(header).strip() if header is not None else "[VACÍO]"
                self.stdout.write(f"Columna {i}: {display_header}")
                
            self.stdout.write(self.style.SUCCESS("--------------------------------------"))
            self.stdout.write(self.style.SUCCESS("\nExtracción completada exitosamente."))
            
        except FileNotFoundError as e:
            raise CommandError(str(e))
        except Exception as e:
            raise CommandError(f"Ocurrió un error al leer o procesar el archivo Excel: {e}")