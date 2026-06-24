from django.core.management.base import BaseCommand
from teachers.models import Teacher
from classes.models import Clase

class Command(BaseCommand):
    help = 'Creates default classes for teachers who have students but no classes.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to create default classes...'))

        teachers = Teacher.objects.all()
        for teacher in teachers:
            if teacher.students.count() > 0 and teacher.clases_teoricas.count() == 0:
                self.stdout.write(self.style.WARNING(f'Teacher {teacher.full_name} has students but no classes.'))
                if teacher.subjects.count() > 0:
                    self.stdout.write(self.style.SUCCESS(f'Teacher {teacher.full_name} has {teacher.subjects.count()} subjects. Creating default classes...'))
                    for subject in teacher.subjects.all():
                        clase, created = Clase.objects.get_or_create(
                            teacher=teacher,
                            subject=subject,
                            defaults={'name': f'{subject.name} - {teacher.full_name}'}
                        )
                        if created:
                            self.stdout.write(self.style.SUCCESS(f'Created class {clase.name}'))
                        else:
                            self.stdout.write(self.style.WARNING(f'Class {clase.name} already exists.'))
                else:
                    self.stdout.write(self.style.ERROR(f'Teacher {teacher.full_name} has no subjects assigned. Cannot create classes.'))

        self.stdout.write(self.style.SUCCESS('Default class creation finished.'))