import re
from django.core.management.base import BaseCommand
from students.models import Student
from classes.models import GradeLevel

class Command(BaseCommand):
    help = 'Migrates data from the old grade_deprecated CharField to the new grade_level ForeignKey.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting grade migration...'))
        
        # Get all students with a value in the old field but not in the new one
        students_to_migrate = Student.objects.filter(
            grade_deprecated__isnull=False,
            grade_level__isnull=True
        ).exclude(grade_deprecated='')

        if not students_to_migrate.exists():
            self.stdout.write(self.style.WARNING('No students to migrate.'))
            return

        self.stdout.write(f'Found {students_to_migrate.count()} students to migrate.')

        created_count = 0
        updated_count = 0

        for student in students_to_migrate:
            old_grade_str = student.grade_deprecated.strip()
            
            # Simple parsing: assumes the last word is the section/parallel
            parts = old_grade_str.split()
            level_str = " ".join(parts[:-1])
            section_str = parts[-1]

            # A more robust regex could be used if formats vary a lot.
            # This is a basic attempt to normalize level names.
            # Example: '1ro Bachillerato' -> '1ro Bachillerato'
            # Example: '2do Básica' -> '2do Básica'
            
            if not level_str:
                level_str = section_str
                section_str = "A" # Default section if only a level is found
            
            # Find a matching level from choices
            level_key = None
            for key, name in GradeLevel.LEVEL_CHOICES:
                if name.lower() in level_str.lower() or key.lower() in level_str.lower():
                    level_key = key
                    break
            
            if not level_key:
                self.stdout.write(self.style.ERROR(f'Could not parse level from "{old_grade_str}" for student {student.name}. Skipping.'))
                continue

            try:
                grade_level, created = GradeLevel.objects.get_or_create(
                    level=level_key,
                    section=section_str
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f'CREATED GradeLevel: {grade_level}'))
                    created_count += 1
                
                student.grade_level = grade_level
                student.save()
                updated_count += 1
                self.stdout.write(f'Updated student {student.name} with grade {grade_level}')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing student {student.name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\nMigration complete!'))
        self.stdout.write(f'GradeLevels created: {created_count}')
        self.stdout.write(f'Students updated: {updated_count}')
