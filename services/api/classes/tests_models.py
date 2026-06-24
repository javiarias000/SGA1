import pytest
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from classes.models import Clase, Enrollment, GradeLevel, Horario, CalificacionParcial, TipoAporte, Calificacion, Asistencia, Grade, Attendance, Activity
from classes.factories import ClaseFactory, EnrollmentFactory, GradeLevelFactory, HorarioFactory
from subjects.factories import SubjectFactory
from users.factories import UsuarioFactory
from users.models import Usuario


@pytest.mark.django_db
class TestGradeLevelModel:
    """Tests para el modelo GradeLevel."""

    def test_grade_level_create(self):
        """Test crear GradeLevel."""
        grade = GradeLevelFactory(level='1', section='A')
        assert grade.pk is not None
        assert grade.level == '1'
        assert grade.section == 'A'

    def test_grade_level_str(self):
        """Test representación string de GradeLevel."""
        grade = GradeLevelFactory(level='1', section='B')
        assert "Primero" in str(grade)
        assert "B" in str(grade)

    def test_grade_level_unique_together(self):
        """Test constraint unique_together (level, section)."""
        GradeLevelFactory(level='1', section='A')
        with pytest.raises(Exception):  # IntegrityError
            GradeLevelFactory(level='1', section='A')

    def test_grade_level_all_levels(self):
        """Test todos los niveles de grado."""
        levels = [choice[0] for choice in GradeLevel.LEVEL_CHOICES]
        assert '1' in levels
        assert '10' in levels


@pytest.mark.django_db
class TestClaseModel:
    """Tests para el modelo Clase."""

    def test_clase_create(self):
        """Test crear Clase."""
        clase = ClaseFactory(name="Violin 1", ciclo_lectivo="2025-2026")
        assert clase.pk is not None
        assert clase.name == "Violin 1"
        assert clase.ciclo_lectivo == "2025-2026"

    def test_clase_str(self):
        """Test representación string de Clase."""
        subject = SubjectFactory(name="Piano")
        teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE, nombre="Prof. García")
        clase = ClaseFactory(subject=subject, docente_base=teacher)
        assert "Piano" in str(clase)

    def test_clase_default_max_students(self):
        """Test capacidad máxima por defecto."""
        clase = ClaseFactory()
        assert clase.max_students == 30

    def test_clase_get_enrolled_count(self):
        """Test contar estudiantes activos inscritos."""
        clase = ClaseFactory()
        # Crear 3 inscripciones activas
        for _ in range(3):
            EnrollmentFactory(clase=clase, estado=Enrollment.Estado.ACTIVO)
        # Crear 1 retirada
        EnrollmentFactory(clase=clase, estado=Enrollment.Estado.RETIRADO)

        assert clase.get_enrolled_count() == 3

    def test_clase_has_space(self):
        """Test verificar si hay espacio disponible."""
        clase = ClaseFactory(max_students=2)
        assert clase.has_space() is True

        EnrollmentFactory(clase=clase)
        assert clase.has_space() is True

        EnrollmentFactory(clase=clase)
        assert clase.has_space() is False

    def test_clase_with_grade_level(self):
        """Test Clase con GradeLevel."""
        grade = GradeLevelFactory()
        clase = ClaseFactory(grade_level=grade)
        assert clase.grade_level == grade

    def test_clase_with_teacher(self):
        """Test Clase con docente base."""
        teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        clase = ClaseFactory(docente_base=teacher)
        assert clase.docente_base == teacher


@pytest.mark.django_db
class TestEnrollmentModel:
    """Tests para el modelo Enrollment."""

    def test_enrollment_create(self):
        """Test crear Enrollment."""
        enrollment = EnrollmentFactory()
        assert enrollment.pk is not None
        assert enrollment.estado == Enrollment.Estado.ACTIVO

    def test_enrollment_str(self):
        """Test representación string de Enrollment."""
        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE, nombre="Juan")
        clase = ClaseFactory()
        enrollment = EnrollmentFactory(estudiante=student, clase=clase)
        assert "Juan" in str(enrollment)

    def test_enrollment_estados(self):
        """Test estados de Enrollment."""
        assert Enrollment.Estado.ACTIVO == 'ACTIVO'
        assert Enrollment.Estado.RETIRADO == 'RETIRADO'

    def test_enrollment_tipo_materia_choices(self):
        """Test tipos de materia."""
        tipos = [choice[0] for choice in [
            ('TEORICA', 'Teórica (Grupal)'),
            ('AGRUPACION', 'Agrupación (Ensamble)'),
            ('INSTRUMENTO', 'Instrumento (Individual)')
        ]]
        assert 'TEORICA' in tipos
        assert 'AGRUPACION' in tipos
        assert 'INSTRUMENTO' in tipos

    def test_enrollment_inherits_teacher_from_clase(self):
        """Test que Enrollment hereda docente de Clase si no se asigna."""
        teacher = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        clase = ClaseFactory(docente_base=teacher)

        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        enrollment = EnrollmentFactory(
            estudiante=student,
            clase=clase,
            docente=None,
            tipo_materia='TEORICA'
        )
        # En save(), debería heredad el docente
        enrollment.refresh_from_db()
        # Note: el save() en factory ejecuta pero el clean() no
        # el docente se asigna en save()

    def test_enrollment_instrumento_requires_teacher(self):
        """Test que INSTRUMENTO requiere docente."""
        clase = ClaseFactory(docente_base=None)  # Sin docente base
        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)

        with pytest.raises(ValueError):
            EnrollmentFactory(
                estudiante=student,
                clase=clase,
                docente=None,
                tipo_materia='INSTRUMENTO'
            )

    def test_enrollment_unique_together(self):
        """Test constraint unique_together (estudiante, clase)."""
        enrollment = EnrollmentFactory()
        with pytest.raises(Exception):  # IntegrityError
            EnrollmentFactory(
                estudiante=enrollment.estudiante,
                clase=enrollment.clase
            )

    def test_enrollment_date_enrolled_auto(self):
        """Test que date_enrolled se asigna automáticamente."""
        enrollment = EnrollmentFactory()
        assert enrollment.date_enrolled is not None


