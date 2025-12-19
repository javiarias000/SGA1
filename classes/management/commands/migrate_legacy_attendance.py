from django.core.management.base import BaseCommand
from django.db import transaction

from classes.models import Attendance, Asistencia, Enrollment
from students.models import Student
from users.models import Usuario


class Command(BaseCommand):
    help = 'Migrates data from legacy Attendance model to new Asistencia model.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting migration of legacy Attendance records...'))

        total_migrated = 0
        total_skipped = 0

        with transaction.atomic():
            for legacy_attendance in Attendance.objects.all():
                student_obj = legacy_attendance.student

                if not student_obj or not student_obj.usuario:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping Attendance ID {legacy_attendance.id}: Student or associated Usuario not found for '{student_obj}'. Name: {student_obj.name}"
                    ))
                    total_skipped += 1
                    continue
                
                # Try to find an Enrollment for the student on this date.
                # Since legacy Attendance doesn't link to a specific class, we'll try to find any active enrollment.
                enrollments = Enrollment.objects.filter(
                    estudiante=student_obj.usuario,
                    estado='ACTIVO', # Only consider active enrollments
                ).order_by('date_enrolled') # Pick the oldest active enrollment if multiple exist

                if not enrollments.exists():
                    self.stdout.write(self.style.WARNING(
                        f"Skipping Attendance ID {legacy_attendance.id}: No active Enrollment found "
                        f"for student '{student_obj.name}' on {legacy_attendance.date}. "
                    ))
                    total_skipped += 1
                    continue
                
                enrollment = enrollments.first() # Pick the first active enrollment
                if enrollments.count() > 1:
                    self.stdout.write(self.style.WARNING(
                        f"Multiple active Enrollments found for student '{student_obj.name}' on {legacy_attendance.date}. "
                        f"Assigning to Enrollment ID {enrollment.id} (Clase: {enrollment.clase.name})."
                    ))
                
                # Check for existing Asistencia to avoid duplicates
                if Asistencia.objects.filter(
                    inscripcion=enrollment,
                    fecha=legacy_attendance.date,
                ).exists():
                    self.stdout.write(self.style.NOTICE(
                        f"Asistencia already exists for Attendance ID {legacy_attendance.id} and date {legacy_attendance.date}. Skipping duplicate."
                    ))
                    total_skipped += 1
                    continue


                try:
                    Asistencia.objects.create(
                        inscripcion=enrollment,
                        fecha=legacy_attendance.date,
                        estado=legacy_attendance.status, # Assuming status names match
                        observacion=legacy_attendance.notes,
                    )
                    total_migrated += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error migrating Attendance ID {legacy_attendance.id} for student '{student_obj.name}': {e}"
                    ))
                    total_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Migration of legacy Attendance records completed. Total migrated: {total_migrated}, Total skipped: {total_skipped}."
        ))
