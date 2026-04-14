import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import Usuario
from teachers.models import Teacher
from utils.etl_normalization import canonical_teacher_name

class Command(BaseCommand):
    help = 'Imports teachers from DOCENTES.json and creates Usuario, Teacher, and auth User profiles.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help='Path to the JSON file containing teacher data (e.g., base_de_datos_json/personal_docente/DOCENTES.json)',
            default='base_de_datos_json/personal_docente/DOCENTES.json'
        )

    def handle(self, *args, **options):
        json_path = options['path']
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'JSON file not found at {json_path}'))
            return

        data = []
        with open(json_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        self.stdout.write(self.style.ERROR(f'Error decoding JSON line: {line} - {e}'))
                        continue
        
        self.stdout.write(self.style.SUCCESS(f'Importing teachers from {json_path}...'))

        created_usuario_count = 0
        updated_usuario_count = 0
        created_teacher_profile_count = 0
        updated_teacher_profile_count = 0
        created_auth_user_count = 0
        linked_auth_user_count = 0

        for entry in data:
            raw_full_name = entry.get('full_name')
            if not raw_full_name:
                self.stdout.write(self.style.WARNING(f'Skipping entry due to missing "full_name": {entry}'))
                continue
            
            cleaned_name = canonical_teacher_name(raw_full_name)
            if not cleaned_name:
                self.stdout.write(self.style.WARNING(f'Skipping entry for "{raw_full_name}" due to empty cleaned name.'))
                continue

            # Create or update Usuario
            usuario, usuario_created = Usuario.objects.get_or_create(
                nombre=cleaned_name,
                defaults={'rol': Usuario.Rol.DOCENTE}
            )
            if usuario_created:
                created_usuario_count += 1
            else:
                updated_usuario_count += 1
                if usuario.rol != Usuario.Rol.DOCENTE:
                    usuario.rol = Usuario.Rol.DOCENTE
                    usuario.save()

            # Create or link auth_user
            if usuario.auth_user is None:
                username_from_json = entry.get('email') or entry.get('username')
                if not username_from_json:
                    self.stdout.write(self.style.ERROR(f'Skipping auth user for {cleaned_name} due to missing username/email in JSON.'))
                    continue

                # Ensure username is unique for django.contrib.auth.models.User
                unique_username = username_from_json
                counter = 1
                while User.objects.filter(username=unique_username).exists():
                    unique_username = f"{username_from_json}_{counter}"
                    counter += 1
                
                auth_user = User.objects.create(username=unique_username)
                if entry.get('password_plano'):
                    auth_user.set_password(entry['password_plano'])
                else:
                    auth_user.set_unusable_password() # Or set a default password
                
                auth_user.email = entry.get('email', '')
                auth_user.first_name = entry.get('Nombres', '').split(' ')[0] if entry.get('Nombres') else ''
                auth_user.last_name = entry.get('Apellidos', '').split(' ')[0] if entry.get('Apellidos') else ''
                auth_user.save()

                usuario.auth_user = auth_user
                usuario.email = auth_user.email # Sync email
                usuario.save()
                created_auth_user_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created and linked new auth User: {unique_username} for {usuario.nombre}'))
            else:
                # If auth_user already exists, just update its password/email if changed
                auth_user = usuario.auth_user
                password_from_json = entry.get('password_plano')
                email_from_json = entry.get('email')

                if password_from_json and not auth_user.check_password(password_from_json):
                    auth_user.set_password(password_from_json)
                    self.stdout.write(self.style.WARNING(f'Updated password for existing auth User: {auth_user.username}'))
                
                if email_from_json and auth_user.email != email_from_json:
                    auth_user.email = email_from_json
                    self.stdout.write(self.style.WARNING(f'Updated email for existing auth User: {auth_user.username}'))
                
                auth_user.first_name = entry.get('Nombres', '').split(' ')[0] if entry.get('Nombres') else auth_user.first_name
                auth_user.last_name = entry.get('Apellidos', '').split(' ')[0] if entry.get('Apellidos') else auth_user.last_name
                auth_user.save()
                linked_auth_user_count += 1
                self.stdout.write(self.style.WARNING(f'Usuario {usuario.nombre} already has auth User {auth_user.username}. Ensured password/email is up to date.'))

            # Create or update Teacher profile
            teacher_profile, teacher_profile_created = Teacher.objects.get_or_create(
                usuario=usuario,
                defaults={'specialization': entry.get('especialidad', '')}
            )
            if teacher_profile_created:
                created_teacher_profile_count += 1
            else:
                updated_teacher_profile_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Finished importing teachers.\n'
            f'Usuarios created: {created_usuario_count}, existing: {updated_usuario_count}\n'
            f'Teacher profiles created: {created_teacher_profile_count}, existing: {updated_teacher_profile_count}\n'
            f'Auth Users created: {created_auth_user_count}, linked: {linked_auth_user_count}'
        ))