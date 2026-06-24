import factory
from factory.django import DjangoModelFactory
from subjects.models import Subject
from faker import Faker

fake = Faker('es_ES')


class SubjectFactory(DjangoModelFactory):
    """Factory para Subject."""
    class Meta:
        model = Subject

    name = factory.Sequence(lambda n: f"{fake.word()} {n}")
    description = factory.LazyAttribute(lambda obj: fake.sentence())
    tipo_materia = factory.Iterator([choice[0] for choice in Subject.TIPO_MATERIA_CHOICES])
