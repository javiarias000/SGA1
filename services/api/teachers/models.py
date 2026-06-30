from django.db import models
from django.contrib.auth.models import User
from subjects.models import Subject
from users.models import Usuario

class TeacherSubject(models.Model):
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'subject')
        verbose_name = "Materia Asignada a Docente"
        verbose_name_plural = "Materias Asignadas a Docentes"

    def __str__(self):
        return f"{self.teacher.full_name} - {self.subject.name}"


class Teacher(models.Model):
    """Perfil extendido del docente (compatibilidad UI).
    El usuario académico unificado es `users.Usuario`.
    """

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teacher_profile',
        verbose_name='Usuario unificado'
    )

    # Campos propios del perfil docente (no duplican a Usuario)
    specialization = models.CharField(max_length=120, blank=True, default='', verbose_name='Especialidad')
    subjects = models.ManyToManyField(
        Subject,
        through='TeacherSubject', # Specify the explicit through model
        blank=True,
        related_name='teachers',
        verbose_name='Materias asignadas'
    )

    photo = models.ImageField(upload_to='profiles/teachers/', blank=True, null=True, verbose_name="Foto de perfil")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"
        ordering = ['usuario__nombre'] # Order by the name in Usuario

    @property
    def full_name(self):
        return self.usuario.nombre if self.usuario else "Docente sin nombre"

    @property
    def phone(self):
        return self.usuario.phone if self.usuario else ""

    def __str__(self):
        return self.full_name


    def get_total_students(self):
        return self.students.count()

    def get_total_classes(self):
        from classes.models import Activity
        return Activity.objects.filter(student__teacher=self).count()


class DirectorArea(models.Model):
    """Tabla maestra de Directores de Área del Conservatorio.

    Se usa para autocompletar los datos del director en el wizard de
    Informe Final Docente: la búsqueda solo consulta esta tabla, no el
    listado general de docentes.
    """

    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    area = models.CharField(max_length=120, blank=True, default='', verbose_name='Área')
    telefono = models.CharField(max_length=30, blank=True, default='', verbose_name='Teléfono')
    correo = models.EmailField(blank=True, default='', verbose_name='Correo electrónico')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Director de Área'
        verbose_name_plural = 'Directores de Área'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.area})' if self.area else self.nombre
