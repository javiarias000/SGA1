from django.db import migrations


FUNCIONES_INICIALES = [
    ('Director de Área', 'Responsable académico de un área de especialidad.'),
    ('Tutor de Curso', 'Docente tutor asignado a un nivel/paralelo.'),
    ('Coordinador Académico', 'Coordinación general de la planificación académica.'),
]


def seed_funciones(apps, schema_editor):
    Funcion = apps.get_model('teachers', 'Funcion')
    for nombre, descripcion in FUNCIONES_INICIALES:
        Funcion.objects.get_or_create(nombre=nombre, defaults={'descripcion': descripcion})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0004_funcion_docentefuncion'),
    ]

    operations = [
        migrations.RunPython(seed_funciones, noop),
    ]
