import os
import pandas as pd
import json
from django.core.management.base import BaseCommand

# --- Configuración ---
BASE_DIR = "/usr/src/app/" # Directorio raíz del proyecto en el contenedor
EXCEL_FILENAME = "25-26_Distribucion_instrumento_agrupaciones.xlsx" # Nombre exacto del archivo
OUTPUT_DIR = "/usr/src/base_de_datos_json/normalized/Instrumento_Agrupaciones"

class Command(BaseCommand):
    help = 'Extrae datos de asignaciones desde un archivo Excel y los guarda como JSON.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando la extracción de datos desde el archivo Excel..."))

        excel_file_path = os.path.join(BASE_DIR, EXCEL_FILENAME)

        if not os.path.exists(excel_file_path):
            self.stdout.write(self.style.ERROR(f"El archivo Excel no se encuentra en la ruta: {excel_file_path}"))
            return

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        try:
            xls = pd.ExcelFile(excel_file_path, engine='openpyxl')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"No se pudo leer el archivo Excel. Error: {e}"))
            return

        for sheet_name in xls.sheet_names:
            if sheet_name.lower() not in ["conj. inst", "acompañamiento"]:
                self.stdout.write(self.style.WARNING(f"Omitiendo hoja '{sheet_name}'."))
                continue

            output_filename = f"ASIGNACIONES_{sheet_name.lower().replace('.', '').replace(' ', '_')}_CORREGIDO.json"
            self.stdout.write(f"\n--- Procesando hoja: '{sheet_name}' ---")
            
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                
                # Mapeo de columnas dinámico
                if sheet_name.lower() == "acompañamiento":
                    column_mapping = {
                        'Apellidos del Estudiante': 'apellidos',
                        'Nombres del Estudiante': 'nombres',
                        'Año de estudio': 'grado',
                        'PARALELO (señalar el mismo paralelo en el que estuvieron el año anterior)': 'paralelo',
                        'Docente piano acompañamiento': 'docente_nombre'
                    }
                    df.rename(columns=column_mapping, inplace=True)
                    df['clase'] = 'Acompañamiento'

                elif sheet_name.lower() == "conj. inst":
                    column_mapping = {
                        'Apellidos del Estudiante': 'apellidos',
                        'Nombres del Estudiante': 'nombres',
                        'Año de estudio': 'grado',
                        'PARALELO (señalar el mismo paralelo en el que estuvieron el año anterior)': 'paralelo',
                        'Agrupación': 'clase'
                    }
                    df.rename(columns=column_mapping, inplace=True)
                    # En esta hoja, no hay docente explícito, se deja vacío
                    df['docente_nombre'] = ""

                required_cols = ['apellidos', 'nombres']
                if not all(col in df.columns for col in required_cols):
                    self.stdout.write(self.style.ERROR(f"Columnas requeridas no encontradas en '{sheet_name}'."))
                    continue

                df.dropna(subset=required_cols, how='all', inplace=True)
                df['full_name'] = df['apellidos'].astype(str).str.strip() + " " + df['nombres'].astype(str).str.strip()

                export_cols = ['full_name', 'grado', 'paralelo', 'clase', 'docente_nombre']
                output_df = df[[col for col in export_cols if col in df.columns]].copy()
                
                records = output_df.to_dict('records')
                
                final_json_data = []
                for i, record in enumerate(records):
                    record['docente_nombre'] = record.get('docente_nombre', '') or ''
                    final_json_data.append({
                        "model": "default.data",
                        "pk": i + 1,
                        "fields": record
                    })

                output_path = os.path.join(OUTPUT_DIR, output_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(final_json_data, f, ensure_ascii=False, indent=2)
                
                self.stdout.write(self.style.SUCCESS(f"  -> Datos guardados exitosamente en: {output_path} ({len(final_json_data)} registros)"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  -> Ocurrió un error al procesar la hoja '{sheet_name}': {e}"))

        self.stdout.write(self.style.SUCCESS("\n--- Proceso de extracción finalizado ---"))