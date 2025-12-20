from django.db import models
from django.contrib.auth.models import User
from teachers.models import Teacher
from subjects.models import Subject
from users.models import Usuario

import uuid


class Student(models.Model):
    """Perfil de estudiante (compatibilidad UI).

    El usuario académico unificado es `users.Usuario`.
    """

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        verbose_name='Usuario unificado'
    )

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name="Docente")
    grade_level = models.ForeignKey('classes.GradeLevel', on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name="Grado")
    parent_name = models.CharField(max_length=200, blank=True, verbose_name="Nombre del padre/madre")
    parent_email = models.EmailField(blank=True, verbose_name="Email del padre/madre")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del padre/madre")
    notes = models.TextField(blank=True, verbose_name="Notas adicionales")
    photo = models.ImageField(upload_to='profiles/students/', blank=True, null=True, verbose_name="Foto de perfil")
    active = models.BooleanField(default=True, verbose_name="Activo")
    registration_code = models.CharField(max_length=36, unique=True, blank=True, null=True, verbose_name="Código de Registro")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['usuario__nombre'] # Order by the name in Usuario
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"

    @property
    def name(self):
        return self.usuario.nombre if self.usuario else "Estudiante sin nombre"

    def __str__(self):
        return f"{self.name} - {self.grade_level}"

    def save(self, *args, **kwargs):
        if not self.registration_code:
            self.registration_code = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def get_class_count(self):
        """Número de clases activas en las que está inscrito el estudiante."""
        if not self.usuario:
            return 0
        from classes.models import Enrollment
        return Enrollment.objects.filter(estudiante=self.usuario, estado='ACTIVO').count()

    def can_take_subject(self, subject):
        """
        Determines if the student can take a given subject.
        For now, all students can take any subject. This can be extended later
        to include grade-based restrictions or prerequisites.
        """
        return True

    def get_subjects(self):
        """Materias distintas en las que está inscrito (vía Enrollment)."""
        if not self.usuario:
            return Subject.objects.none()
        return Subject.objects.filter(
            clases__enrollments__estudiante=self.usuario, # Corrected to filter by the Usuario instance
            clases__enrollments__estado='ACTIVO'
        ).distinct()

