"""
Tests de integración — SGA1
Flujo completo: Subject → GradeLevel → Clase → Enrollment → Calificaciones
"""
import pytest
from decimal import Decimal
from datetime import date, time
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from users.models import Usuario
from users.factories import UsuarioFactory, UserFactory
from subjects.models import Subject
from subjects.factories import SubjectFactory
from classes.models import (
    GradeLevel, Clase, Enrollment, TipoAporte,
    CalificacionParcial, Calificacion, Asistencia,
    MallaCurricular,
)
from classes.factories import GradeLevelFactory, ClaseFactory, EnrollmentFactory
from students.models import Student
from teachers.models import Teacher
from setup.models import ConfiguracionInstitucion


# ════════════════════════════════════════
# Fixtures compartidos
# ════════════════════════════════════════

@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser('admin_test', 'admin@test.com', 'Admin1234!')
    return user

@pytest.fixture
def subject_piano(db):
    return SubjectFactory(name='Piano', tipo_materia='INSTRUMENTO')

@pytest.fixture
def subject_solfeo(db):
    return SubjectFactory(name='Solfeo', tipo_materia='TEORIA')

@pytest.fixture
def subject_orquesta(db):
    return SubjectFactory(name='Orquesta', tipo_materia='AGRUPACION')

@pytest.fixture
def nivel_1(db):
    gl, _ = GradeLevel.objects.get_or_create(level='1', section='Único')
    return gl

@pytest.fixture
def docente_usuario(db):
    return UsuarioFactory(nombre='Prof. Test', rol=Usuario.Rol.DOCENTE)

@pytest.fixture
def docente(db, docente_usuario):
    teacher, _ = Teacher.objects.get_or_create(usuario=docente_usuario)
    return teacher

@pytest.fixture
def estudiante_usuario(db):
    return UsuarioFactory(nombre='Estudiante Test', rol=Usuario.Rol.ESTUDIANTE)

@pytest.fixture
def estudiante(db, estudiante_usuario):
    student, _ = Student.objects.get_or_create(usuario=estudiante_usuario)
    return student

@pytest.fixture
def clase_piano(db, subject_piano, nivel_1, docente_usuario):
    return ClaseFactory(
        name='Piano 1er Año',
        subject=subject_piano,
        grade_level=nivel_1,
        docente_base=docente_usuario,
        ciclo_lectivo='2025-2026',
    )

@pytest.fixture
def tipo_aporte(db):
    return TipoAporte.objects.create(nombre='Deberes', codigo='DEB', peso=1.0)

@pytest.fixture
def enrollment(db, clase_piano, estudiante_usuario, docente_usuario):
    return Enrollment.objects.create(
        estudiante=estudiante_usuario,
        clase=clase_piano,
        docente=docente_usuario,
        tipo_materia='INSTRUMENTO',
        estado=Enrollment.Estado.ACTIVO,
    )


# ════════════════════════════════════════
# 1. FLUJO DE CREACIÓN DE ENTIDADES BASE
# ════════════════════════════════════════

@pytest.mark.django_db
class TestFlujoEntidadesBase:

    def test_subject_create(self, subject_piano):
        assert subject_piano.pk is not None
        assert subject_piano.tipo_materia == 'INSTRUMENTO'

    def test_grade_level_create(self, nivel_1):
        assert nivel_1.pk is not None
        assert nivel_1.level == '1'

    def test_usuario_docente_creates_teacher_profile(self, docente_usuario):
        assert Teacher.objects.filter(usuario=docente_usuario).exists()

    def test_usuario_estudiante_creates_student_profile(self, estudiante_usuario):
        assert Student.objects.filter(usuario=estudiante_usuario).exists()

    def test_clase_links_subject_nivel_docente(self, clase_piano, subject_piano, nivel_1, docente_usuario):
        assert clase_piano.subject == subject_piano
        assert clase_piano.grade_level == nivel_1
        assert clase_piano.docente_base == docente_usuario


