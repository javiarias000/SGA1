from django.db import models
from django.contrib.auth.models import User
from teachers.models import Teacher
from subjects.models import Subject # Import Subject model


import uuid # Import uuid module

class Student(models.Model):
    """Modelo de Estudiante"""
    GRADE_CHOICES = [
        ('2do Básica', '2do Básica'),
        ('3ro Básica', '3ro Básica'),
        ('4to Básica', '4to Básica'),
        ('5to Básica', '5to Básica'),
        ('6to Básica', '6to Básica'),
        ('7mo Básica', '7mo Básica'),
        ('8vo Básica', '8vo Básica'),
        ('1ro Bachillerato', '1ro Bachillerato'),
        ('2do Bachillerato', '2do Bachillerato'),
        ('3ro Bachillerato', '3ro Bachillerato'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name="Docente")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile', verbose_name="Usuario del estudiante")
    name = models.CharField(max_length=200, verbose_name="Nombre completo")
    grade = models.CharField(max_length=50, verbose_name="Año escolar")
    parent_name = models.CharField(max_length=200, blank=True, verbose_name="Nombre del padre/madre")
    parent_email = models.EmailField(blank=True, verbose_name="Email del padre/madre")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del padre/madre")
    notes = models.TextField(blank=True, verbose_name="Notas adicionales")
    photo = models.ImageField(upload_to='profiles/students/', blank=True, null=True, verbose_name="Foto de perfil")
    active = models.BooleanField(default=True, verbose_name="Activo")
    registration_code = models.CharField(max_length=36, unique=True, blank=True, null=True, verbose_name="Código de Registro") # New field
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
    
    def __str__(self):
        return f"{self.name} - {self.grade}"

    def save(self, *args, **kwargs):
        if not self.registration_code:
            self.registration_code = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def get_class_count(self):
        """Returns the number of active classes the student is enrolled in."""
        # Assuming 'enrollments' is the related_name for ForeignKey from Enrollment to Student
        return self.enrollments.filter(active=True).count()

    def can_take_subject(self, subject):
        """
        Determines if the student can take a given subject.
        For now, all students can take any subject. This can be extended later
        to include grade-based restrictions or prerequisites.
        """
        return True

    def get_subjects(self):
        """
        Returns a QuerySet of all distinct subjects the student is currently enrolled in.
        """
        return Subject.objects.filter(clases__enrollments__student=self, clases__enrollments__active=True).distinct()

