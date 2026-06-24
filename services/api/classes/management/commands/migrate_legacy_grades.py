from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from classes.models import Grade, Calificacion, Enrollment, Clase
from students.models import Student
from subjects.models import Subject
from users.models import Usuario


class Command(BaseCommand):
    help = 'Migrates data from legacy Grade model to new Calificacion model.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting migration of legacy Grade records...'))

        total_migrated = 0
        total_skipped = 0

        with transaction.atomic():
            for legacy_grade in Grade.objects.all():
                student_obj = legacy_grade.student
                subject_obj = legacy_grade.subject

                if not student_obj or not student_obj.usuario:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping Grade ID {legacy_grade.id}: Student or associated Usuario not found for '{student_obj}'. Name: {student_obj.name}"
                    ))
                    total_skipped += 1
                    continue

                if not subject_obj:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping Grade ID {legacy_grade.id}: Subject not found for student '{student_obj.name}'."
                    ))
                    total_skipped += 1
                    continue
                
                # Try to find a Clase that matches the subject
                # This assumes a student enrolls in a Clase for a specific subject
                # If a student has multiple enrollments for the same subject (e.g., different classes),
                # this might pick one, which might not be perfectly accurate.
                # Prioritize active enrollments.
                enrollments = Enrollment.objects.filter(
                    estudiante=student_obj.usuario,
                    clase__subject=subject_obj
                ).order_by('-estado', '-date_enrolled') # Active first, then newest

                if not enrollments.exists():
                    self.stdout.write(self.style.WARNING(
                        f"Skipping Grade ID {legacy_grade.id}: No matching active Enrollment found "
                        f"for student '{student_obj.name}' and subject '{subject_obj.name}'. "
                        f"Attempting to create a dummy Enrollment."
                    ))
                    # Attempt to create a dummy Enrollment if none exists for this student/subject
                    # This requires finding a Clase for the subject, or creating one.
                    clase_for_subject = Clase.objects.filter(subject=subject_obj).first()
                    if not clase_for_subject:
                        # Fallback: Create a dummy Clase if no existing one for the subject
                        self.stdout.write(self.style.WARNING(
                            f"Creating dummy Clase for Subject '{subject_obj.name}' to facilitate Enrollment."
                        ))
                        clase_for_subject = Clase.objects.create(
                            name=f"Dummy Clase for {subject_obj.name}",
                            subject=subject_obj,
                            ciclo_lectivo='2025-2026', # Default cycle
                            active=False, # Mark as inactive dummy
                        )

                    enrollment, created_enrollment = Enrollment.objects.get_or_create(
                        estudiante=student_obj.usuario,
                        clase=clase_for_subject,
                        defaults={
                            'estado': 'ACTIVO', # Assume active for migration purposes
                            'docente': clase_for_subject.docente_base # Use base teacher of dummy clase
                        }
                    )
                    if created_enrollment:
                        self.stdout.write(self.style.NOTICE(
                            f"Created Enrollment ID {enrollment.id} for student '{student_obj.name}' in '{clase_for_subject.name}'."
                        ))
                else:
                    enrollment = enrollments.first()
                
                # Check for existing Calificacion to avoid duplicates
                if Calificacion.objects.filter(
                    inscripcion=enrollment,
                    fecha=legacy_grade.date,
                    descripcion=f"{legacy_grade.get_period_display()} - {legacy_grade.comments or ''}".strip()
                ).exists():
                    self.stdout.write(self.style.NOTICE(
                        f"Calificacion already exists for Grade ID {legacy_grade.id}. Skipping duplicate."
                    ))
                    total_skipped += 1
                    continue

                try:
                    Calificacion.objects.create(
                        inscripcion=enrollment,
                        descripcion=f"{legacy_grade.get_period_display()} - {legacy_grade.comments or ''}".strip(),
                        nota=legacy_grade.score,
                        fecha=legacy_grade.date,
                    )
                    total_migrated += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error migrating Grade ID {legacy_grade.id} for student '{student_obj.name}': {e}"
                    ))
                    total_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Migration of legacy Grade records completed. Total migrated: {total_migrated}, Total skipped: {total_skipped}."
        ))

