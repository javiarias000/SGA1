from django.core.management.base import BaseCommand
from students.models import Student

class Command(BaseCommand):
    help = 'Extracts cleaned student names from the database and prints them to stdout.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Extracting cleaned student names...'))

        for s in Student.objects.all():
            cleaned_name = s.name.rsplit(' - ', 1)[0].strip()
            self.stdout.write(cleaned_name) # Print directly to stdout
        self.stdout.write(self.style.SUCCESS('Extraction finished.'))
