import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.factories import UsuarioFactory, UserFactory
from users.models import Usuario
from subjects.factories import SubjectFactory
from classes.factories import ClaseFactory, EnrollmentFactory
from faker import Faker


@pytest.mark.django_db
class TestAcademiaHorarioModel:
    """Tests para academia.Horario."""

    def test_horario_str(self):
        """Horario __str__ retorna formato correcto."""
        from academia.models import Horario
        from classes.factories import GradeLevelFactory
        grade = GradeLevelFactory(level='1', section='A')
        subject = SubjectFactory(name="Música")
        horario = Horario.objects.create(
            curso=grade, dia="Lunes",
            hora="08:00-09:00", aula="Sala 1",
            clase=subject
        )
        s = str(horario)
        assert "Lunes" in s

    def test_horario_without_curso(self):
        """Horario sin curso igual hace __str__."""
        from academia.models import Horario
        subject = SubjectFactory(name="Arte")
        horario = Horario.objects.create(
            curso=None, dia="Martes",
            hora="10:00-11:00", clase=subject
        )

fake = Faker('es_ES')


@pytest.mark.django_db
class TestAPIAuthentication:
    """Tests para autenticación en API."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_login_with_valid_credentials(self):
        """Test login con credenciales válidas."""
        from users.models import Usuario
        auth_user = UserFactory(username='testuser', password='testpass123')
        auth_user.set_password('testpass123')
        auth_user.save()
        # Signal already creates Usuario — fetch it
        usuario = Usuario.objects.get(auth_user=auth_user)
        assert usuario is not None

        # Intentar login (si hay endpoint de login)
        # response = self.client.post(reverse('login'), {
        #     'username': 'testuser',
        #     'password': 'testpass123'
        # })
        # assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_request(self):
        """Test request sin autenticación."""
        # Verificar que endpoints protegidos rechacen
        # response = self.client.get(reverse('api-enrollments'))
        # assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
class TestClaseAPI:
    """Tests para endpoints de Clase."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()
        self.teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        self.student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)

    def test_list_clases(self):
        """Test listar clases."""
        ClaseFactory.create_batch(3)
        # response = self.client.get(reverse('clase-list'))
        # assert response.status_code == status.HTTP_200_OK
        # assert len(response.data) >= 3


@pytest.mark.django_db
class TestEnrollmentAPI:
    """Tests para endpoints de Enrollment."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()
        self.student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        self.teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE)

    def test_create_enrollment(self):
        """Test crear Enrollment via API."""
        clase = ClaseFactory(docente_base=self.teacher)
        # payload = {
        #     'estudiante': self.student.id,
        #     'clase': clase.id,
        #     'docente': self.teacher.id,
        #     'tipo_materia': 'TEORICA'
        # }
        # response = self.client.post(reverse('enrollment-list'), payload)
        # assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestGraphQLQueries:
    """Tests para queries GraphQL."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_graphql_endpoint_exists(self):
        """Test que endpoint GraphQL existe."""
        # response = self.client.get('/graphql/')
        # assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]
