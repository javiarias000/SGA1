import factory
from factory.django import DjangoModelFactory
from teachers.models import Teacher
from users.models import Usuario
from users.factories import UsuarioFactory
from faker import Faker

fake = Faker('es_ES')


class TeacherFactory(DjangoModelFactory):
	"""Factory para Teacher (perfil de docente)."""
	class Meta:
		model = Teacher

	usuario = factory.SubFactory(
		UsuarioFactory,
		rol=Usuario.Rol.DOCENTE
	)
	specialization = factory.LazyAttribute(lambda obj: fake.word())
	active = True


__all__ = ['TeacherFactory']
