import pytest
from django.test import TestCase
from students.models import Student
from users.models import Usuario
from users.factories import UsuarioFactory
from subjects.factories import SubjectFactory


class TestStudentModel:
    """Tests para el modelo Student."""

    @pytest.mark.django_db
    def test_student_create(self, student_user):
        """Test crear Student."""
        assert student_user.pk is not None
        assert student_user.usuario is not None

    @pytest.mark.django_db(transaction=True)
    def test_student_name_property(self, db):
        """Test propiedad name."""
        usuario = UsuarioFactory(nombre="Carlos López", rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        assert student.name == "Carlos López"

    @pytest.mark.django_db(transaction=True)
    def test_student_name_without_usuario(self, db):
        """Test name cuando Usuario es None."""
        student = Student.objects.create(usuario=None)
        assert student.name == "Estudiante sin nombre"

    @pytest.mark.django_db
    def test_student_str(self, student_user):
        """Test representación string."""
        assert str(student_user) is not None

    @pytest.mark.django_db(transaction=True)
    def test_student_parent_info(self, db):
        """Test información de padres."""
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        student.parent_name = "María García"
        student.parent_email = "maria@example.com"
        student.parent_phone = "1234567890"
        student.save()
        assert student.parent_name == "María García"
        assert student.parent_email == "maria@example.com"

    @pytest.mark.django_db
    def test_student_registration_code_auto_generate(self, student_user):
        """Test que registration_code se genera automáticamente."""
        assert student_user.registration_code is not None
        assert len(student_user.registration_code) == 36  # UUID length

    @pytest.mark.django_db
    def test_student_active_default(self, student_user):
        """Test que active es True por defecto."""
        assert student_user.active is True

    @pytest.mark.django_db
    def test_student_created_at(self, student_user):
        """Test que created_at se asigna."""
        assert student_user.created_at is not None

    @pytest.mark.django_db(transaction=True)
    def test_multiple_students(self, db):
        """Test crear múltiples students."""
        usuarios = [UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE) for _ in range(5)]
        students = [Student.objects.get_or_create(usuario=u)[0] for u in usuarios]
        assert len(students) == 5
        assert all(s.pk is not None for s in students)


@pytest.mark.django_db
class TestStudentMethods:
    """Tests para métodos del modelo Student."""

    def test_get_class_count_no_usuario(self):
        """get_class_count retorna 0 cuando no hay usuario."""
        student = Student.objects.create(usuario=None)
        assert student.get_class_count() == 0

    def test_get_class_count_with_enrollments(self):
        """get_class_count cuenta enrollments activos."""
        from classes.factories import ClaseFactory, EnrollmentFactory
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        clase = ClaseFactory()
        EnrollmentFactory(estudiante=usuario, clase=clase, estado='ACTIVO')
        assert student.get_class_count() == 1

    def test_get_subjects_no_usuario(self):
        """get_subjects retorna queryset vacío si no hay usuario."""
        student = Student.objects.create(usuario=None)
        from subjects.models import Subject
        assert list(student.get_subjects()) == []

    def test_get_subjects_with_enrollments(self):
        """get_subjects retorna materias del estudiante."""
        from classes.factories import ClaseFactory, EnrollmentFactory
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        subject = SubjectFactory(name="Piano Test")
        clase = ClaseFactory(subject=subject)
        EnrollmentFactory(estudiante=usuario, clase=clase, estado='ACTIVO')
        subjects = student.get_subjects()
        assert subject in subjects

    def test_can_take_subject(self):
        """can_take_subject siempre retorna True."""
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        subject = SubjectFactory()
        assert student.can_take_subject(subject) is True
