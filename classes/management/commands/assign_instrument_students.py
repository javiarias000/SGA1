
import os
import json
import unicodedata
import re
import csv
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth.models import User
from users.models import Usuario
from classes.models import Clase, Subject

# --- Configuración ---
JSON_DIR = "/usr/src/base_de_datos_json/normalized/Instrumento_Agrupaciones"
ACTION_LOG_FILE = "assignment_final_log.csv" # Nuevo archivo de log

ENROLL_STUDENT_MUTATION = """
mutation EnrollStudent($studentId: ID!, $claseId: ID!, $docenteId: ID) {
  enrollStudentInClass(studentUsuarioId: $studentId, claseId: $claseId, docenteUsuarioId: $docenteId) {
    enrollment {
      id
    }
  }
}
"""

def normalize_name(name):
    if not name: return ""
    name = str(name)
    nfkd_form = unicodedata.normalize('NFD', name)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return re.sub(r'\s+', ' ', only_ascii).strip().lower()

class Command(BaseCommand):
    help = 'Asigna estudiantes usando los archivos JSON corregidos.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = {}
        self.log_writer = None
        self.log_file = None

    def _setup_log_file(self):
        self.log_file = open(ACTION_LOG_FILE, 'w', newline='', encoding='utf-8')
        self.log_writer = csv.writer(self.log_file)
        self.log_writer.writerow(['Archivo JSON', 'Estudiante (JSON)', 'Docente (JSON)', 'Clase (JSON)', 'Status', 'Detalle'])

    def _close_log_file(self):
        if self.log_file: self.log_file.close()

    def _get_authenticated_client(self):
        client = Client()
        user = User.objects.filter(is_superuser=True).first()
        if not user: user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("No se encontró ningún usuario para la autenticación."))
            return None
        client.force_login(user)
        self.stdout.write(self.style.SUCCESS(f"Cliente autenticado como: {user.username}"))
        return client

    def _run_graphql_request(self, client, query, variables=None):
        payload = {'query': query}
        if variables: payload['variables'] = variables
        try:
            response = client.post("/graphql/", json.dumps(payload), content_type='application/json', HTTP_HOST='localhost')
            if response.status_code != 200:
                self.log_writer.writerow(['N/A', '', '', '', 'FALLO_HTTP', f"Status: {response.status_code}"])
                return None
            json_response = response.json()
            if 'errors' in json_response:
                self.log_writer.writerow(['N/A', '', '', '', 'FALLO_GRAPHQL', json_response['errors']])
                return None
            return json_response
        except Exception as e:
            self.log_writer.writerow(['N/A', '', '', '', 'FALLO_PETICION', str(e)])
            return None

    def _find_user(self, normalized_name):
        return self.user_cache.get(normalized_name)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando la asignación final con los JSON corregidos..."))
        self._setup_log_file()
        
        client = self._get_authenticated_client()
        if not client:
            self._close_log_file()
            return

        json_files = [f for f in os.listdir(JSON_DIR) if f.endswith('_CORREGIDO.json')]
        
        self.stdout.write("Precargando usuarios en caché...")
        for user in Usuario.objects.all():
            self.user_cache[normalize_name(user.nombre)] = user
        self.stdout.write(f"{len(self.user_cache)} usuarios cargados.")

        total_asignaciones = 0
        total_exitosas = 0

        for file_name in json_files:
            file_path = os.path.join(JSON_DIR, file_name)
            self.stdout.write(self.style.HTTP_INFO(f"\n--- Procesando archivo: {file_name} ---"))
            
            with open(file_path, 'r', encoding='utf-8') as f:
                asignaciones = json.load(f)

            for item in asignaciones:
                total_asignaciones += 1
                record = item.get("fields", {})
                
                estudiante_nombre = record.get("full_name")
                docente_nombre = record.get("docente_nombre")
                clase_nombre = record.get("clase")

                if not estudiante_nombre or not clase_nombre:
                    self.log_writer.writerow([file_name, estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Registro JSON incompleto"])
                    continue

                student_user = self._find_user(normalize_name(estudiante_nombre))
                if not student_user:
                    self.log_writer.writerow([file_name, estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Estudiante no encontrado"])
                    continue

                teacher_user = None
                if docente_nombre:
                    teacher_user = self._find_user(normalize_name(docente_nombre))
                    if not teacher_user:
                        self.log_writer.writerow([file_name, estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Docente no encontrado"])
                        continue
                
                subject, _ = Subject.objects.get_or_create(name=clase_nombre, defaults={'tipo_materia': 'AGRUPACION'})
                
                clase_defaults = {'name': clase_nombre, 'subject': subject}
                if teacher_user:
                    clase_defaults['docente_base'] = teacher_user

                clase, _ = Clase.objects.get_or_create(
                    name=clase_nombre,
                    ciclo_lectivo='2025-2026',
                    defaults=clase_defaults
                )

                enroll_vars = {"studentId": str(student_user.id), "claseId": str(clase.id)}
                if teacher_user:
                    enroll_vars["docenteId"] = str(teacher_user.id)
                else: 
                    # El ID del docente puede ser nulo en GraphQL
                    enroll_vars["docenteId"] = None
                
                result = self._run_graphql_request(client, ENROLL_STUDENT_MUTATION, enroll_vars)
                
                if result and result.get('data', {}).get('enrollStudentInClass'):
                    self.stdout.write(self.style.SUCCESS(f"  -> Éxito: '{estudiante_nombre}' en '{clase_nombre}'"))
                    self.log_writer.writerow([file_name, estudiante_nombre, docente_nombre, clase_nombre, "EXITO", ""])
                    total_exitosas += 1
                else:
                    self.log_writer.writerow([file_name, estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Mutación GraphQL falló"])

        self._close_log_file()
        self.stdout.write(self.style.SUCCESS(f"\n--- Proceso Finalizado ---"))
        self.stdout.write(f"Total procesados: {total_asignaciones}, Exitosas: {total_exitosas}, Fallidos: {total_asignaciones - total_exitosas}")
        self.stdout.write(f"Log detallado guardado en: {ACTION_LOG_FILE}")
