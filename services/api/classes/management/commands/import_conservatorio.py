import re
import secrets, string # Import for random password generation
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from openpyxl import load_workbook
from students.models import Student
from teachers.models import Teacher
from classes.models import Clase, Enrollment, GradeLevel # Added GradeLevel import
from subjects.models import Subject
from users.models import Usuario

from utils.etl_normalization import ( # Import normalization utilities
    _clean_person_name, # Added
    canonical_subject_name,
    canonical_teacher_name,
    canonical_student_name, # Added
    load_aliases,
    map_grade_level, # Added
)


# Removed norm() function as we will use canonical functions directly

def slug_username(name):
    # Use _clean_person_name for slugging
    base = re.sub(r"[^a-z0-9]", "", _clean_person_name(name).lower()) or "docente"
    candidate = base[:20]
    i = 1
    while User.objects.filter(username=candidate).exists():
        i += 1
        candidate = f"{base[:18]}{i:02d}"
    return candidate


def get_or_create_teacher(full_name_raw: str, teacher_aliases) -> Teacher: # Modified signature
    # Use canonical_teacher_name for robust matching
    full_name = canonical_teacher_name(full_name_raw, teacher_aliases)
    
    if not full_name:
        full_name = "Docente Sistema"

    # Try to find an existing Usuario (teacher role) with this name
    usuario = Usuario.objects.filter(rol=Usuario.Rol.DOCENTE, nombre__iexact=full_name).first()

    if not usuario:
        # If Usuario doesn't exist, create it along with a Django User
        username = slug_username(full_name)
        rand = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        
        user = User.objects.create_user(
            username=username,
            password=rand,
            email=f"{username}@example.com", # Placeholder email
            first_name=full_name.split(' ')[0] if full_name else '',
            last_name=' '.join(full_name.split(' ')[1:]) if full_name else '',
            is_staff=True # Ensure teachers are staff
        )
        user.save()

        usuario = Usuario.objects.create(
            auth_user=user,
            rol=Usuario.Rol.DOCENTE,
            nombre=full_name,
            email=user.email,
        )
        usuario.save()

    # Now, ensure a Teacher profile exists for this Usuario
    # The Teacher model will automatically inherit the full_name from Usuario via property
    teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
    return teacher


class Command(BaseCommand):
    help = "Importa estudiantes, materias, clases y matrículas desde los archivos de Excel del Conservatorio"

    def add_arguments(self, parser):
        # Update default paths to relative paths
        parser.add_argument('--matriculados', default='../archivos_formularios/25-26 Matriculados Conservatorio Bolívar de AMbato2.xlsx')
        parser.add_argument('--distribucion', default='../archivos_formularios/25-26 Distribucion instrumento, agrupaciones.xlsx')
        parser.add_argument('--horarios', default='../archivos_formularios/2025-2026 horarios cursos.xlsx')
        parser.add_argument('--dry-run', action='store_true', help='No guarda cambios, solo muestra resumen')

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts['dry_run']
        # Added grade_levels to created summary
        created = {"students": 0, "clases": 0, "enrollments": 0, "teachers": 0, "subjects": 0, "grade_levels": 0} 
        
        # Load aliases
        subj_aliases, teacher_aliases, student_aliases = load_aliases('base_de_datos_json')

        # Cache for Usuario (students and teachers)
        # Using _clean_person_name for index keys for consistency
        usuarios_by_normname: Dict[str, Usuario] = {} 

        def index_usuario(u: Usuario):
            # For this script, we assume unique names from matriculation
            key = _clean_person_name(u.nombre) # Use _clean_person_name for indexing
            usuarios_by_normname[key] = u

        # Pre-index existing Usuarios
        for u in Usuario.objects.all().only('id', 'nombre', 'rol'):
            index_usuario(u)

        # Helper: find student Usuario by name
        def find_student_usuario_by_name(full_name_raw: str) -> Optional[Usuario]:
            full_name = canonical_student_name(full_name_raw, student_aliases) # Use canonical function
            return usuarios_by_normname.get(_clean_person_name(full_name)) # Use _clean_person_name for lookup

        # Helper: find teacher Usuario by name (re-using get_or_create_teacher logic)
        def find_teacher_usuario_by_name(full_name_raw: str) -> Optional[Usuario]:
            full_name = canonical_teacher_name(full_name_raw, teacher_aliases)
            return usuarios_by_normname.get(_clean_person_name(full_name))