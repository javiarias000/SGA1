from django.core.management.base import BaseCommand
from django.db import transaction
from teachers.models import Teacher, TeacherSubject
from subjects.models import Subject
from classes.models import Clase # Assuming Clase model has docente_base and subject fields

class Command(BaseCommand):
    help = 'Assigns subjects to teachers based on the classes they are assigned to.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting subject assignment to teachers...'))

        with transaction.atomic():
            # Clear existing TeacherSubject relationships if you want to rebuild cleanly
            # TeacherSubject.objects.all().delete()
            # self.stdout.write(self.style.WARNING('Cleared existing TeacherSubject relationships (optional step).'))

            teachers_assigned_subjects = 0
            
            # Iterate through all classes that have a teacher assigned
            # We need to consider both Clase.docente_base and Enrollment.docente
            # For simplicity, let's focus on Clase.docente_base first,
            # as it directly links a class to a specific teacher's Usuario profile.
            
            # Find all distinct (teacher_usuario, subject) pairs from Clase objects
            # where the class has a docente_base
            classes_with_teachers = Clase.objects.filter(docente_base__isnull=False).select_related('docente_base', 'subject').distinct()

            for clase in classes_with_teachers:
                docente_usuario = clase.docente_base
                subject = clase.subject

                if docente_usuario and subject:
                    # Find the Teacher profile associated with this Usuario
                    teacher_profile = Teacher.objects.filter(usuario=docente_usuario).first()

                    if teacher_profile:
                        # Get or create the TeacherSubject entry
                        teacher_subject, created = TeacherSubject.objects.get_or_create(
                            teacher=teacher_profile,
                            subject=subject
                        )
                        if created:
                            teachers_assigned_subjects += 1
                            self.stdout.write(self.style.SUCCESS(
                                f'Assigned {subject.name} to {teacher_profile.full_name}'
                            ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'Teacher profile not found for Usuario: {docente_usuario.nombre} (Clase: {clase.name})'
                        ))
                
            self.stdout.write(self.style.SUCCESS(
                f'Finished subject assignment. Total new assignments: {teachers_assigned_subjects}'
            ))
