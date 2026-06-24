import json
import os
import glob
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User # Import User model
from users.models import Usuario
from students.models import Student
from classes.models import GradeLevel
from django.db.utils import IntegrityError
from utils.etl_normalization import canonical_student_name, map_grade_level

class Command(BaseCommand):
    help = 'Imports students from JSON files and creates Usuario and Student profiles.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path_pattern',
            type=str,
            help='Glob pattern for JSON files containing student data (e.g., base_de_datos_json/estudiantes_matriculados/*.json)',
            default='base_de_datos_json/estudiantes_matriculados/*.json'
        )

    def handle(self, *args, **options):
        path_pattern = options['path_pattern']
        json_files = glob.glob(path_pattern)

        if not json_files:
            self.stdout.write(self.style.ERROR(f'No JSON files found matching pattern: {path_pattern}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Importing students from files matching {path_pattern}...'))

        created_usuario_count = 0
        updated_usuario_count = 0
        created_student_profile_count = 0
        updated_student_profile_count = 0
        created_auth_user_count = 0
        linked_auth_user_count = 0
        
        # Cache GradeLevels for efficient lookup
        grade_levels_cache = {
            (gl.level, gl.section): gl for gl in GradeLevel.objects.all()
        }

        for json_path in json_files:
            self.stdout.write(f'Processing file: {json_path}')
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Error decoding JSON from {json_path}: {e}'))
                continue
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
                continue

            if not isinstance(data, list):
                self.stdout.write(self.style.ERROR(f'Expected a list of objects in {json_path}, skipping.'))
                continue

            for entry in data:
                # Access nested 'fields' dictionary
                fields = entry.get('fields', {})
                
                raw_student_name = fields.get('Apellidos', '') + ' ' + fields.get('Nombres', '')
                if not raw_student_name.strip():
                    self.stdout.write(self.style.WARNING(f'Skipping entry due to missing student name in {json_path}: {entry}'))
                    continue
                
                cleaned_student_name = canonical_student_name(raw_student_name)
                if not cleaned_student_name:
                    self.stdout.write(self.style.WARNING(f'Skipping entry for "{raw_student_name}" due to empty cleaned name in {json_path}.'))
                    continue

                cedula_value = str(fields.get('Número de Cédula del Estudiante')) if fields.get('Número de Cédula del Estudiante') else None
                email_value = fields.get('email')

                usuario = None
                # Prioritize lookup by cedula, which is unique
                if cedula_value:
                    usuario = Usuario.objects.filter(cedula=cedula_value).first()
                
                # If not found by cedula, try by email, which is also unique
                if not usuario and email_value:
                    usuario = Usuario.objects.filter(email=email_value).first()

                if usuario: # Found an existing Usuario by unique identifiers (cedula or email)
                    usuario_created = False
                    # Update fields of the existing Usuario
                    usuario.nombre = cleaned_student_name
                    usuario.rol = Usuario.Rol.ESTUDIANTE

                    if email_value and usuario.email != email_value:
                        # Check if the new email is already taken by another Usuario
                        if Usuario.objects.filter(email=email_value).exclude(pk=usuario.pk).exists():
                            self.stdout.write(self.style.WARNING(f'Skipping email update for existing Usuario {usuario.nombre} as email {email_value} is already taken by another Usuario.'))
                        else:
                            usuario.email = email_value
                    
                    # Update phone if provided
                    if fields.get('Número de cédula del Representante'):
                        usuario.phone = str(fields.get('Número de cédula del Representante'))
                    
                    usuario.save()

                    updated_usuario_count += 1
                    self.stdout.write(self.style.WARNING(f'Updated existing Usuario: {usuario.nombre}'))

                else: # No existing Usuario found by unique identifiers, so create a new one
                    usuario_created = True
                    defaults = {
                        'rol': Usuario.Rol.ESTUDIANTE,
                        'nombre': cleaned_student_name,
                    }
                    if email_value:
                        defaults['email'] = email_value
                    if fields.get('Número de cédula del Representante'):
                        defaults['phone'] = str(fields.get('Número de cédula del Representante'))
                    
                    try:
                        if cedula_value:
                            usuario = Usuario.objects.create(cedula=cedula_value, **defaults)
                        else: # If no cedula, create without it. email uniqueness is handled by the model.
                            usuario = Usuario.objects.create(**defaults)
                    except IntegrityError as e:
                        if 'email' in str(e).lower() and email_value:
                            self.stdout.write(self.style.ERROR(f'IntegrityError creating Usuario for {cleaned_student_name} with email {email_value}. Email likely duplicated. Trying to create without email.'))
                            if 'email' in defaults:
                                del defaults['email']
                            if cedula_value:
                                usuario = Usuario.objects.create(cedula=cedula_value, **defaults)
                            else:
                                usuario = Usuario.objects.create(**defaults)
                        else:
                            raise e # Re-raise other integrity errors
                    
                    created_usuario_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created Usuario: {usuario.nombre}'))

                # Create or link auth_user
                if usuario.auth_user is None:
                    username_from_json = email_value if email_value else cedula_value
                    if not username_from_json:
                        self.stdout.write(self.style.ERROR(f'Skipping auth user for {cleaned_student_name} due to missing email or cedula in JSON.'))
                        continue
                    
                    # Ensure username is unique for django.contrib.auth.models.User
                    unique_username = username_from_json
                    counter = 1
                    while User.objects.filter(username=unique_username).exists():
                        unique_username = f"{username_from_json}_{counter}"
                        counter += 1

                    auth_user = User.objects.create(username=unique_username)
                    auth_user.set_password("temporal123") # Default password for students
                    auth_user.email = email_value if email_value else '' # Set email if available
                    auth_user.first_name = fields.get('Nombres', '').split(' ')[0] if fields.get('Nombres') else ''
                    auth_user.last_name = fields.get('Apellidos', '').split(' ')[0] if fields.get('Apellidos') else ''
                    auth_user.save()
                    
                    # Sync email, checking for uniqueness
                    if auth_user.email and usuario.email != auth_user.email:
                        if Usuario.objects.filter(email=auth_user.email).exclude(pk=usuario.pk).exists():
                            self.stdout.write(self.style.WARNING(f'Skipping email update for {usuario.nombre} as email {auth_user.email} is already taken by another Usuario.'))
                        else:
                            usuario.email = auth_user.email
                    usuario.save()
                    created_auth_user_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created and linked new auth User: {unique_username} for {usuario.nombre}'))
                else:
                    # If auth_user already exists, just update its password/email if changed
                    auth_user = usuario.auth_user
                    # For students, we have no 'password_plano' in JSON, so we assume it's "temporal123" if not set
                    if not auth_user.has_usable_password() or not auth_user.check_password("temporal123"): # Check if password is not set or not the default
                        auth_user.set_password("temporal123")
                        self.stdout.write(self.style.WARNING(f'Set default password for existing auth User: {auth_user.username}'))
                    
                    # Update email, checking for uniqueness
                    if email_value and auth_user.email != email_value:
                        if Usuario.objects.filter(email=email_value).exclude(pk=usuario.pk).exists():
                            self.stdout.write(self.style.WARNING(f'Skipping email update for {usuario.nombre} as email {email_value} is already taken by another Usuario.'))
                        else:
                            auth_user.email = email_value
                            self.stdout.write(self.style.WARNING(f'Updated email for existing auth User: {auth_user.username}'))
                    
                    auth_user.first_name = fields.get('Nombres', '').split(' ')[0] if fields.get('Nombres') else auth_user.first_name
                    auth_user.last_name = fields.get('Apellidos', '').split(' ')[0] if fields.get('Apellidos') else auth_user.last_name
                    auth_user.save()
                    linked_auth_user_count += 1
                    self.stdout.write(self.style.WARNING(f'Usuario {usuario.nombre} already has auth User {auth_user.username}. Ensured password/email is up to date.'))


                # Determine GradeLevel
                curso_raw = fields.get('CURSO')
                paralelo_raw = fields.get('PARALELO')
                grade_level_obj = None
                
                if curso_raw and paralelo_raw:
                    parsed_grade_level = map_grade_level(curso_raw, paralelo_raw)
                    if parsed_grade_level.level and parsed_grade_level.section:
                        grade_level_key = (parsed_grade_level.level, parsed_grade_level.section)
                        grade_level_obj = grade_levels_cache.get(grade_level_key)
                        if not grade_level_obj:
                            # This should ideally not happen if import_gradelevels ran successfully
                            self.stdout.write(self.style.ERROR(f'GradeLevel not found for {grade_level_key}. Student {usuario.nombre} will not have a grade level assigned.'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Could not map grade level for student {usuario.nombre} from Curso: "{curso_raw}", Paralelo: "{paralelo_raw}".'))


                # Create or update Student profile
                student_profile, student_profile_created = Student.objects.get_or_create(
                    usuario=usuario,
                    defaults={
                        'grade_level': grade_level_obj,
                        'parent_name': f"{str(fields.get('Apellidos del Representante del Estudiante', ''))} {str(fields.get('Nombres del Representante del Estudiante', ''))}".strip(),
                        'parent_phone': str(fields.get('Número de cédula del Representante')) if fields.get('Número de cédula del Representante') else '',
                        # 'parent_email': fields.get('email_representante', ''), # Assuming 'email_representante' field if it exists
                    }
                )
                if student_profile_created:
                    created_student_profile_count += 1
                else:
                    updated_student_profile_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Finished importing students.\n'
            f'Usuarios created: {created_usuario_count}, existing: {updated_usuario_count}\n'
            f'Student profiles created: {created_student_profile_count}, existing: {updated_student_profile_count}\n'
            f'Auth Users created: {created_auth_user_count}, linked: {linked_auth_user_count}'
        ))