
import os
import json
import unicodedata
import re
import csv
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth.models import User
from users.models import Usuario
from students.models import Student
from classes.models import Clase, Subject, GradeLevel

# --- Configuración ---
JSON_AGRUPACIONES_PATH = "/usr/src/app/base_de_datos_json/normalized/asignaciones_grupales/asignaciones_completas.json"
JSON_TEORICAS_PATH = "/usr/src/app/base_de_datos_json/normalized/horarios_academicos/REPORTE_DOCENTES_HORARIOS_0858.json"
GRAPHQL_URL = "http://localhost:8000/graphql/"
ASSIGNMENT_LOG_FILE = "assignment_all_students_log.csv"

ENROLL_STUDENT_MUTATION = """
mutation EnrollStudent($studentId: ID!, $claseId: ID!, $docenteId: ID) {
  enrollStudentInClass(studentUsuarioId: $studentId, claseId: $claseId, docenteUsuarioId: $docenteId) {
    enrollment {
      id
      estudiante { nombre }
      clase { name }
      docente { nombre }
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
    help = 'Asigna estudiantes a clases de agrupaciones y teóricas usando los JSONs provistos.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = {}
        self.grade_level_cache = {}
        self.log_writer = None
        self.log_file = None
        self.client = None

    def _setup_log_file(self):
        self.log_file = open(ASSIGNMENT_LOG_FILE, 'w', newline='', encoding='utf-8')
        self.log_writer = csv.writer(self.log_file)
        self.log_writer.writerow(['Archivo Origen', 'Tipo Asignacion', 'Estudiante (JSON)', 'Docente (JSON)', 'Clase (JSON)', 'Status', 'Detalle'])

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

    def _run_graphql_request(self, query, variables=None):
        payload = {'query': query}
        if variables: payload['variables'] = variables
        try:
            response = self.client.post(GRAPHQL_URL, json.dumps(payload), content_type='application/json', HTTP_HOST='localhost')
            if response.status_code != 200:
                return {'errors': [{'message': f"HTTP Error {response.status_code}", 'details': response.content.decode()}]}
            json_response = response.json()
            return json_response
        except Exception as e:
            return {'errors': [{'message': f"Error de petición: {str(e)}"}]}

    def _get_or_create_user_and_student(self, full_name):
        normalized_name = normalize_name(full_name)
        if normalized_name in self.user_cache: return self.user_cache[normalized_name]

        user = None
        # Buscar usuario existente por nombre normalizado
        for u in Usuario.objects.filter(rol=Usuario.Rol.ESTUDIANTE):
            if normalize_name(u.nombre) == normalized_name:
                user = u
                break
        
        if not user:
            # Si no existe, crear el Usuario y su perfil de Student
            email_base = normalize_name(full_name).replace(' ', '.')
            email = f"{email_base}@conservatorio-temporal.edu.ec"
            user = Usuario.objects.create(
                nombre=full_name,
                email=email,
                rol=Usuario.Rol.ESTUDIANTE
            )
            Student.objects.create(usuario=user)
            self.stdout.write(f"  -> Creado Estudiante: {full_name} (ID: {user.id})")
        
        self.user_cache[normalized_name] = user
        return user
    
    def _get_or_create_teacher_user(self, full_name):
        normalized_name = normalize_name(full_name)
        if normalized_name in self.user_cache: return self.user_cache[normalized_name]

        user = None
        # Buscar usuario existente por nombre normalizado
        for u in Usuario.objects.filter(rol=Usuario.Rol.DOCENTE):
            if normalize_name(u.nombre) == normalized_name:
                user = u
                break
        
        if not user:
            self.stdout.write(self.style.WARNING(f"  -> ADVERTENCIA: Docente '{full_name}' no encontrado. Se buscará en todos los usuarios para crear o se omitirá."))
            # Si el docente no existe como tal, intentar encontrarlo como Usuario o crear uno.
            email_base = normalize_name(full_name).replace(' ', '.')
            email = f"{email_base}@conservatorio-docente-temporal.edu.ec"
            user, created = Usuario.objects.get_or_create(
                nombre=full_name,
                defaults={'email': email, 'rol': Usuario.Rol.DOCENTE}
            )
            if created:
                self.stdout.write(f"  -> Creado Docente: {full_name} (ID: {user.id})")
            else:
                self.stdout.write(f"  -> Encontrado Usuario para Docente: {full_name} (ID: {user.id})")

        self.user_cache[normalized_name] = user
        return user

    def _get_or_create_grade_level(self, curso, paralelo):
        if (curso, paralelo) in self.grade_level_cache: return self.grade_level_cache[(curso, paralelo)]
        
        grade_level, created = GradeLevel.objects.get_or_create(
            level=curso,
            section=paralelo
        )
        if created:
            self.stdout.write(f"  -> Creado GradeLevel: {curso} {paralelo} (ID: {grade_level.id})")
        
        self.grade_level_cache[(curso, paralelo)] = grade_level
        return grade_level


    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando la asignación de estudiantes a materias de agrupaciones y teóricas..."))
        self._setup_log_file()
        
        self.client = self._get_authenticated_client()
        if not self.client:
            self._close_log_file()
            return

        self.stdout.write("Precargando usuarios y niveles de grado en caché...")
        for user in Usuario.objects.all():
            self.user_cache[normalize_name(user.nombre)] = user
        for gl in GradeLevel.objects.all():
            self.grade_level_cache[(gl.level, gl.section)] = gl
        self.stdout.write(f"{len(self.user_cache)} usuarios cargados.")
        self.stdout.write(f"{len(self.grade_level_cache)} niveles de grado cargados.")

        total_procesados = 0
        total_enrollments_exitosos = 0
        
        # --- Procesar asignaciones_completas.json (Agrupaciones) ---
        self.stdout.write(self.style.HTTP_INFO(f"\n--- Procesando: {JSON_AGRUPACIONES_PATH} (Agrupaciones) ---"))
        try:
            with open(JSON_AGRUPACIONES_PATH, 'r', encoding='utf-8') as f:
                agrupaciones_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {JSON_AGRUPACIONES_PATH}"))
            self._close_log_file()
            return

        for item in agrupaciones_data:
            total_procesados += 1
            record = item.get("fields", item) # Manejar si 'fields' no está anidado
            
            estudiante_nombre = record.get("nombre_completo") or record.get("full_name")
            docente_nombre = record.get("docente_asignado")
            clase_nombre = record.get("agrupacion") or record.get("clase")

            if not all([estudiante_nombre, docente_nombre, clase_nombre]):
                self.log_writer.writerow(['asignaciones_completas.json', 'AGRUPACION', estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Registro JSON incompleto o faltan datos clave"])
                continue
            
            self.stdout.write(f"  -> Agrupación: Estudiante '{estudiante_nombre}' a '{clase_nombre}' con '{docente_nombre}'")

            student_user = self._get_or_create_user_and_student(estudiante_nombre)
            if not student_user:
                self.log_writer.writerow(['asignaciones_completas.json', 'AGRUPACION', estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Estudiante no encontrado/creado"])
                continue
            
            teacher_user = self._get_or_create_teacher_user(docente_nombre)
            if not teacher_user:
                self.log_writer.writerow(['asignaciones_completas.json', 'AGRUPACION', estudiante_nombre, docente_nombre, clase_nombre, "FALLO", "Docente no encontrado/creado"])
                continue

            subject, _ = Subject.objects.get_or_create(name=clase_nombre, defaults={'tipo_materia': 'AGRUPACION'})
            
            clase_defaults = {'name': clase_nombre, 'subject': subject, 'ciclo_lectivo': '2025-2026', 'docente_base': teacher_user}
            clase, created_clase = Clase.objects.get_or_create(
                name=clase_nombre,
                subject=subject,
                docente_base=teacher_user,
                ciclo_lectivo='2025-2026', # Asegurarse de la unicidad para evitar duplicados
                defaults=clase_defaults
            )
            if created_clase:
                self.stdout.write(f"    -> Creada Clase de Agrupación: {clase_nombre} (ID: {clase.id})")

            enroll_vars = {"studentId": str(student_user.id), "claseId": str(clase.id), "docenteId": str(teacher_user.id)}
            result = self._run_graphql_request(ENROLL_STUDENT_MUTATION, enroll_vars)
            
            if result and result.get('data', {}).get('enrollStudentInClass'):
                self.stdout.write(self.style.SUCCESS(f"    -> Éxito: '{estudiante_nombre}' inscrito en '{clase_nombre}'"))
                self.log_writer.writerow(['asignaciones_completas.json', 'AGRUPACION', estudiante_nombre, docente_nombre, clase_nombre, "EXITO", ""])
                total_enrollments_exitosos += 1
            else:
                self.log_writer.writerow(['asignaciones_completas.json', 'AGRUPACION', estudiante_nombre, docente_nombre, clase_nombre, "FALLO", f"Mutación GraphQL falló: {result.get('errors', 'Error desconocido')}"])
        
        # --- Procesar REPORTE_DOCENTES_HORARIOS_0858.json (Teóricas) ---
        self.stdout.write(self.style.HTTP_INFO(f"\n--- Procesando: {JSON_TEORICAS_PATH} (Materias Teóricas) ---"))
        try:
            with open(JSON_TEORICAS_PATH, 'r', encoding='utf-8') as f:
                teoricas_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {JSON_TEORICAS_PATH}"))
            self._close_log_file()
            return
        
        processed_classes = set() # Para evitar procesar la misma clase/horario múltiples veces

        for item in teoricas_data:
            total_procesados += 1
            record = item.get("fields", item) # Manejar si 'fields' no está anidado

            curso = record.get("curso")
            paralelo = record.get("paralelo")
            clase_nombre = record.get("clase")
            docente_nombre = record.get("docente")

            if not all([curso, paralelo, clase_nombre, docente_nombre]):
                self.log_writer.writerow(['REPORTE_DOCENTES_HORARIOS_0858.json', 'TEORICA', 'N/A', docente_nombre, clase_nombre, "FALLO", "Registro JSON incompleto o faltan datos clave"])
                continue
            
            # Si el docente es "ND" o "Nulo", lo omitimos o lo tratamos como sin docente
            if docente_nombre.strip().lower() in ["nd", "nulo", ""]:
                teacher_user = None
                self.stdout.write(f"  -> Teórica: Clase '{clase_nombre}' para '{curso} {paralelo}' sin docente asignado.")
            else:
                teacher_user = self._get_or_create_teacher_user(docente_nombre)
                if not teacher_user:
                    self.log_writer.writerow(['REPORTE_DOCENTES_HORARIOS_0858.json', 'TEORICA', 'N/A', docente_nombre, clase_nombre, "FALLO", "Docente no encontrado/creado"])
                    continue
                self.stdout.write(f"  -> Teórica: Clase '{clase_nombre}' para '{curso} {paralelo}' con '{docente_nombre}'")

            # Mapear o crear GradeLevel
            grade_level = self._get_or_create_grade_level(curso, paralelo)
            if not grade_level:
                self.log_writer.writerow(['REPORTE_DOCENTES_HORARIOS_0858.json', 'TEORICA', 'N/A', docente_nombre, clase_nombre, "FALLO", "GradeLevel no encontrado/creado"])
                continue

            # Obtener o crear Subject (asumimos tipo TEORIA para estas)
            subject, _ = Subject.objects.get_or_create(name=clase_nombre, defaults={'tipo_materia': 'TEORIA'})
            
            # Obtener o crear la Clase
            # Aquí es crucial para evitar duplicados, usar la combinación de grade_level y subject
            clase_unique_key = (clase_nombre, subject.id, grade_level.id, teacher_user.id if teacher_user else None)
            if clase_unique_key in processed_classes:
                continue # Ya procesamos esta combinación de clase/docente/nivel
            
            clase_defaults = {'name': clase_nombre, 'subject': subject, 'ciclo_lectivo': '2025-2026', 'grade_level': grade_level}
            if teacher_user:
                clase_defaults['docente_base'] = teacher_user

            clase, created_clase = Clase.objects.get_or_create(
                name=clase_nombre, # Considerar que el nombre de la clase puede ser más específico
                subject=subject,
                grade_level=grade_level,
                docente_base=teacher_user,
                ciclo_lectivo='2025-2026',
                defaults=clase_defaults
            )
            processed_classes.add(clase_unique_key)

            if created_clase:
                self.stdout.write(f"    -> Creada Clase Teórica: {clase_nombre} ({curso} {paralelo}) (ID: {clase.id})")
            
            # --- Inscribir a todos los estudiantes de ese GradeLevel a esta Clase ---
            students_in_grade_level = Student.objects.filter(grade_level=grade_level)
            self.stdout.write(f"    -> Inscribiendo {students_in_grade_level.count()} estudiantes de '{curso} {paralelo}' a '{clase_nombre}'")

            for student in students_in_grade_level:
                student_user = student.usuario
                enroll_vars = {"studentId": str(student_user.id), "claseId": str(clase.id)}
                if teacher_user:
                    enroll_vars["docenteId"] = str(teacher_user.id)
                else:
                    enroll_vars["docenteId"] = None # Docente opcional en la mutación

                result = self._run_graphql_request(ENROLL_STUDENT_MUTATION, enroll_vars)

                if result and result.get('data', {}).get('enrollStudentInClass'):
                    self.stdout.write(self.style.SUCCESS(f"      -> Éxito: '{student_user.nombre}' inscrito en '{clase_nombre}'"))
                    self.log_writer.writerow([os.path.basename(JSON_TEORICAS_PATH), 'TEORICA', student_user.nombre, docente_nombre, clase_nombre, "EXITO", ""])
                    total_enrollments_exitosos += 1
                else:
                    error_msg = result.get('errors', 'Error desconocido')
                    self.log_writer.writerow([os.path.basename(JSON_TEORICAS_PATH), 'TEORICA', student_user.nombre, docente_nombre, clase_nombre, "FALLO", f"Mutación GraphQL falló: {error_msg}"])

        self._close_log_file()
        self.stdout.write(self.style.SUCCESS(f"\n--- Proceso Finalizado ---"))
        self.stdout.write(f"Total de registros de JSON procesados: {total_procesados}")
        self.stdout.write(f"Total de inscripciones exitosas: {total_enrollments_exitosos}")
        self.stdout.write(f"Log detallado guardado en: {ASSIGNMENT_LOG_FILE}")