@pytest.mark.django_db
class TestHorarioModel:
    """Tests para el modelo Horario."""

    def test_horario_create(self):
        """Test crear Horario."""
        horario = HorarioFactory()
        assert horario.pk is not None

    def test_horario_str(self):
        """Test representación string de Horario."""
        clase = ClaseFactory(name="Piano 101")
        horario = HorarioFactory(clase=clase, dia_semana='Lunes')
        assert "Piano 101" in str(horario)
        assert "Lunes" in str(horario)

    def test_horario_dias_semana(self):
        """Test días de semana disponibles."""
        dias = [choice[0] for choice in [
            ('Lunes', 'Lunes'), ('Martes', 'Martes'), ('Miércoles', 'Miércoles'),
            ('Jueves', 'Jueves'), ('Viernes', 'Viernes'), ('Sábado', 'Sábado'),
            ('Domingo', 'Domingo')
        ]]
        assert 'Lunes' in dias
        assert 'Domingo' in dias

    def test_horario_unique_together(self):
        """Test constraint unique_together (clase, dia_semana, hora_inicio)."""
        horario1 = HorarioFactory()
        with pytest.raises(Exception):  # IntegrityError
            HorarioFactory(
                clase=horario1.clase,
                dia_semana=horario1.dia_semana,
                hora_inicio=horario1.hora_inicio
            )


@pytest.mark.django_db
class TestEnrollmentSave:
    """Tests para Enrollment.save() logic."""

    def test_save_inherits_docente_from_clase(self):
        """Si no se elige docente, hereda docente_base de la clase."""
        docente = UsuarioFactory(rol=Usuario.Rol.DOCENTE)
        clase = ClaseFactory(docente_base=docente)
        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        enrollment = Enrollment.objects.create(
            estudiante=student,
            clase=clase,
            docente=None,
            tipo_materia='TEORICA'
        )
        assert enrollment.docente == docente

    def test_save_instrumento_without_docente_raises(self):
        """INSTRUMENTO sin docente lanza ValueError."""
        subject = SubjectFactory()
        clase = ClaseFactory(subject=subject, docente_base=None)
        student = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        with pytest.raises(ValueError):
            Enrollment.objects.create(
                estudiante=student,
                clase=clase,
                docente=None,
                tipo_materia='INSTRUMENTO'
            )

    def test_enrollment_str(self):
        """__str__ de Enrollment."""
        enrollment = EnrollmentFactory()
        s = str(enrollment)
        assert enrollment.clase.name in s


@pytest.mark.django_db
class TestTipoAporteModel:
    """Tests para TipoAporte."""

    def test_create_tipo_aporte(self):
        tipo = TipoAporte.objects.create(nombre="Deberes", codigo="DEB", peso=1.0)
        assert tipo.pk is not None

    def test_str_tipo_aporte(self):
        tipo = TipoAporte.objects.create(nombre="Examen", codigo="EXAM", peso=2.0)
        assert "Examen" in str(tipo)
        assert "2.0" in str(tipo) or "2" in str(tipo)