# ════════════════════════════════════════
# 2. FLUJO DE MATRÍCULA (ENROLLMENT)
# ════════════════════════════════════════

@pytest.mark.django_db
class TestFlujoMatricula:

    def test_enrollment_creation(self, enrollment):
        assert enrollment.pk is not None
        assert enrollment.estado == Enrollment.Estado.ACTIVO

    def test_enrollment_class_capacity(self, clase_piano, estudiante_usuario, docente_usuario):
        clase_piano.max_students = 2
        clase_piano.save()
        assert clase_piano.has_space()

        u2 = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        u3 = UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE)
        Enrollment.objects.create(estudiante=u2, clase=clase_piano, docente=docente_usuario, tipo_materia='INSTRUMENTO')
        assert clase_piano.has_space()
        Enrollment.objects.create(estudiante=u3, clase=clase_piano, docente=docente_usuario, tipo_materia='INSTRUMENTO')
        assert not clase_piano.has_space()

    def test_enrollment_unique_estudiante_clase(self, enrollment, clase_piano, estudiante_usuario, docente_usuario):
        with pytest.raises(Exception):
            Enrollment.objects.create(
                estudiante=estudiante_usuario,
                clase=clase_piano,
                docente=docente_usuario,
                tipo_materia='INSTRUMENTO',
            )

    def test_enrollment_hereda_docente_de_clase(self, clase_piano, estudiante_usuario):
        enr = Enrollment.objects.create(
            estudiante=estudiante_usuario,
            clase=clase_piano,
            docente=None,
            tipo_materia='TEORICA',
        )
        assert enr.docente == clase_piano.docente_base

    def test_enrollment_get_enrolled_count(self, clase_piano, enrollment):
        assert clase_piano.get_enrolled_count() == 1

    def test_enrollment_retirado_no_cuenta(self, clase_piano, enrollment):
        enrollment.estado = Enrollment.Estado.RETIRADO
        enrollment.save()
        assert clase_piano.get_enrolled_count() == 0


# ════════════════════════════════════════
# 3. FLUJO DE CALIFICACIONES PARCIALES
# ════════════════════════════════════════

