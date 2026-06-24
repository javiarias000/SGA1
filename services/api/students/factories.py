import factory
from factory.django import DjangoModelFactory
from students.models import Student
from users.models import Usuario
from faker import Faker

fake = Faker('es_ES')


# Esta es una re-exportación desde users.factories
from users.factories import StudentFactory

__all__ = ['StudentFactory']
