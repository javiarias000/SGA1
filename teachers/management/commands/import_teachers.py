import os
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teachers.models import Teacher

class Command(BaseCommand):
    help = 'Import teachers from a JSON file'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Importando Docentes ---'))

        file_path = '/usr/src/base_de_datos_json/personal_docente/DOCENTES.json'
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {file_path}'))
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        created_count = 0
        updated_count = 0

        for item in data:
            fields = item.get('fields', {})
            username = fields.get('username')
            if not username:
                continue

            # Split full_name into first_name and last_name
            full_name = fields.get('full_name', '')
            name_parts = full_name.split()
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': fields.get('email'),
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )

            if created:
                # Set a default password
                password = fields.get('password_plano', 'password123')
                user.set_password(password)
                user.save()
                
                # The signal will create the Teacher profile, but we can update it if needed
                teacher_profile = user.teacher_profile
                teacher_profile.full_name = full_name
                # Add any other fields from the JSON that need to be populated
                # teacher_profile.phone = fields.get('telefono') 
                teacher_profile.save()
                
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Usuario y perfil de docente creados para: "{full_name}"'))
            else:
                # Update existing user if necessary
                user.email = fields.get('email')
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                
                # Ensure teacher profile exists and update it
                teacher_profile, profile_created = Teacher.objects.get_or_create(user=user)
                if profile_created:
                    self.stdout.write(self.style.WARNING(f'Perfil de docente no existía, creado para: "{full_name}"'))

                teacher_profile.full_name = full_name
                teacher_profile.save()

                updated_count += 1
                self.stdout.write(self.style.NOTICE(f'Datos de docente actualizados para: "{full_name}"'))

        self.stdout.write(self.style.SUCCESS('--- Fin de la importación ---'))
        self.stdout.write(self.style.SUCCESS(f'Nuevos docentes creados: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Docentes actualizados: {updated_count}'))
