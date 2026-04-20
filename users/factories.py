import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from users.models import Usuario, Profile
from faker import Faker
import uuid

fake = Faker('es_ES')


class UserFactory(DjangoModelFactory):
    """Factory para Django auth.User."""
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: fake.email())
    first_name = factory.LazyAttribute(lambda obj: fake.first_name())
    last_name = factory.LazyAttribute(lambda obj: fake.last_name())
    is_active = True


class UsuarioFactory(DjangoModelFactory):
    """Factory para Usuario (dominio académico unificado)."""
    class Meta:
        model = Usuario

    nombre = factory.LazyAttribute(lambda obj: f"{fake.first_name()} {fake.last_name()}")
    rol = Usuario.Rol.PENDIENTE
    email = factory.LazyAttribute(lambda obj: f'usuario_{uuid.uuid4().hex[:8]}@test.com')
    phone = factory.LazyAttribute(lambda obj: fake.phone_number()[:20])
    cedula = factory.LazyAttribute(lambda obj: f'{uuid.uuid4().int % 10000000000:010d}')
    auth_user = None  # Opcional, se puede agregar con relación


class StudentFactory(DjangoModelFactory):
    """Factory para Student (perfil de estudiante)."""
    class Meta:
        model = 'students.Student'

    usuario = factory.SubFactory(
        UsuarioFactory,
        rol=Usuario.Rol.ESTUDIANTE
    )
    parent_name = factory.LazyAttribute(lambda obj: f"{fake.first_name()} {fake.last_name()}")
    parent_email = factory.LazyAttribute(lambda obj: fake.email())
    parent_phone = factory.LazyAttribute(lambda obj: fake.phone_number()[:20])
    active = True


class TeacherFactory(DjangoModelFactory):
    """Factory para Teacher (perfil de docente)."""
    class Meta:
        model = 'teachers.Teacher'

    usuario = factory.SubFactory(
        UsuarioFactory,
        rol=Usuario.Rol.DOCENTE
    )
    specialization = factory.LazyAttribute(lambda obj: fake.word())
