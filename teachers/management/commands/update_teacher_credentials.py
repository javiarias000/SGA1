import os
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teachers.models import Teacher

class Command(BaseCommand):
    help = 'Updates teacher emails and usernames from DOCENTES.json'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting Teacher Credentials Update ---'))

        # Define the path to the DOCENTES.json file
        file_path = '/usr/src/base_de_datos_json/personal_docente/DOCENTES.json'
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Error: DOCENTES.json not found at {file_path}'))
            return

        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Error: Could not decode JSON from a line in {file_path}. Error: {e}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred while reading the file: {e}'))
            return

        updated_count = 0
        skipped_count = 0

        for teacher_data in data:
            json_full_name = teacher_data.get('full_name')
            json_email = teacher_data.get('email')
            json_username = teacher_data.get('username')

            if not all([json_full_name, json_email, json_username]):
                self.stdout.write(self.style.WARNING(f'Skipping entry due to missing data: {teacher_data}'))
                skipped_count += 1
                continue

            teacher_found = None
            user_found = None
            try:
                # Try to find Teacher by full_name
                teacher_found = Teacher.objects.get(full_name__iexact=json_full_name)
                user_found = teacher_found.user
            except Teacher.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Teacher with full_name "{json_full_name}" not found. Skipping.'))
                skipped_count += 1
                continue
            except Teacher.MultipleObjectsReturned:
                self.stdout.write(self.style.ERROR(f'Multiple teachers found for full_name "{json_full_name}". Skipping. Manual intervention required.'))
                skipped_count += 1
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An unexpected error occurred while finding teacher "{json_full_name}": {e}'))
                skipped_count += 1
                continue
            
            if not user_found:
                self.stdout.write(self.style.WARNING(f'User not found for teacher "{json_full_name}". Skipping.'))
                skipped_count += 1
                continue

            # Construct the new email with the correct domain
            local_part = json_username.split('@')[0]
            new_email = local_part + '@docentes.educacion.edu.ec'

            # Update User object
            user_changed = False
            if user_found.email != new_email:
                user_found.email = new_email
                user_changed = True
                self.stdout.write(self.style.NOTICE(f'Updating email for {user_found.username} from "{user_found.email}" to "{new_email}"'))
            
            if user_found.username != json_username:
                # Ensure username is unique before updating
                if User.objects.filter(username=json_username).exclude(pk=user_found.pk).exists():
                    self.stdout.write(self.style.ERROR(f'New username "{json_username}" for {user_found.username} already exists for another user. Skipping username update.'))
                else:
                    user_found.username = json_username
                    user_changed = True
                    self.stdout.write(self.style.NOTICE(f'Updating username for {user_found.email} from "{user_found.username}" to "{json_username}"'))

            # Split full_name into first_name and last_name for User model
            name_parts = json_full_name.split()
            if len(name_parts) > 2:
                new_last_name = ' '.join(name_parts[:2])
                new_first_name = ' '.join(name_parts[2:])
            elif len(name_parts) == 2:
                new_last_name = name_parts[0]
                new_first_name = name_parts[1]
            else:
                new_last_name = json_full_name
                new_first_name = ''


            if user_found.first_name != new_first_name:
                user_found.first_name = new_first_name
                user_changed = True
                self.stdout.write(self.style.NOTICE(f'Updating first name for {user_found.username} to "{new_first_name}"'))
            if user_found.last_name != new_last_name:
                user_found.last_name = new_last_name
                user_changed = True
                self.stdout.write(self.style.NOTICE(f'Updating last name for {user_found.username} to "{new_last_name}"'))

            if user_changed:
                user_found.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Successfully updated User data for "{json_full_name}".'))
            else:
                self.stdout.write(self.style.NOTICE(f'No changes detected for User data of "{json_full_name}".'))

            # Update Teacher profile (full_name)
            try:
                teacher_profile = user_found.teacher_profile
                if teacher_profile.full_name != json_full_name:
                    teacher_profile.full_name = json_full_name
                    teacher_profile.save()
                    if not user_changed: # Only increment if user wasn't counted as updated
                        updated_count += 1 
                    self.stdout.write(self.style.SUCCESS(f'Successfully updated Teacher profile full_name for "{json_full_name}".'))
                else:
                    self.stdout.write(self.style.NOTICE(f'No changes detected for Teacher profile full_name of "{json_full_name}".'))

            except Teacher.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Teacher profile for user "{user_found.username}" not found. Skipping Teacher profile update.'))
                skipped_count += 1
            
        self.stdout.write(self.style.SUCCESS('--- Teacher Credentials Update Finished ---'))
        self.stdout.write(self.style.SUCCESS(f'Total users updated: {updated_count}'))
        self.stdout.write(self.style.WARNING(f'Total users skipped: {skipped_count}'))
