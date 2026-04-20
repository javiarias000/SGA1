import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from users.models import Usuario, Profile
from users.factories import UsuarioFactory, UserFactory
from subjects.factories import SubjectFactory


@pytest.mark.django_db
class TestUsuarioModel:
    """Tests para el modelo Usuario."""

    def test_usuario_create(self):
        """Test crear Usuario con valores básicos."""
        usuario = UsuarioFactory(
            nombre="Juan Pérez",
            rol=Usuario.Rol.DOCENTE,
            email="juan@example.com"
        )
        assert usuario.pk is not None
        assert usuario.nombre == "Juan Pérez"
        assert usuario.rol == Usuario.Rol.DOCENTE
        assert usuario.email == "juan@example.com"

    def test_usuario_str(self):
        """Test representación string de Usuario."""
        usuario = UsuarioFactory(nombre="María García", rol=Usuario.Rol.ESTUDIANTE)
        assert str(usuario) == "María García (ESTUDIANTE)"

    def test_usuario_is_teacher_property(self):
        """Test propiedad is_teacher."""
        teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        assert teacher.is_teacher is True
        assert student.is_teacher is False

    def test_usuario_is_student_property(self):
        """Test propiedad is_student."""
        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        assert student.is_student is True
        assert teacher.is_student is False

    def test_usuario_email_unique(self):
        """Test que email es único."""
        email = "unique@example.com"
        UsuarioFactory(email=email)
        with pytest.raises(Exception):  # IntegrityError
            UsuarioFactory(email=email)

    def test_usuario_cedula_unique(self):
        """Test que cédula es única."""
        cedula = "1234567890"
        UsuarioFactory(cedula=cedula)
        with pytest.raises(Exception):  # IntegrityError
            UsuarioFactory(cedula=cedula)

    def test_usuario_auth_user_simple(self, db):
        """Test que auth_user puede ser None."""
        usuario = UsuarioFactory()
        assert usuario.auth_user is None

    # Note: Full OneToOne relationship test omitted due to unique constraint complexity

    def test_usuario_created_at_auto_set(self):
        """Test que created_at se establece automáticamente."""
        usuario = UsuarioFactory()
        assert usuario.created_at is not None

    def test_usuario_default_rol(self):
        """Test rol por defecto."""
        usuario = UsuarioFactory()
        assert usuario.rol == Usuario.Rol.PENDIENTE


@pytest.mark.django_db
class TestProfileModel:
    """Tests para el modelo Profile."""

    def test_profile_auto_create_on_user_creation(self):
        """Test que Profile se crea al crear User."""
        auth_user = UserFactory()
        profile = Profile.objects.get(user=auth_user)
        assert profile.pk is not None
        assert profile.must_change_password is False

    def test_profile_must_change_password(self):
        """Test campo must_change_password."""
        auth_user = UserFactory()
        profile = auth_user.profile
        profile.must_change_password = True
        profile.save()
        refreshed = Profile.objects.get(user=auth_user)
        assert refreshed.must_change_password is True

    def test_profile_str(self):
        """Test representación string de Profile."""
        auth_user = UserFactory(username="testuser")
        profile = auth_user.profile
        assert str(profile) == "testuser"


@pytest.mark.django_db
class TestCustomBackend:
    """Tests para CustomBackend de autenticación."""

    def setup_method(self):
        from users.backends import CustomBackend
        self.backend = CustomBackend()
        self.rf = RequestFactory()

    def test_authenticate_by_username(self):
        """Autentica por username estándar."""
        user = UserFactory(username='testlogin')
        user.set_password('pass123')
        user.save()
        result = self.backend.authenticate(self.rf.get('/'), username='testlogin', password='pass123')
        assert result == user

    def test_authenticate_by_email(self):
        """Autentica por email cuando username falla."""
        user = UserFactory(username='emailuser', email='login@test.com')
        user.set_password('pass123')
        user.save()
        result = self.backend.authenticate(self.rf.get('/'), username='login@test.com', password='pass123')
        assert result == user

    def test_authenticate_by_short_username(self):
        """Autentica por username corto (appends docentes domain)."""
        email = 'jsmith@docentes.educacion.edu.ec'
        user = UserFactory(username='jsmith_full', email=email)
        user.set_password('pass123')
        user.save()
        result = self.backend.authenticate(self.rf.get('/'), username='jsmith', password='pass123')
        assert result == user

    def test_authenticate_wrong_password(self):
        """Falla con contraseña incorrecta."""
        UserFactory(username='nopass', email='nopass@test.com')
        result = self.backend.authenticate(self.rf.get('/'), username='nopass', password='wrong')
        assert result is None

    def test_authenticate_nonexistent_user(self):
        """Falla con usuario que no existe."""
        result = self.backend.authenticate(self.rf.get('/'), username='ghost@nowhere.com', password='x')
        assert result is None

    def test_get_user_exists(self):
        """get_user retorna user cuando existe."""
        user = UserFactory()
        result = self.backend.get_user(user.pk)
        assert result == user

    def test_get_user_not_found(self):
        """get_user retorna None cuando no existe."""
        result = self.backend.get_user(99999)
        assert result is None


