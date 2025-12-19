import json
import os
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Inspects a JSON file to infer its structure and identify where teacher data might be located.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando el inspector de archivos JSON para datos de docentes...'))

        # Base path where JSON files are expected to be mounted inside the Docker container
        base_json_dir = '/usr/src/base_de_datos_json/personal_docente/'
        
        file_name_input = input(self.style.NOTICE("Por favor, introduce el NOMBRE del archivo JSON de docentes (ej. DOCENTES.json): "))
        file_path = os.path.join(base_json_dir, file_name_input)

        if not os.path.exists(file_path):
            raise CommandError(f"El archivo no existe en la ruta esperada: '{file_path}'. Asegúrate de que el nombre del archivo sea correcto y que esté en la carpeta 'base_de_datos_json/personal_docente/' de tu proyecto.")
        
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line: # Only process non-empty lines
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            raise CommandError(f"Error al decodificar la línea {line_num} del archivo JSON. Asegúrate de que cada línea en '{file_path}' sea un JSON válido. Línea problemática: '{line}'")
            if not data:
                self.stdout.write(self.style.WARNING(f"El archivo '{file_path}' está vacío o no contiene JSON válido."))
                return # Exit if file is empty/invalid after processing
        except Exception as e:
            raise CommandError(f"Ocurrió un error al leer el archivo: {e}")

        self.stdout.write(self.style.SUCCESS(f"\nArchivo '{file_path}' cargado exitosamente (formato JSON Lines)."))
        self.stdout.write(self.style.NOTICE(f"Tipo de estructura principal (colección de líneas JSON): {type(data).__name__}"))

        teacher_data_found = False

        if isinstance(data, list):
            self.stdout.write(self.style.SUCCESS("\nLa estructura principal inferida es una LISTA de objetos JSON."))
            if data:
                self.stdout.write(self.style.NOTICE(f"El primer elemento de la lista es de tipo: {type(data[0]).__name__}"))
                if isinstance(data[0], dict):
                    self.stdout.write(self.style.NOTICE("Parece ser una lista de diccionarios, lo cual es un formato común para registros."))
                    self.stdout.write(self.style.NOTICE("Podrías acceder a los datos de los docentes como la lista 'data'."))
                    self.stdout.write(self.style.NOTICE("Ejemplo de acceso (en Python): `teacher_records = data`"))
                    self.stdout.write(self.style.NOTICE("Campos encontrados en el primer registro:"))
                    for key in data[0].keys():
                        self.stdout.write(f"  - '{key}'")
                    teacher_data_found = True
            else:
                self.stdout.write(self.style.WARNING("La lista de objetos JSON está vacía. No se pueden inferir campos."))

        elif isinstance(data, dict):
            self.stdout.write(self.style.SUCCESS("\nLa estructura principal es un DICCIONARIO."))
            self.stdout.write(self.style.NOTICE("Buscando claves que puedan contener una lista de docentes..."))
            
            potential_keys = ["teachers", "docentes", "records", "data", "maestros"]
            found_key = None

            for key in potential_keys:
                if key in data and isinstance(data[key], list):
                    found_key = key
                    break
            
            if found_key:
                self.stdout.write(self.style.NOTICE(f"Se encontró una lista de docentes bajo la clave '{found_key}'."))
                self.stdout.write(self.style.NOTICE(f"Podrías acceder a los datos de los docentes como: `teacher_records = data['{found_key}']`"))
                if data[found_key]:
                    self.stdout.write(self.style.NOTICE(f"El primer elemento de la lista es de tipo: {type(data[found_key][0]).__name__}"))
                    if isinstance(data[found_key][0], dict):
                        self.stdout.write(self.style.NOTICE("Campos encontrados en el primer registro:"))
                        for key_in_record in data[found_key][0].keys():
                            self.stdout.write(f"  - '{key_in_record}'")
                        teacher_data_found = True
                else:
                    self.stdout.write(self.style.WARNING(f"La lista bajo la clave '{found_key}' está vacía. No se pueden inferir campos."))
            else:
                self.stdout.write(self.style.WARNING("No se encontró una clave obvia que contenga una lista de docentes."))
                self.stdout.write("Claves de nivel superior encontradas:")
                for key in data.keys():
                    self.stdout.write(f"  - '{key}' (Tipo: {type(data[key]).__name__})")
        
        if not teacher_data_found:
            self.stdout.write(self.style.WARNING("\nNo se pudo inferir claramente dónde se encuentran los datos de los docentes."))
            self.stdout.write("Por favor, revisa manualmente la estructura del archivo JSON y elija la forma adecuada de acceder a los registros de los docentes.")
        
        self.stdout.write(self.style.SUCCESS('\nAnálisis de archivo JSON completado.'))
