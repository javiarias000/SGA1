import json
import os
import openpyxl
from django.core.management.base import BaseCommand, CommandError

# Helper function (for normalization)
def normalize_name(name):
    """Normaliza un nombre (convierte a minúsculas, elimina puntos y títulos)."""
    if not isinstance(name, str):
        return ""
    name = name.lower().replace('.', '').strip()
    titles = ["mgs", "lic", "dr", "ing", "mgtr", "phd"] # Se añadieron más títulos comunes
    for title in titles:
        # Asegura que el título se reemplace solo si está seguido por un espacio o al final
        name = name.replace(title + ' ', ' ')
        if name.endswith(title):
             name = name[:-len(title)].strip()
    return ' '.join(name.split())

class Command(BaseCommand):
    help = 'Enriches DOCENTES.json with phone and Cedula data from an Excel file.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando el enriquecimiento de datos de docentes...'))

        # --- Define file paths ---
        original_json_file_path = '/usr/src/base_de_datos_json/personal_docente/DOCENTES.json'
        enriched_json_file_path = '/usr/src/base_de_datos_json/personal_docente/DOCENTES_enriched.json' # NEW OUTPUT FILE
        excel_file_path = '/usr/src/archivos_formularios/DATOS DOCENTES 2025 Conservatorio Bolívar.xlsx'
        
        # --- Configuración de cabeceras ---
        EXCEL_NAME_HEADER = "APELLIDOS Y NOMBRES"
        EXCEL_PHONE_HEADER = "\nCELULAR" # Usando el encabezado corregido del script original
        EXCEL_CEDULA_HEADER = "CEDULA"
        
        # Normalización de cabeceras de Excel (claves de búsqueda)
        NORMALIZED_NAME_KEY = normalize_name(EXCEL_NAME_HEADER)
        NORMALIZED_PHONE_KEY = normalize_name(EXCEL_PHONE_HEADER)
        NORMALIZED_CEDULA_KEY = normalize_name(EXCEL_CEDULA_HEADER)


        # --- 1. Load existing DOCENTES.json data ---
        teacher_json_data = []
        try:
            with open(original_json_file_path, 'r', encoding='utf-8') as f:
                # El archivo parece ser JSON Lines, cargamos línea por línea.
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            # Añadimos el nombre normalizado para una búsqueda eficiente
                            data['normalized_full_name'] = normalize_name(data.get('full_name', ''))
                            teacher_json_data.append(data)
                        except json.JSONDecodeError:
                            raise CommandError(f"Error al decodificar la línea {line_num} de {original_json_file_path}. Línea problemática: '{line}'")
            # ... (verificaciones omitidas para brevedad, pero mantenidas de tu script)
            self.stdout.write(self.style.SUCCESS(f"'{original_json_file_path}' cargado exitosamente. Se encontraron {len(teacher_json_data)} registros."))
        except Exception as e:
            raise CommandError(f"Ocurrió un error al leer o procesar el archivo JSON: {e}")

        # --- 2. Load and Index Excel file data ---
        excel_lookup_data = {} # Diccionario para búsqueda rápida: {normalized_name: row_data}
        try:
            workbook = openpyxl.load_workbook(excel_file_path)
            sheet = workbook.active
            
            # Asunción: Encabezados en fila 3
            headers = [cell.value for cell in sheet[3]]
            
            # Identificar las posiciones de las columnas clave
            try:
                # Buscamos la posición de la columna de nombre usando la cabecera exacta
                name_col_index = headers.index(EXCEL_NAME_HEADER) 
                
                # Buscamos las posiciones de las cabeceras de Celular y Cédula (usando normalización para flexibilidad)
                # Creamos un mapa de cabeceras normalizadas a su índice (posición)
                normalized_headers_map = {normalize_name(str(h)): idx for idx, h in enumerate(headers)}

                phone_col_index = normalized_headers_map.get(NORMALIZED_PHONE_KEY)
                cedula_col_index = normalized_headers_map.get(NORMALIZED_CEDULA_KEY)
                
            except ValueError:
                # Si no encontramos la cabecera principal de nombre (APELLIDOS Y NOMBRES)
                 raise CommandError(f"La columna '{EXCEL_NAME_HEADER}' no se encontró en la Fila 3 del archivo Excel. Encabezados encontrados: {headers}")

            if phone_col_index is None:
                self.stdout.write(self.style.WARNING("No se encontró la columna 'Celular' en el archivo Excel. No se extraerá el teléfono."))
            if cedula_col_index is None:
                self.stdout.write(self.style.WARNING("No se encontró la columna 'Cedula' en el archivo Excel. No se extraerá la cédula."))

            # Iterar desde la Fila 4 para obtener los datos
            for row_num in range(4, sheet.max_row + 1):
                row = sheet[row_num]
                
                # Obtener el nombre para indexación y normalizarlo
                excel_name = row[name_col_index].value if row[name_col_index].value else ""
                normalized_excel_name = normalize_name(str(excel_name))
                
                if not normalized_excel_name:
                    continue # Saltar filas sin nombre
                
                # Construir el diccionario de datos de la fila
                row_data = {}
                
                # Extraer Celular
                if phone_col_index is not None:
                    phone_val = row[phone_col_index].value
                    # Convertir a cadena y limpiar posibles formatos flotantes (p. ej., 9.99e+09)
                    row_data['phone'] = str(phone_val).split('.')[0].strip() if phone_val is not None else ""

                # Extraer Cédula
                if cedula_col_index is not None:
                    cedula_val = row[cedula_col_index].value
                    row_data['cedula'] = str(cedula_val).split('.')[0].strip() if cedula_val is not None else ""

                # Indexar por el nombre normalizado para el lookup
                excel_lookup_data[normalized_excel_name] = row_data

            self.stdout.write(self.style.SUCCESS(f"'{excel_file_path}' cargado e indexado exitosamente. Se indexaron {len(excel_lookup_data)} registros únicos."))
        except FileNotFoundError:
            raise CommandError(f"Archivo Excel no encontrado: {excel_file_path}")
        except Exception as e:
            raise CommandError(f"Ocurrió un error al leer o procesar el archivo Excel: {e}")

        # --- 3. Enrich JSON data and save new file ---
        enriched_data = []
        updates_count = 0

        for teacher in teacher_json_data:
            # Usar el nombre normalizado precalculado del JSON
            normalized_json_name = teacher.get('normalized_full_name')
            
            # Buscar el docente en los datos del Excel
            match = excel_lookup_data.get(normalized_json_name)
            
            if match:
                # Fusión de datos: Añadir 'phone' y 'cedula' si existen en el Excel
                if 'phone' in match:
                    teacher['phone'] = match['phone']
                if 'cedula' in match:
                    teacher['cedula'] = match['cedula']
                updates_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"Docente no encontrado en Excel: {teacher.get('full_name')} (normalizado: {normalized_json_name})"))
            
            # Eliminar la clave temporal de normalización antes de guardar
            teacher.pop('normalized_full_name', None)
            enriched_data.append(teacher)
        
        # --- 4. Save the enriched JSON data to the new file ---
        try:
            with open(enriched_json_file_path, 'w', encoding='utf-8') as f:
                # Guardamos como JSON Lines (un objeto por línea)
                for teacher_data in enriched_data:
                    f.write(json.dumps(teacher_data, ensure_ascii=False) + '\n')
            
            self.stdout.write(self.style.SUCCESS(f"\n--- ¡Proceso Completado! ---"))
            self.stdout.write(self.style.SUCCESS(f"Se enriquecieron {updates_count} de {len(teacher_json_data)} registros de docentes."))
            self.stdout.write(self.style.SUCCESS(f"El archivo enriquecido ha sido guardado en: {enriched_json_file_path}"))

        except Exception as e:
            raise CommandError(f"Error al escribir el archivo JSON enriquecido: {e}")