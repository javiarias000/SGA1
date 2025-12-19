from django.core.management.base import BaseCommand
from subjects.models import Subject

class Command(BaseCommand):
    help = 'Adds a predefined list of subjects to the database.'

    def handle(self, *args, **options):
        subjects_data = [
            {'name': 'Acompañamiento', 'tipo_materia': 'OTRO'},
            {'name': 'Clarinete', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Complementario', 'tipo_materia': 'OTRO'},
            {'name': 'Conj. Inst', 'tipo_materia': 'AGRUPACION'},
            {'name': 'Contrabajo', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Flauta Traversa', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Guitarra', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Percusión', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Piano', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Saxofón', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Trombón', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Trompeta', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Viola', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Violonchelo', 'tipo_materia': 'INSTRUMENTO'},
            {'name': 'Violín', 'tipo_materia': 'INSTRUMENTO'},
        ]

        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=subject_data['name'],
                defaults={'tipo_materia': subject_data['tipo_materia']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created subject: '{subject.name}' with type '{subject.tipo_materia}'"))
            else:
                self.stdout.write(self.style.NOTICE(f"Subject '{subject.name}' already exists. Type: '{subject.tipo_materia}'"))

        self.stdout.write(self.style.SUCCESS('Finished adding subjects.'))
