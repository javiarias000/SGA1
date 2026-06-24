from django.core.management.base import BaseCommand
from teachers.models import Teacher
from subjects.models import Subject

class Command(BaseCommand):
    help = 'Assigns all subjects to teachers who have students but no subjects.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to assign subjects to teachers...'))

        teachers = Teacher.objects.all()
        all_subjects = Subject.objects.all()

        for teacher in teachers:
            if teacher.students.count() > 0 and teacher.subjects.count() == 0:
                self.stdout.write(self.style.WARNING(f'Teacher {teacher.full_name} has students but no subjects. Assigning all subjects...'))
                teacher.subjects.add(*all_subjects)
                self.stdout.write(self.style.SUCCESS(f'Assigned {all_subjects.count()} subjects to {teacher.full_name}'))

        self.stdout.write(self.style.SUCCESS('Subject assignment finished.'))
