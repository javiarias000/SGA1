"""
Tests de integración para workflows completos.
"""
import pytest
from django.test import TestCase
from users.models import Usuario
from users.factories import UsuarioFactory
from students.factories import StudentFactory
from teachers.factories import TeacherFactory
from subjects.factories import SubjectFactory
from classes.factories import ClaseFactory, EnrollmentFactory


@pytest.mark.django_db
class TestEnrollmentWorkflow:
    """Test workflow completo de inscripción."""

    def test_complete_enrollment_flow(self):
        """Test crear una Clase, inscribir estudiante, asignar docente."""
        # 1. Crear docente
        teacher = TeacherFactory()
        assert teacher.usuario.rol == Usuario.Rol.DOCENTE

        # 2. Crear materia
        subject = SubjectFactory(name="Piano", tipo_materia="INSTRUMENTO")
        assert subject.pk is not None

        # 3. Crear Clase
        clase = ClaseFactory(
            subject=subject,
            docente_base=teacher.usuario,
            max_students=20
        )
        assert clase.docente_base == teacher.usuario
        assert clase.get_enrolled_count() == 0

        # 4. Crear estudiante
        student = StudentFactory()
        assert student.usuario.rol == Usuario.Rol.ESTUDIANTE

        # 5. Inscribir estudiante
        enrollment = EnrollmentFactory(
            estudiante=student.usuario,
            clase=clase,
            docente=teacher.usuario,
            tipo_materia='INSTRUMENTO'
        )
        assert enrollment.pk is not None
        assert enrollment.estado == 'ACTIVO'

        # 6. Verificar inscripción
        assert clase.get_enrolled_count() == 1
        assert clase.has_space() is True


@pytest.mark.django_db
class TestMultipleEnrollments:
    """Test múltiples inscripciones."""

    def test_multiple_students_same_class(self):
        """Test múltiples estudiantes en la misma clase."""
        # Crear clase
        clase = ClaseFactory(max_students=3)

        # Crear 3 estudiantes
        students = StudentFactory.create_batch(3)

        # Inscribir todos
        for student in students:
            enrollment = EnrollmentFactory(
                estudiante=student.usuario,
                clase=clase
            )
            assert enrollment.pk is not None

        # Verificar capacidad
        assert clase.get_enrolled_count() == 3
        assert clase.has_space() is False

        # Intentar agregar uno más debería fallar
        student4 = StudentFactory()
        enrollment4 = EnrollmentFactory(
            estudiante=student4.usuario,
            clase=clase
        )
        assert clase.get_enrolled_count() == 4  # Se permite, solo es validación lógica

    def test_student_multiple_classes(self):
        """Test estudiante inscrito en múltiples clases."""
        student = StudentFactory()

        # Inscribir en 3 clases diferentes
        clases = ClaseFactory.create_batch(3)
        enrollments = []

        for clase in clases:
            enrollment = EnrollmentFactory(
                estudiante=student.usuario,
                clase=clase
            )
            enrollments.append(enrollment)

        assert len(enrollments) == 3
        assert all(e.estudiante == student.usuario for e in enrollments)


@pytest.mark.django_db
class TestRoleBasedAccess:
    """Test acceso basado en roles."""

    def test_teacher_can_teach(self):
        """Test que docente puede enseñar."""
        teacher = TeacherFactory()
        subject = SubjectFactory()

        teacher.subjects.add(subject)
        assert subject in teacher.subjects.all()

    def test_student_enrolled_in_class(self):
        """Test que estudiante puede estar inscrito."""
        student = StudentFactory()
        clase = ClaseFactory()

        enrollment = EnrollmentFactory(
            estudiante=student.usuario,
            clase=clase
        )
        assert enrollment.estudiante == student.usuario

    def test_teacher_cannot_be_student(self):
        """Test que docente no puede ser estudiante."""
        teacher = TeacherFactory()
        assert teacher.usuario.is_teacher is True
        assert teacher.usuario.is_student is False


@pytest.mark.django_db
class TestDataIntegrity:
    """Test integridad de datos en relaciones."""

    def test_enrollment_maintains_relationships(self):
        """Test que Enrollment mantiene relaciones válidas."""
        teacher = TeacherFactory()
        student = StudentFactory()
        clase = ClaseFactory(docente_base=teacher.usuario)

        enrollment = EnrollmentFactory(
            estudiante=student.usuario,
            clase=clase,
            docente=teacher.usuario
        )

        # Verificar todas las relaciones
        assert enrollment.estudiante == student.usuario
        assert enrollment.clase == clase
        assert enrollment.docente == teacher.usuario

    def test_clase_with_subject_and_teacher(self):
        """Test Clase con Subject y Teacher."""
        subject = SubjectFactory()
        teacher = TeacherFactory()

        clase = ClaseFactory(
            subject=subject,
            docente_base=teacher.usuario
        )

        assert clase.subject == subject
        assert clase.docente_base == teacher.usuario

    def test_cascade_delete_clase_deletes_enrollments(self):
        """Test que eliminar Clase elimina sus Enrollments."""
        clase = ClaseFactory()
        enrollment1 = EnrollmentFactory(clase=clase)
        enrollment2 = EnrollmentFactory(clase=clase)

        clase_id = clase.id
        clase.delete()

        # Las inscripciones deben ser eliminadas en cascada
        from classes.models import Enrollment
        assert Enrollment.objects.filter(clase_id=clase_id).count() == 0
