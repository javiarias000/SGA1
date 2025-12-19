from django.core.management.base import BaseCommand
from students.models import Student
from classes.models import Clase, Enrollment
from teachers.models import Teacher

class Command(BaseCommand):
    help = 'Enrolls students in classes based on their assigned teacher.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting student enrollment...'))

        students = Student.objects.all()
        for student in students:
            if student.teacher:
                classes_to_enroll = Clase.objects.filter(teacher=student.teacher)
                for clase in classes_to_enroll:
                    enrollment, created = Enrollment.objects.get_or_create(
                        student=student,
                        clase=clase
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Enrolled {student.name} in {clase.name}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'{student.name} is already enrolled in {clase.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Student {student.name} has no assigned teacher.'))

        self.stdout.write(self.style.SUCCESS('Student enrollment finished.'))