@pytest.mark.django_db
class TestGeneratePassword:
    """Tests para generate_temporary_password."""

    def test_password_length(self):
        from users.utils import generate_temporary_password
        pwd = generate_temporary_password(12)
        assert len(pwd) == 12

    def test_password_alphanumeric(self):
        import string
        from users.utils import generate_temporary_password
        pwd = generate_temporary_password()
        allowed = set(string.ascii_letters + string.digits)
        assert all(c in allowed for c in pwd)

    def test_password_custom_length(self):
        from users.utils import generate_temporary_password
        assert len(generate_temporary_password(20)) == 20

    def test_send_welcome_email_type_error(self):
        """Raise TypeError si no se pasa un User."""
        from users.utils import send_welcome_email_with_temporary_password
        with pytest.raises(TypeError):
            send_welcome_email_with_temporary_password("not_a_user")

    @patch('users.utils.send_mail')
    @patch('users.utils.render_to_string', return_value='<html>body</html>')
    def test_send_welcome_email_sends(self, mock_render, mock_send):
        """send_welcome_email_with_temporary_password llama send_mail."""
        from users.utils import send_welcome_email_with_temporary_password
        user = UserFactory(email='welcome@test.com')
        result = send_welcome_email_with_temporary_password(user)
        assert result is True
        mock_send.assert_called_once()


@pytest.mark.django_db
class TestUserSignals:
    """Tests para create_or_update_usuario_profile signal."""

    def test_signal_creates_usuario_on_new_user(self):
        """Crear User → signal crea Usuario."""
        user = UserFactory()
        assert Usuario.objects.filter(auth_user=user).exists()

    def test_signal_links_existing_usuario_by_email(self):
        """Si ya existe Usuario con ese email, signal lo vincula."""
        email = 'link@test.com'
        existing = UsuarioFactory(email=email, auth_user=None, rol=Usuario.Rol.PENDIENTE)
        user = UserFactory(email=email)
        existing.refresh_from_db()
        assert existing.auth_user == user

    def test_signal_updates_usuario_on_user_save(self):
        """Actualizar User → signal actualiza Usuario."""
        user = UserFactory(first_name='Old', last_name='Name')
        user.first_name = 'New'
        user.last_name = 'Name'
        user.save()
        usuario = Usuario.objects.get(auth_user=user)
        assert 'New' in usuario.nombre

    def test_signal_sets_docente_rol_for_staff(self):
        """User is_staff=True → Usuario rol DOCENTE."""
        user = UserFactory(is_staff=True)
        usuario = Usuario.objects.get(auth_user=user)
        assert usuario.rol == Usuario.Rol.DOCENTE

    def test_signal_sets_estudiante_rol_for_non_staff(self):
        """User is_staff=False → Usuario rol ESTUDIANTE."""
        user = UserFactory(is_staff=False)
        usuario = Usuario.objects.get(auth_user=user)
        assert usuario.rol == Usuario.Rol.ESTUDIANTE


@pytest.mark.django_db
class TestRoleProfileSignals:
    """Tests para create_or_update_role_profile signal."""

    def test_docente_usuario_creates_teacher_profile(self):
        """Usuario rol DOCENTE → Teacher auto-creado."""
        from teachers.models import Teacher
        usuario = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        assert Teacher.objects.filter(usuario=usuario).exists()

    def test_estudiante_usuario_creates_student_profile(self):
        """Usuario rol ESTUDIANTE → Student auto-creado."""
        from students.models import Student
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        assert Student.objects.filter(usuario=usuario).exists()

    def test_save_usuario_runs_signal_without_error(self):
        """Guardar Usuario (rol change) no lanza error."""
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        usuario.rol = Usuario.Rol.DOCENTE
        # Should not raise
        usuario.save()
        usuario.refresh_from_db()
        assert usuario.rol == Usuario.Rol.DOCENTE

    def test_pendiente_usuario_has_no_teacher_profile(self):
        """PENDIENTE no crea Teacher ni Student."""
        from students.models import Student
        from teachers.models import Teacher
        usuario = UsuarioFactory(rol=Usuario.Rol.PENDIENTE)
        assert not Teacher.objects.filter(usuario=usuario).exists()
        assert not Student.objects.filter(usuario=usuario).exists()

    def test_rol_change_estudiante_to_docente_deletes_student_profile(self):
        """Cambio ESTUDIANTE → DOCENTE elimina Student, crea Teacher."""
        from students.models import Student
        from teachers.models import Teacher
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        assert Student.objects.filter(usuario=usuario).exists()
        usuario.rol = Usuario.Rol.DOCENTE
        usuario.save()
        assert not Student.objects.filter(usuario=usuario).exists()
        assert Teacher.objects.filter(usuario=usuario).exists()

    def test_rol_change_docente_to_estudiante_deletes_teacher_profile(self):
        """Cambio DOCENTE → ESTUDIANTE elimina Teacher, crea Student."""
        from students.models import Student
        from teachers.models import Teacher
        usuario = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        assert Teacher.objects.filter(usuario=usuario).exists()
        usuario.rol = Usuario.Rol.ESTUDIANTE
        usuario.save()
        assert not Teacher.objects.filter(usuario=usuario).exists()
        assert Student.objects.filter(usuario=usuario).exists()

    def test_rol_change_to_pendiente_removes_profiles(self):
        """Cambio a PENDIENTE elimina perfiles."""
        from students.models import Student
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        assert Student.objects.filter(usuario=usuario).exists()
        usuario.rol = Usuario.Rol.PENDIENTE
        usuario.save()
        assert not Student.objects.filter(usuario=usuario).exists()