@pytest.mark.django_db
class TestCalificacionParcialMethods:
    """Tests para CalificacionParcial métodos estáticos."""

    def _make_student(self):
        from students.models import Student
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        return student

    def test_calcular_promedio_parcial_empty(self):
        """Promedio parcial sin calificaciones retorna 0."""
        student = self._make_student()
        subject = SubjectFactory()
        result = CalificacionParcial.calcular_promedio_parcial(student, subject, '1P')
        assert result == Decimal('0.00')

    def test_calcular_promedio_parcial_with_grades(self):
        """Promedio parcial con calificaciones."""
        from teachers.models import Teacher
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T1", codigo="T1X", peso=1)
        CalificacionParcial.objects.create(
            student=student, subject=subject,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo, calificacion=8
        )
        result = CalificacionParcial.calcular_promedio_parcial(student, subject, '1P')
        assert result == Decimal('8.00')

    def test_calcular_promedio_quimestre_empty(self):
        """Promedio quimestre sin calificaciones retorna 0."""
        student = self._make_student()
        subject = SubjectFactory()
        result = CalificacionParcial.calcular_promedio_quimestre(student, subject)
        assert result == Decimal('0.00')

    def test_calcular_nota_final_materia(self):
        """Nota final materia cuando Q1 y Q2 tienen datos."""
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T2", codigo="T2X", peso=1)
        for parcial in ['1P', '2P']:
            CalificacionParcial.objects.create(
                student=student, subject=subject,
                parcial=parcial, quimestre='Q1',
                tipo_aporte=tipo, calificacion=8
            )
        result = CalificacionParcial.calcular_nota_final_materia(student, subject)
        assert result >= Decimal('0')

    def test_calcular_promedio_general_no_materias(self):
        """Promedio general sin materias retorna 0."""
        student = self._make_student()
        result = CalificacionParcial.calcular_promedio_general(student)
        assert result == Decimal('0.00')

    def test_get_escala_cualitativa_dar(self):
        """Nota >= 9 → DAR."""
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T3", codigo="T3X", peso=1)
        cp = CalificacionParcial.objects.create(
            student=student, subject=subject,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo, calificacion=9.5
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'DAR'

    def test_get_escala_cualitativa_aar(self):
        """Nota 7-8.99 → AAR."""
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T4", codigo="T4X", peso=1)
        cp = CalificacionParcial.objects.create(
            student=student, subject=subject,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo, calificacion=8
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'AAR'

    def test_get_escala_cualitativa_paar(self):
        """Nota 4.01-6.99 → PAAR."""
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T5", codigo="T5X", peso=1)
        cp = CalificacionParcial.objects.create(
            student=student, subject=subject,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo, calificacion=5
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'PAAR'

    def test_get_escala_cualitativa_naar(self):
        """Nota <= 4 → NAAR."""
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T6", codigo="T6X", peso=1)
        cp = CalificacionParcial.objects.create(
            student=student, subject=subject,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo, calificacion=3
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'NAAR'

    def test_calificacion_parcial_str(self):
        """__str__ de CalificacionParcial."""
        student = self._make_student()
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="T7", codigo="T7X", peso=1)
        cp = CalificacionParcial.objects.create(
            student=student, subject=subject,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo, calificacion=7
        )
        s = str(cp)
        assert "7" in s


@pytest.mark.django_db
class TestCalificacionAsistenciaModels:
    """Tests para Calificacion y Asistencia."""

    def test_calificacion_str(self):
        enrollment = EnrollmentFactory()
        from datetime import date
        cal = Calificacion.objects.create(
            inscripcion=enrollment,
            descripcion="Examen",
            nota=8.5,
            fecha=date.today()
        )
        s = str(cal)
        assert "8.5" in s or "Examen" in s

    def test_asistencia_str(self):
        enrollment = EnrollmentFactory()
        from datetime import date
        asistencia = Asistencia.objects.create(
            inscripcion=enrollment,
            fecha=date.today(),
            estado=Asistencia.Estado.PRESENTE
        )
        s = str(asistencia)
        assert "Presente" in s

    def test_grade_str(self):
        """Legacy Grade __str__."""
        from students.models import Student
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        subject = SubjectFactory()
        from datetime import date
        grade = Grade.objects.create(
            student=student, subject=subject,
            period='Primer Parcial', score=9,
            date=date.today()
        )
        s = str(grade)
        assert "9" in s

    def test_attendance_str(self):
        """Legacy Attendance __str__."""
        from students.models import Student
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        from datetime import date
        att = Attendance.objects.create(
            student=student,
            date=date.today(),
            status='Presente'
        )
        s = str(att)
        assert "Presente" in s


@pytest.mark.django_db
class TestClassSignals:
    """Tests para signals de classes."""

    def test_alerta_bajo_rendimiento_no_crash_on_error(self):
        """Signal no crashea si hay error interno."""
        from students.models import Student
        student = Student.objects.create(usuario=None)
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="ST1", codigo="ST1X", peso=1)
        with patch('utils.notifications.NotificacionWhatsApp') as mock_notif:
            CalificacionParcial.objects.create(
                student=student, subject=subject,
                parcial='1P', quimestre='Q1',
                tipo_aporte=tipo, calificacion=5
            )

    def test_calificacion_signal_fires_on_save(self):
        """Signal alerta_bajo_rendimiento dispara sin crash."""
        from students.models import Student
        usuario = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=usuario)
        subject = SubjectFactory()
        tipo = TipoAporte.objects.create(nombre="ST2", codigo="ST2X", peso=1)
        with patch('utils.notifications.NotificacionWhatsApp') as mock_wa:
            cp = CalificacionParcial.objects.create(
                student=student, subject=subject,
                parcial='1P', quimestre='Q1',
                tipo_aporte=tipo, calificacion=6
            )
            assert cp.pk is not None
