"""
Carga los 11 niveles del conservatorio y la malla curricular por defecto.

Uso:
    python manage.py cargar_malla_default
    python manage.py cargar_malla_default --reset   # borra malla antes de cargar
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from subjects.models import Subject
from classes.models import GradeLevel, MallaCurricular


# ─── Materias por defecto ────────────────────────────────────────────────────

SUBJECTS_DEFAULT = [
    # (nombre, tipo)
    ('Instrumento',           'INSTRUMENTO'),
    ('Solfeo',                'TEORIA'),
    ('Ritmo y Movimiento',    'TEORIA'),
    ('Armonía',               'TEORIA'),
    ('Historia de la Música', 'TEORIA'),
    ('Lenguaje Musical',      'TEORIA'),
    ('Educación Musical',     'TEORIA'),
    ('Composición',           'TEORIA'),
    ('Agrupación Musical',    'AGRUPACION'),
    ('Orquesta',              'AGRUPACION'),
    ('Coro',                  'AGRUPACION'),
    ('Cámara',                'AGRUPACION'),
]

# ─── Malla curricular por ciclo ───────────────────────────────────────────────

# Formato: { ciclo: [(nombre_materia, obligatoria, orden), ...] }
MALLA_POR_CICLO = {
    'BASICA': [
        ('Instrumento',        True,  1),
        ('Solfeo',             True,  2),
        ('Ritmo y Movimiento', True,  3),
    ],
    'MEDIA': [
        ('Instrumento',        True,  1),
        ('Lenguaje Musical',   True,  2),
        ('Armonía',            True,  3),
        ('Agrupación Musical', True,  4),
    ],
    'SUPERIOR': [
        ('Instrumento',           True,  1),
        ('Armonía',               True,  2),
        ('Historia de la Música', True,  3),
        ('Agrupación Musical',    True,  4),
        ('Cámara',                False, 5),
    ],
    'BACHILLERATO': [
        ('Instrumento',           True,  1),
        ('Armonía',               True,  2),
        ('Historia de la Música', True,  3),
        ('Composición',           True,  4),
        ('Orquesta',              True,  5),
        ('Cámara',                False, 6),
    ],
}

# ─── Niveles por defecto ─────────────────────────────────────────────────────

NIVELES_DEFAULT = [
    # (level, section, ciclo)
    ('1',  'A', 'BASICA'),
    ('2',  'A', 'BASICA'),
    ('3',  'A', 'MEDIA'),
    ('4',  'A', 'MEDIA'),
    ('5',  'A', 'MEDIA'),
    ('6',  'A', 'SUPERIOR'),
    ('7',  'A', 'SUPERIOR'),
    ('8',  'A', 'SUPERIOR'),
    ('9',  'A', 'BACHILLERATO'),
    ('10', 'A', 'BACHILLERATO'),
    ('11', 'A', 'BACHILLERATO'),
]


class Command(BaseCommand):
    help = 'Carga materias, niveles y malla curricular por defecto.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina la malla existente antes de cargar los datos.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        reset = options['reset']

        if reset:
            MallaCurricular.objects.all().delete()
            self.stdout.write(self.style.WARNING('Malla curricular eliminada.'))

        # 1. Crear/actualizar materias
        subjects_map = {}
        for nombre, tipo in SUBJECTS_DEFAULT:
            subj, created = Subject.objects.get_or_create(
                name=nombre,
                defaults={'tipo_materia': tipo},
            )
            if created:
                self.stdout.write(f'  ✓ Materia creada: {nombre} ({tipo})')
            else:
                # Actualizar tipo si cambió
                if subj.tipo_materia != tipo:
                    subj.tipo_materia = tipo
                    subj.save()
            subjects_map[nombre] = subj

        # 2. Crear/actualizar niveles
        niveles_map = {}
        for level, section, ciclo in NIVELES_DEFAULT:
            nivel, created = GradeLevel.objects.get_or_create(
                level=level,
                section=section,
                defaults={'ciclo': ciclo},
            )
            if created:
                self.stdout.write(f'  ✓ Nivel creado: {nivel}')
            else:
                # Actualizar ciclo si cambió
                if nivel.ciclo != ciclo:
                    nivel.ciclo = ciclo
                    nivel.save()
            niveles_map[(level, section)] = nivel

        # 3. Poblar malla curricular
        created_count = 0
        for (level, section), nivel in niveles_map.items():
            ciclo = nivel.ciclo
            materias_ciclo = MALLA_POR_CICLO.get(ciclo, [])
            for nombre, obligatoria, orden in materias_ciclo:
                subj = subjects_map.get(nombre)
                if not subj:
                    continue
                entry, created = MallaCurricular.objects.get_or_create(
                    nivel=nivel,
                    subject=subj,
                    defaults={'obligatoria': obligatoria, 'orden': orden},
                )
                if created:
                    created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Malla cargada: {Subject.objects.count()} materias, '
            f'{GradeLevel.objects.count()} niveles, '
            f'{MallaCurricular.objects.count()} entradas en malla.'
        ))