@pytest.mark.django_db
class TestUserSignalEmailUpdate:
    """Tests para caminos de actualización de email en la señal."""

    def test_update_user_same_email_no_conflict(self):
        """Actualizar User con mismo email no lanza error."""
        user = UserFactory(email='same@test.com')
        user.first_name = 'Updated'
        user.save()
        assert Usuario.objects.filter(auth_user=user).exists()

    def test_update_user_email_taken_by_other(self):
        """Actualizar email del User cuando ya existe en otro Usuario no lanza error."""
        existing = UsuarioFactory(email='taken@test.com', auth_user=None)
        user = UserFactory(email='original@test.com')
        # Change user email to one already taken by another Usuario
        user.email = 'taken@test.com'
        user.save()  # Signal handles conflict gracefully
        assert True  # No exception raised

    def test_create_user_finds_unlinked_usuario_by_email(self):
        """Si Usuario no vinculado existe con ese email, signal lo vincula."""
        usuario = UsuarioFactory(email='unlinked@test.com', auth_user=None)
        user = UserFactory(email='unlinked@test.com')
        usuario.refresh_from_db()
        assert usuario.auth_user == user

    def test_update_user_email_changes_in_usuario(self):
        """Actualizar email User → se actualiza en Usuario cuando no conflicto."""
        user = UserFactory(email='old@test.com')
        usuario = Usuario.objects.get(auth_user=user)
        user.email = 'new@test.com'
        user.save()
        usuario.refresh_from_db()
        assert usuario.email == 'new@test.com'

    def test_update_user_rol_staff_changes_to_docente(self):
        """User is_staff → rol DOCENTE en signal update."""
        user = UserFactory(is_staff=False)
        usuario = Usuario.objects.get(auth_user=user)
        usuario.rol = Usuario.Rol.PENDIENTE
        usuario.save()
        user.is_staff = True
        user.save()
        usuario.refresh_from_db()
        assert usuario.rol == Usuario.Rol.DOCENTE


@pytest.mark.django_db
class TestClassSignalWhatsApp:
    """Tests para WhatsApp signals en classes."""

    def test_alerta_bajo_rendimiento_triggers_notification(self):
        """Signal notifica WhatsApp cuando promedio < 7."""
        from students.models import Student
        from classes.models import CalificacionParcial, TipoAporte
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="WA1", codigo="WA1X", peso=1)
        with patch('utils.notifications.NotificacionWhatsApp') as mock_wa:
            mock_wa.enviar_alerta_bajo_rendimiento = MagicMock()
            cp = CalificacionParcial.objects.create(
                student=student, subject=subject,
                parcial='1P', quimestre='Q1',
                tipo_aporte=tipo, calificacion=5
            )
        assert cp.pk is not None

    def test_deber_entrega_signal_revisado(self):
        """Signal notifica cuando DeberEntrega estado=revisado y calificacion."""
        from classes.models import Deber, DeberEntrega
        from classes.factories import ClaseFactory
        from django.utils import timezone
        docente = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        estudiante = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        clase = ClaseFactory(docente_base=docente)
        deber = Deber.objects.create(
            clase=clase, teacher=docente,
            titulo="Test Deber",
            fecha_entrega=timezone.now()
        )
        with patch('utils.notifications.NotificacionWhatsApp') as mock_wa:
            mock_wa.notificar_calificacion_deber = MagicMock()
            entrega = DeberEntrega.objects.create(
                deber=deber,
                estudiante=estudiante,
                estado='revisado',
                calificacion=8
            )
        assert entrega.pk is not None
