import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teachers.models import Teacher
from django.db import transaction

class Command(BaseCommand):
    help = 'Loads teachers from a JSON file into the database'

    def handle(self, *args, **options):
        json_file_path = 'base_de_datos_json/personal_docente/DOCENTES.json'
        
        try:
            with open(json_file_path, 'r') as f:
                # The JSON is line-delimited, so we read it line by line
                for line in f:
                    data = json.loads(line)
                    
                    username = data.get('username')
                    email = data.get('email')
                    full_name = data.get('full_name', '').strip()
                    password = data.get('password_plano')

                    if not username:
                        self.stdout.write(self.style.WARNING(f"Skipping record due to missing username: {data}"))
                        continue

                    # Split full_name into first_name and last_name
                    name_parts = full_name.split(' ')
                    first_name = name_parts[0] if name_parts else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    with transaction.atomic():
                        user, created = User.objects.update_or_create(
                            username=username,
                            defaults={
                                'email': email,
                                'first_name': first_name,
                                'last_name': last_name,
                                'is_staff': True # Assuming teachers are staff
                            }
                        )

                        if created:
                            user.set_password(password)
                            user.save()
                            self.stdout.write(self.style.SUCCESS(f"Created user for {username}"))
                        else:
                            # If user already exists, check if password needs to be set/updated
                            if not user.has_usable_password() and password:
                                user.set_password(password)
                                user.save()
                            self.stdout.write(self.style.SUCCESS(f"Updated user for {username}"))

                        # The signal should have created a Teacher profile.
                        # Now, let's update the full_name in the Teacher profile.
                        if hasattr(user, 'teacher_profile'):
                            teacher_profile = user.teacher_profile
                            teacher_profile.full_name = full_name
                            teacher_profile.save()
                            self.stdout.write(self.style.SUCCESS(f"Updated teacher profile for {full_name}"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {json_file_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
