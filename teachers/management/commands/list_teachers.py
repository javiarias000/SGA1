from django.core.management.base import BaseCommand
from teachers.models import Teacher

class Command(BaseCommand):
    help = 'Lists the full names of all teachers in the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Listing all teacher names:'))
        
        teachers = Teacher.objects.all().order_by('full_name')

        if not teachers.exists():
            self.stdout.write(self.style.WARNING('No teachers found in the database.'))
            return

        for teacher in teachers:
            self.stdout.write(f"- {teacher.full_name}")
