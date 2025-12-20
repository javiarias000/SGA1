from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

from teachers.models import Teacher
from students.models import Student
from users.models import Usuario
from classes.models import Enrollment, Clase

class Command(BaseCommand):
    help = 'Assigns teachers to students based on their enrollments and class assignments.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting student-teacher assignment...'))

        with transaction.atomic():
            # Clear existing student-teacher assignments if rebuilding cleanly
            # Student.objects.all().update(teacher=None)
            # self.stdout.write(self.style.WARNING('Cleared existing student-teacher assignments (optional step).'))

            assignments_made = 0
            unassigned_students = 0

            # Get all enrollments where the docente is set
            enrollments = Enrollment.objects.filter(docente__isnull=False, clase__docente_base__isnull=False).select_related('estudiante', 'docente', 'clase', 'clase__docente_base')

            for enrollment in enrollments:
                student_profile = enrollment.estudiante # enrollment.estudiante is already a Student object
                teacher_usuario = enrollment.docente or enrollment.clase.docente_base # Prefer enrollment.docente if available

                if student_profile and teacher_usuario:
                    try:
                        teacher_profile = Teacher.objects.get(usuario=teacher_usuario)

                        # Assign the teacher if not already assigned or if it needs to be updated
                        if student_profile.teacher != teacher_profile:
                            student_profile.teacher = teacher_profile
                            student_profile.save()
                            assignments_made += 1
                            # Optional: self.stdout.write(self.style.SUCCESS(f'Assigned {teacher_profile.full_name} to {student_profile.name}'))
                        
                    except Teacher.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f'Teacher profile not found for Usuario: {teacher_usuario.nombre}. Cannot assign student {student_profile.name}.'
                        ))
                        unassigned_students += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
                        unassigned_students += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f'Missing student_profile or teacher_usuario for enrollment (Student: {student_profile.name if student_profile else 'N/A'}, Teacher: {teacher_usuario.nombre if teacher_usuario else 'N/A'}).'
                    ))
                    unassigned_students += 1

            self.stdout.write(self.style.SUCCESS(
                f'Finished student-teacher assignment. Assignments made: {assignments_made}. Students unassigned due to missing profiles: {unassigned_students}.'
            ))
