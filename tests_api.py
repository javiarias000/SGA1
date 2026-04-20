"""
Tests para API REST y GraphQL endpoints.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from users.factories import UsuarioFactory, UserFactory
from users.models import Usuario
from students.factories import StudentFactory
from teachers.factories import TeacherFactory
from subjects.factories import SubjectFactory
from classes.factories import ClaseFactory


@pytest.mark.django_db
class TestTokenAuth:
    """Tests para autenticación con tokens."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_token_auth_with_valid_credentials(self):
        """Test obtener token con credenciales válidas."""
        # Crear usuario Django
        auth_user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Hacer request al endpoint de token
        response = self.client.post(
            reverse('api_token_auth'),
            {'username': 'testuser', 'password': 'testpass123'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert response.data['token'] is not None

    def test_token_auth_with_invalid_credentials(self):
        """Test obtener token con credenciales inválidas."""
        response = self.client.post(
            reverse('api_token_auth'),
            {'username': 'invalid', 'password': 'invalid'},
            format='json'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED
        ]

    def test_authenticated_request_with_token(self):
        """Test request autenticado con token."""
        auth_user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        token = Token.objects.create(user=auth_user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Hacer request protegido (ejemplo: si existe alguno)
        # response = self.client.get('/api/some-protected-endpoint/')
        # assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestGraphQLQueries:
    """Tests para GraphQL queries."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_graphql_endpoint_accessible(self):
        """Test que endpoint GraphQL es accesible."""
        response = self.client.get('/graphql/')
        # En GraphiQL mode
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_graphql_query_usuarios(self):
        """Test query para listar usuarios."""
        # Crear algunos usuarios
        UsuarioFactory.create_batch(3)

        query = """
        {
            usuarios {
                id
                nombre
                rol
            }
        }
        """

        response = self.client.post(
            '/graphql/',
            {'query': query},
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verificar que no hay errores
        if 'errors' in data:
            assert data['errors'] is None or len(data['errors']) == 0


@pytest.mark.django_db
class TestAPIPermissions:
    """Tests para permisos en API."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_unauthenticated_access(self):
        """Test acceso sin autenticación a endpoints protegidos."""
        # Si hay algún endpoint protegido, testear que rechaza sin auth
        # response = self.client.get('/api/protected/')
        # assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_teacher_permissions(self):
        """Test que docentes tienen permisos correctos."""
        teacher = TeacherFactory()
        auth_user = UserFactory()
        teacher.usuario.auth_user = auth_user
        teacher.usuario.save()

        token = Token.objects.create(user=auth_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Test acceso a recursos de docente
        # assert permission check works


@pytest.mark.django_db
class TestAPIDataValidation:
    """Tests para validación de datos en API."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_invalid_json_handling(self):
        """Test manejo de JSON inválido."""
        response = self.client.post(
            reverse('api_token_auth'),
            'invalid json',
            content_type='application/json'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        ]

    def test_missing_required_fields(self):
        """Test validación de campos requeridos."""
        response = self.client.post(
            reverse('api_token_auth'),
            {},  # Sin username ni password
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCORSHeaders:
    """Tests para CORS headers."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_cors_headers_present(self):
        """Test que CORS headers estén presentes."""
        response = self.client.get(
            reverse('api_token_auth'),
            HTTP_ORIGIN='https://example.com'
        )

        # Los headers CORS deben estar presentes en producción
        # assert 'access-control-allow-origin' in response.headers or True


@pytest.mark.django_db
class TestErrorHandling:
    """Tests para manejo de errores."""

    def setup_method(self):
        """Setup antes de cada test."""
        self.client = APIClient()

    def test_404_not_found(self):
        """Test 404 Not Found."""
        response = self.client.get('/api/non-existent-endpoint/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed(self):
        """Test 405 Method Not Allowed."""
        # GET en endpoint que solo acepta POST
        response = self.client.get(
            reverse('api_token_auth')
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
