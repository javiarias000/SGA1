import factory
from factory.django import DjangoModelFactory
from classes.models import Clase, Enrollment, GradeLevel, Horario
from subjects.models import Subject
from users.models import Usuario
from users.factories import UsuarioFactory
from faker import Faker
from datetime import time, timedelta
from django.utils import timezone

fake = Faker('es_ES')


class GradeLevelFactory(DjangoModelFactory):
    """Factory para GradeLevel."""
    class Meta:
        model = GradeLevel

    level = factory.Iterator([choice[0] for choice in GradeLevel.LEVEL_CHOICES])
    section = factory.LazyAttribute(lambda obj: fake.word().upper())


class ClaseFactory(DjangoModelFactory):
    """Factory para Clase."""
    class Meta:
        model = Clase

    name = factory.LazyAttribute(lambda obj: f"Clase de {fake.word()}")
    subject = factory.SubFactory('subjects.factories.SubjectFactory')
    ciclo_lectivo = '2025-2026'
    paralelo = factory.LazyAttribute(lambda obj: fake.word().upper())
    description = factory.LazyAttribute(lambda obj: fake.sentence())
    schedule = factory.LazyAttribute(lambda obj: '9:00-10:00')
    room = factory.LazyAttribute(lambda obj: f"Aula {fake.numerify('##')}")
    max_students = 30
    active = True
    grade_level = factory.SubFactory(GradeLevelFactory)
    docente_base = factory.SubFactory(UsuarioFactory, rol=Usuario.Rol.DOCENTE)


class EnrollmentFactory(DjangoModelFactory):
    """Factory para Enrollment."""
    class Meta:
        model = Enrollment

    estudiante = factory.SubFactory(UsuarioFactory, rol=Usuario.Rol.ESTUDIANTE)
    clase = factory.SubFactory(ClaseFactory)
    docente = factory.SubFactory(UsuarioFactory, rol=Usuario.Rol.DOCENTE)
    estado = Enrollment.Estado.ACTIVO
    tipo_materia = factory.Iterator([choice[0] for choice in [
        ('TEORICA', 'Teórica (Grupal)'),
        ('AGRUPACION', 'Agrupación (Ensamble)'),
        ('INSTRUMENTO', 'Instrumento (Individual)')
    ]])


class HorarioFactory(DjangoModelFactory):
    """Factory para Horario."""
    class Meta:
        model = Horario

    clase = factory.SubFactory(ClaseFactory)
    dia_semana = factory.Iterator([choice[0] for choice in [
        ('Lunes', 'Lunes'), ('Martes', 'Martes'), ('Miércoles', 'Miércoles'),
        ('Jueves', 'Jueves'), ('Viernes', 'Viernes')
    ]])
    hora_inicio = time(9, 0)
    hora_fin = time(10, 0)