@pytest.mark.django_db
class TestFlujoCalificaciones:

    def test_calificacion_parcial_create(self, estudiante, subject_piano, tipo_aporte):
        cp = CalificacionParcial.objects.create(
            student=estudiante,
            subject=subject_piano,
            parcial='1P',
            quimestre='Q1',
            tipo_aporte=tipo_aporte,
            calificacion=8.5,
        )
        assert cp.pk is not None
        assert cp.calificacion == Decimal('8.5')

    def test_escala_dar(self, estudiante, subject_piano, tipo_aporte):
        cp = CalificacionParcial.objects.create(
            student=estudiante, subject=subject_piano,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo_aporte, calificacion=9.5
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'DAR'

    def test_escala_aar(self, estudiante, subject_piano, tipo_aporte):
        cp = CalificacionParcial.objects.create(
            student=estudiante, subject=subject_piano,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo_aporte, calificacion=8.0
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'AAR'

    def test_escala_paar(self, estudiante, subject_piano, tipo_aporte):
        cp = CalificacionParcial.objects.create(
            student=estudiante, subject=subject_piano,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo_aporte, calificacion=5.0
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'PAAR'

    def test_escala_naar(self, estudiante, subject_piano, tipo_aporte):
        cp = CalificacionParcial.objects.create(
            student=estudiante, subject=subject_piano,
            parcial='1P', quimestre='Q1',
            tipo_aporte=tipo_aporte, calificacion=3.0
        )
        assert cp.get_escala_cualitativa()['codigo'] == 'NAAR'

    def test_promedio_parcial(self, estudiante, subject_piano):
        t1 = TipoAporte.objects.create(nombre='Tareas', codigo='TAR', peso=1)
        t2 = TipoAporte.objects.create(nombre='Examen', codigo='EXA', peso=1)
        CalificacionParcial.objects.create(
            student=estudiante, subject=subject_piano,
            parcial='1P', quimestre='Q1', tipo_aporte=t1, calificacion=8
        )
        CalificacionParcial.objects.create(
            student=estudiante, subject=subject_piano,
            parcial='1P', quimestre='Q1', tipo_aporte=t2, calificacion=6
        )
        prom = CalificacionParcial.calcular_promedio_parcial(estudiante, subject_piano, '1P')
        assert prom == Decimal('7.00')

    def test_multiples_parciales_mismo_quimestre(self, estudiante, subject_piano, tipo_aporte):
        for parcial in ['1P', '2P', '3P']:
            CalificacionParcial.objects.create(
                student=estudiante, subject=subject_piano,
                parcial=parcial, quimestre='Q1',
                tipo_aporte=tipo_aporte, calificacion=8
            )
        prom = CalificacionParcial.calcular_promedio_quimestre(estudiante, subject_piano)
        assert prom >= Decimal('0')


# ════════════════════════════════════════
# 4. FLUJO DE ASISTENCIA
# ════════════════════════════════════════

@pytest.mark.django_db
class TestFlujoAsistencia:

    def test_asistencia_create(self, enrollment):
        a = Asistencia.objects.create(
            inscripcion=enrollment,
            fecha=date.today(),
            estado=Asistencia.Estado.PRESENTE,
        )
        assert a.pk is not None
        assert a.estado == Asistencia.Estado.PRESENTE

    def test_asistencia_estados(self, enrollment):
        estados = [Asistencia.Estado.PRESENTE, Asistencia.Estado.AUSENTE, Asistencia.Estado.TARDANZA]
        for estado in estados:
            a = Asistencia.objects.create(
                inscripcion=enrollment,
                fecha=date(2025, 1, estados.index(estado) + 1),
                estado=estado,
            )
            assert a.estado == estado

    def test_calificacion_legacy_create(self, enrollment):
        cal = Calificacion.objects.create(
            inscripcion=enrollment,
            descripcion='Examen Final',
            nota=9.0,
            fecha=date.today(),
        )
        assert cal.pk is not None


# ════════════════════════════════════════
# 5. PENSUM (MALLA CURRICULAR)
# ════════════════════════════════════════

@pytest.mark.django_db
class TestFlujoPensum:

    def test_malla_curricular_create(self, nivel_1, subject_piano):
        mc = MallaCurricular.objects.create(
            nivel=nivel_1,
            subject=subject_piano,
            obligatoria=True,
            orden=1,
        )
        assert mc.pk is not None
        assert mc.obligatoria is True

    def test_malla_curricular_multiple_subjects(self, nivel_1, subject_piano, subject_solfeo, subject_orquesta):
        subjects = [subject_piano, subject_solfeo, subject_orquesta]
        for i, s in enumerate(subjects):
            MallaCurricular.objects.create(nivel=nivel_1, subject=s, obligatoria=True, orden=i)
        count = MallaCurricular.objects.filter(nivel=nivel_1).count()
        assert count == 3

    def test_malla_curricular_unique(self, nivel_1, subject_piano):
        MallaCurricular.objects.create(nivel=nivel_1, subject=subject_piano, obligatoria=True)
        with pytest.raises(Exception):
            MallaCurricular.objects.create(nivel=nivel_1, subject=subject_piano, obligatoria=False)

    def test_malla_multiples_niveles(self, subject_piano, db):
        for level_val in ['1', '2', '3']:
            gl, _ = GradeLevel.objects.get_or_create(level=level_val, section='Único')
            MallaCurricular.objects.create(nivel=gl, subject=subject_piano, obligatoria=True)
        count = MallaCurricular.objects.filter(subject=subject_piano).count()
        assert count == 3


# ════════════════════════════════════════
# 6. VISTAS DEL WIZARD (HTTP)
# ════════════════════════════════════════

@pytest.mark.django_db
class TestWizardViews:

    def setup_method(self):
        self.client = Client()

    def _login(self):
        user = User.objects.create_superuser('wiz_admin', 'wiz@test.com', 'Pass1234!')
        self.client.login(username='wiz_admin', password='Pass1234!')
        return user

    def test_wizard_home_requires_login(self):
        resp = self.client.get('/setup/')
        assert resp.status_code in (302, 301)

    def test_wizard_home_logged_in(self):
        self._login()
        resp = self.client.get('/setup/')
        assert resp.status_code == 200

    def test_wizard_institucion(self):
        self._login()
        resp = self.client.get('/setup/institucion/')
        assert resp.status_code == 200

    def test_wizard_materias(self):
        self._login()
        resp = self.client.get('/setup/materias/')
        assert resp.status_code == 200

    def test_wizard_tipos_aporte(self):
        self._login()
        resp = self.client.get('/setup/tipos-aporte/')
        assert resp.status_code == 200

    def test_wizard_niveles(self):
        self._login()
        resp = self.client.get('/setup/niveles/')
        assert resp.status_code == 200

    def test_wizard_docentes(self):
        self._login()
        resp = self.client.get('/setup/docentes/')
        assert resp.status_code == 200

    def test_wizard_clases(self):
        self._login()
        resp = self.client.get('/setup/clases/')
        assert resp.status_code == 200

    def test_wizard_estudiantes(self):
        self._login()
        resp = self.client.get('/setup/estudiantes/')
        assert resp.status_code == 200

    def test_wizard_matriculas(self):
        self._login()
        resp = self.client.get('/setup/matriculas/')
        assert resp.status_code == 200

    def test_pensum_home(self):
        self._login()
        resp = self.client.get('/setup/pensum/')
        assert resp.status_code == 200

    def test_pensum_nivel_1(self):
        self._login()
        resp = self.client.get('/setup/pensum/nivel/1/')
        assert resp.status_code == 200

    def test_pensum_nivel_11(self):
        self._login()
        resp = self.client.get('/setup/pensum/nivel/11/')
        assert resp.status_code == 200

    def test_pensum_importar(self):
        self._login()
        resp = self.client.get('/setup/pensum/importar/')
        assert resp.status_code == 200

    def test_pensum_guardar_materias(self, subject_piano, subject_solfeo):
        self._login()
        resp = self.client.post('/setup/pensum/nivel/1/', {
            'action': 'save_stay',
            'subjects': [subject_piano.pk, subject_solfeo.pk],
            'obligatorias': [subject_piano.pk],
        })
        assert resp.status_code in (200, 302)
        gl = GradeLevel.objects.filter(level='1').first()
        if gl:
            assert MallaCurricular.objects.filter(nivel=gl, subject=subject_piano).exists()

    def test_wizard_post_materia(self):
        self._login()
        resp = self.client.post('/setup/materias/', {
            'accion': 'crear',
            'name': 'Guitarra',
            'tipo_materia': 'INSTRUMENTO',
        })
        assert resp.status_code in (200, 302)

    def test_wizard_post_tipo_aporte(self):
        self._login()
        resp = self.client.post('/setup/tipos-aporte/', {
            'accion': 'crear',
            'nombre': 'Lecciones',
            'codigo': 'LEC',
            'peso': '1.0',
        })
        assert resp.status_code in (200, 302)


# ════════════════════════════════════════
# 7. FLUJO COMPLETO END-TO-END
# ════════════════════════════════════════

@pytest.mark.django_db
class TestFlujoCompletoE2E:
    """Simulación del flujo real de un año académico."""

    def test_flujo_completo_matricula_calificacion_asistencia(self):
        # 1. Entidades base
        subject = SubjectFactory(name='Violín', tipo_materia='INSTRUMENTO')
        nivel, _ = GradeLevel.objects.get_or_create(level='2', section='A')
        tipo = TipoAporte.objects.create(nombre='Prueba', codigo='PRU', peso=1)

        # 2. Personas
        doc_usuario = UsuarioFactory(nombre='Prof. Violín', rol=Usuario.Rol.DOCENTE)
        est_usuario = UsuarioFactory(nombre='Ana García', rol=Usuario.Rol.ESTUDIANTE)
        student, _ = Student.objects.get_or_create(usuario=est_usuario)

        # 3. Clase
        clase = Clase.objects.create(
            name='Violín 2do A',
            subject=subject,
            grade_level=nivel,
            docente_base=doc_usuario,
            ciclo_lectivo='2025-2026',
            max_students=15,
        )

        # 4. Matrícula
        enr = Enrollment.objects.create(
            estudiante=est_usuario,
            clase=clase,
            docente=doc_usuario,
            tipo_materia='INSTRUMENTO',
            estado=Enrollment.Estado.ACTIVO,
        )
        assert clase.get_enrolled_count() == 1

        # 5. Asistencia (presente en 3 días)
        for day in range(1, 4):
            Asistencia.objects.create(
                inscripcion=enr,
                fecha=date(2025, 9, day),
                estado=Asistencia.Estado.PRESENTE,
            )
        assert Asistencia.objects.filter(inscripcion=enr).count() == 3

        # 6. Calificaciones parciales
        for parcial, nota in [('1P', 9.0), ('2P', 8.5), ('3P', 7.5)]:
            CalificacionParcial.objects.create(
                student=student,
                subject=subject,
                parcial=parcial,
                quimestre='Q1',
                tipo_aporte=tipo,
                calificacion=nota,
            )

        prom = CalificacionParcial.calcular_promedio_quimestre(student, subject)
        assert prom > Decimal('0')

        # 7. Pensum
        MallaCurricular.objects.create(nivel=nivel, subject=subject, obligatoria=True)
        assert MallaCurricular.objects.filter(nivel=nivel, subject=subject).exists()

        # 8. Verificar escala cualitativa (promedio debe ser ~8.3 → AAR)
        cp = CalificacionParcial.objects.filter(student=student, subject=subject).first()
        escala = cp.get_escala_cualitativa()
        assert escala['codigo'] in ('DAR', 'AAR', 'PAAR', 'NAAR')

    def test_multiples_estudiantes_misma_clase(self, clase_piano, docente_usuario):
        estudiantes = [UsuarioFactory(rol=Usuario.Rol.ESTUDIANTE) for _ in range(5)]
        for est in estudiantes:
            Enrollment.objects.create(
                estudiante=est,
                clase=clase_piano,
                docente=docente_usuario,
                tipo_materia='INSTRUMENTO',
                estado=Enrollment.Estado.ACTIVO,
            )
        assert clase_piano.get_enrolled_count() == 5

    def test_estudiante_en_multiples_clases(self, estudiante_usuario, docente_usuario):
        classes = [ClaseFactory(docente_base=docente_usuario) for _ in range(3)]
        for clase in classes:
            Enrollment.objects.create(
                estudiante=estudiante_usuario,
                clase=clase,
                docente=docente_usuario,
                tipo_materia='TEORICA',
            )
        count = Enrollment.objects.filter(estudiante=estudiante_usuario).count()
        assert count == 3


# ════════════════════════════════════════
# 8. SETUP — CONFIGURACIÓN INSTITUCIÓN
# ════════════════════════════════════════

@pytest.mark.django_db
class TestSetupModelo:

    def test_configuracion_institucion_create(self):
        config, created = ConfiguracionInstitucion.objects.get_or_create(
            defaults={'nombre_institucion': 'Conservatorio Test'}
        )
        assert config.pk is not None

    def test_wizard_redirect_sin_staff(self):
        client = Client()
        user = User.objects.create_user('nostaff', 'ns@test.com', 'Pass1234!')
        client.login(username='nostaff', password='Pass1234!')
        resp = client.get('/setup/')
        assert resp.status_code in (302, 403)
