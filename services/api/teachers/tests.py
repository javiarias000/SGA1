import pytest
from teachers.models import Teacher, TeacherSubject
from users.models import Usuario
from users.factories import UsuarioFactory
from subjects.factories import SubjectFactory


class TestTeacherModel:
    """Tests para el modelo Teacher."""

    @pytest.mark.django_db
    def test_teacher_create(self, teacher_user):
        """Test crear Teacher."""
        assert teacher_user.pk is not None
        assert teacher_user.usuario is not None
        assert teacher_user.usuario.rol == Usuario.Rol.DOCENTE

    @pytest.mark.django_db(transaction=True)
    def test_teacher_specialization(self, db, teacher_usuario):
        """Test campo specialization."""
        teacher, _ = Teacher.objects.get_or_create(usuario=teacher_usuario)
        teacher.specialization = "Violin"
        teacher.save()
        assert teacher.specialization == "Violin"

    @pytest.mark.django_db
    def test_teacher_str(self, teacher_user):
        """Test representación string."""
        assert str(teacher_user) is not None

    @pytest.mark.django_db
    def test_teacher_created_at(self, teacher_user):
        """Test que created_at se asigna."""
        assert teacher_user.created_at is not None

    @pytest.mark.django_db
    def test_teacher_subjects_relationship(self, teacher_user):
        """Test relación muchos-a-muchos con Subject."""
        subject1 = SubjectFactory(name="Piano")
        subject2 = SubjectFactory(name="Violin")

        teacher_user.subjects.add(subject1, subject2)
        assert teacher_user.subjects.count() == 2
        assert subject1 in teacher_user.subjects.all()
        assert subject2 in teacher_user.subjects.all()

    @pytest.mark.django_db(transaction=True)
    def test_teacher_subject_through_model(self, db, teacher_usuario):
        """Test modelo through TeacherSubject."""
        teacher, _ = Teacher.objects.get_or_create(usuario=teacher_usuario)
        subject = SubjectFactory()

        ts = TeacherSubject.objects.create(teacher=teacher, subject=subject)
        assert ts.pk is not None
        assert ts.teacher == teacher
        assert ts.subject == subject

    @pytest.mark.django_db(transaction=True)
    def test_teacher_subject_unique_together(self, db, teacher_usuario):
        """Test constraint unique_together (teacher, subject)."""
        teacher, _ = Teacher.objects.get_or_create(usuario=teacher_usuario)
        subject = SubjectFactory()

        TeacherSubject.objects.create(teacher=teacher, subject=subject)
        with pytest.raises(Exception):  # IntegrityError
            TeacherSubject.objects.create(teacher=teacher, subject=subject)

    @pytest.mark.django_db(transaction=True)
    def test_multiple_teachers(self, db):
        """Test crear múltiples teachers."""
        usuarios = [UsuarioFactory(rol=Usuario.Rol.DOCENTE) for _ in range(3)]
        teachers = [Teacher.objects.get_or_create(usuario=u)[0] for u in usuarios]
        assert len(teachers) == 3
        assert all(t.pk is not None for t in teachers)


@pytest.mark.django_db
class TestTeacherMethods:
    """Tests para métodos y propiedades de Teacher."""

    def test_full_name_with_usuario(self):
        """full_name retorna nombre del usuario."""
        usuario = UsuarioFactory(nombre="Prof. García", rol=Usuario.Rol.DOCENTE)
        teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
        assert teacher.full_name == "Prof. García"

    def test_full_name_without_usuario(self):
        """full_name retorna default cuando no hay usuario."""
        teacher = Teacher.objects.create(usuario=None)
        assert teacher.full_name == "Docente sin nombre"

    def test_phone_with_usuario(self):
        """phone retorna phone del usuario."""
        usuario = UsuarioFactory(rol=Usuario.Rol.DOCENTE, phone="0991234567")
        teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
        assert teacher.phone == "0991234567"

    def test_phone_without_usuario(self):
        """phone retorna string vacío sin usuario."""
        teacher = Teacher.objects.create(usuario=None)
        assert teacher.phone == ""

    def test_str_representation(self):
        """__str__ retorna full_name."""
        usuario = UsuarioFactory(nombre="Test Docente", rol=Usuario.Rol.DOCENTE)
        teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
        assert str(teacher) == "Test Docente"

    def test_teacher_subject_str(self):
        """TeacherSubject.__str__ retorna formato correcto."""
        usuario = UsuarioFactory(nombre="Prof. Piano", rol=Usuario.Rol.DOCENTE)
        teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
        subject = SubjectFactory(name="Piano")
        ts = TeacherSubject.objects.create(teacher=teacher, subject=subject)
        assert "Prof. Piano" in str(ts)
        assert "Piano" in str(ts)

    def test_get_total_students(self):
        """get_total_students retorna 0 sin estudiantes asignados."""
        usuario = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
        assert teacher.get_total_students() == 0

    def test_get_total_classes(self):
        """get_total_classes retorna 0 sin actividades."""
        usuario = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        teacher, _ = Teacher.objects.get_or_create(usuario=usuario)
        assert teacher.get_total_classes() == 0
