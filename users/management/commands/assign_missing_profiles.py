from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from users.models import Usuario
from teachers.models import Teacher
from students.models import Student

User = get_user_model()

class Command(BaseCommand):
    help = 'Ensures all existing User instances have a corresponding Usuario profile and the correct role-specific profile (Teacher or Student).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Starting profile assignment for existing users..."))

        users_processed = 0
        usuarios_created = 0
        teachers_created = 0
        students_created = 0

        with transaction.atomic():
            for user in User.objects.all():
                users_processed += 1
                self.stdout.write(f"Processing user: {user.username} (ID: {user.id})")

                # 1. Ensure Usuario exists and has correct rol
                usuario_defaults = {
                    'nombre': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'email': user.email,
                }
                # Default to ESTUDIANTE for non-staff, otherwise DOCENTE
                initial_rol = Usuario.Rol.DOCENTE if user.is_staff else Usuario.Rol.ESTUDIANTE

                # Get or create Usuario; importantly, use initial_rol only for newly created
                usuario_defaults = {
                    'nombre': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'email': user.email,
                    'rol': initial_rol # Include rol directly in the defaults
                }
                
                usuario, created_usuario = Usuario.objects.get_or_create(
                    auth_user=user,
                    defaults=usuario_defaults
                )

                if created_usuario:
                    usuarios_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  Created Usuario for {user.username} with rol: {usuario.rol}"))
                else:
                    # Update Usuario fields if user data changed, or if rol needs correction
                    needs_save = False
                    current_name = f"{user.first_name} {user.last_name}".strip() or user.username
                    if usuario.nombre != current_name:
                        usuario.nombre = current_name
                        needs_save = True
                    if usuario.email != user.email and user.email: # Only update if user.email is not empty
                        usuario.email = user.email
                        needs_save = True

                    # Check if the rol needs to be updated based on is_staff, but respect manually set PENDIENTE
                    if usuario.rol == Usuario.Rol.PENDIENTE:
                        # If PENDIENTE, don't auto-assign a specific rol unless forced or explicitly set by other means
                        self.stdout.write(f"  Usuario for {user.username} has PENDING rol. Skipping automatic rol update.")
                    elif user.is_staff and usuario.rol != Usuario.Rol.DOCENTE:
                        usuario.rol = Usuario.Rol.DOCENTE
                        needs_save = True
                    elif not user.is_staff and usuario.rol != Usuario.Rol.ESTUDIANTE and usuario.rol != Usuario.Rol.DOCENTE:
                        # If not staff, not a teacher, and not already student, set to student
                        usuario.rol = Usuario.Rol.ESTUDIANTE
                        needs_save = True
                    
                    if needs_save:
                        usuario.save()
                        self.stdout.write(self.style.WARNING(f"  Updated existing Usuario for {user.username}, new rol: {usuario.rol}"))
                    else:
                        self.stdout.write(f"  Usuario for {user.username} already exists and is up-to-date. Rol: {usuario.rol}")

                # 2. Ensure role-specific profile (Teacher/Student) exists based on final usuario.rol
                if usuario.rol == Usuario.Rol.DOCENTE:
                    if not hasattr(usuario, 'teacher_profile'):
                        Teacher.objects.create(usuario=usuario, specialization='')
                        teachers_created += 1
                        self.stdout.write(self.style.SUCCESS(f"    Created Teacher profile for {user.username}"))
                    else:
                        self.stdout.write(f"    Teacher profile for {user.username} already exists.")
                    
                    # If user is a Teacher, ensure no Student profile
                    if hasattr(usuario, 'student_profile'):
                        self.stdout.write(self.style.WARNING(f"    Deleting Student profile for {user.username} as rol is DOCENTE."))
                        usuario.student_profile.delete()
                
                elif usuario.rol == Usuario.Rol.ESTUDIANTE:
                    if not hasattr(usuario, 'student_profile'):
                        Student.objects.create(usuario=usuario) # registration_code will be generated on save
                        students_created += 1
                        self.stdout.write(self.style.SUCCESS(f"    Created Student profile for {user.username}"))
                    else:
                        self.stdout.write(f"    Student profile for {user.username} already exists.")
                    
                    # If user is a Student, ensure no Teacher profile
                    if hasattr(usuario, 'teacher_profile'):
                        self.stdout.write(self.style.WARNING(f"    Deleting Teacher profile for {user.username} as rol is ESTUDIANTE."))
                        usuario.teacher_profile.delete()

                elif usuario.rol == Usuario.Rol.PENDIENTE:
                    self.stdout.write(f"  Usuario for {user.username} has PENDING rol. No specific role profile created yet.")
                    # Ensure no teacher/student profile exists if rol is PENDING
                    if hasattr(usuario, 'teacher_profile'):
                        self.stdout.write(self.style.WARNING(f"    Deleting Teacher profile for {user.username} as rol is PENDIENTE."))
                        usuario.teacher_profile.delete()
                    if hasattr(usuario, 'student_profile'):
                        self.stdout.write(self.style.WARNING(f"    Deleting Student profile for {user.username} as rol is PENDIENTE."))
                        usuario.student_profile.delete()

        self.stdout.write(self.style.MIGRATE_HEADING("\nProfile assignment complete."))
        self.stdout.write(self.style.SUCCESS(f"Total users processed: {users_processed}"))
        self.stdout.write(self.style.SUCCESS(f"New Usuario profiles created: {usuarios_created}"))
        self.stdout.write(self.style.SUCCESS(f"New Teacher profiles created: {teachers_created}"))
        self.stdout.write(self.style.SUCCESS(f"New Student profiles created: {students_created}"))
