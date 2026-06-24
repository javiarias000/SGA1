import os
import pytest
from django.conf import settings
from django.test import Client
from users.factories import UsuarioFactory, UserFactory
from users.models import Usuario
from subjects.factories import SubjectFactory
from classes.factories import ClaseFactory, GradeLevelFactory, EnrollmentFactory
from faker import Faker

fake = Faker('es_ES')


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Configure test database."""
    with django_db_blocker.unblock():
        pass


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def user(db):
    """Create test Usuario - unique per test."""
    return UsuarioFactory(rol=Usuario.Rol.PENDIENTE)


@pytest.fixture
def student_usuario(db):
    """Create test Student Usuario - unique per test."""
    return UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE, email=f"student_{fake.uuid4()}@test.com", nombre=f"Student {fake.uuid4()}")


@pytest.fixture
def student_user(transactional_db, student_usuario):
    """Create test Student with unique Usuario."""
    from students.models import Student
    student, _ = Student.objects.get_or_create(usuario=student_usuario)
    return student


@pytest.fixture
def teacher_usuario(db):
    """Create test Teacher Usuario - unique per test."""
    return UsuarioFactory(rol=Usuario.Rol.DOCENTE, email=f"teacher_{fake.uuid4()}@test.com")


@pytest.fixture
def teacher_user(transactional_db, teacher_usuario):
    """Create test Teacher with unique Usuario - function scoped."""
    from teachers.models import Teacher
    teacher, _ = Teacher.objects.get_or_create(usuario=teacher_usuario)
    return teacher


@pytest.fixture
def subject(db):
    """Create test Subject."""
    return SubjectFactory()


@pytest.fixture
def grade_level(db):
    """Create test GradeLevel."""
    return GradeLevelFactory()


@pytest.fixture
def clase(db, subject, teacher_usuario):
    """Create test Clase."""
    return ClaseFactory(subject=subject, docente_base=teacher_usuario)


@pytest.fixture
def enrollment(db, student_usuario, clase):
    """Create test Enrollment."""
    return EnrollmentFactory(
        estudiante=student_usuario,
        clase=clase,
        docente=clase.docente_base
    )


@pytest.fixture
def authenticated_client(client, user):
    """Authenticated test client with auth_user."""
    auth_user = UserFactory()
    user.auth_user = auth_user
    user.save()
    client.force_login(auth_user)
    return client


@pytest.fixture
def teacher_client(client, teacher_usuario):
    """Teacher authenticated client."""
    auth_user = UserFactory()
    teacher_usuario.auth_user = auth_user
    teacher_usuario.save()
    client.force_login(auth_user)
    return client


@pytest.fixture
def student_client(client, student_usuario):
    """Student authenticated client."""
    auth_user = UserFactory()
    student_usuario.auth_user = auth_user
    student_usuario.save()
    client.force_login(auth_user)
    return client
