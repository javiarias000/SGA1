from django.db import models
from django.contrib.auth.models import User
from teachers.models import Teacher


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
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='students', verbose_name="Docente")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile', verbose_name="Usuario del estudiante")
    name = models.CharField(max_length=200, verbose_name="Nombre completo")
    grade = models.CharField(max_length=50, verbose_name="Año escolar")
    parent_name = models.CharField(max_length=200, blank=True, verbose_name="Nombre del padre/madre")
    parent_email = models.EmailField(blank=True, verbose_name="Email del padre/madre")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del padre/madre")
    notes = models.TextField(blank=True, verbose_name="Notas adicionales")
    photo = models.ImageField(upload_to='profiles/students/', blank=True, null=True, verbose_name="Foto de perfil")
    active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
    
    def __str__(self):
        return f"{self.name} - {self.grade}"
    
    def can_take_subject(self, subject):
        """Verifica si el estudiante puede tomar una materia según su grado.
        Se usan coincidencias flexibles por nombre para tolerar variaciones (acentos, alias).
        """
        subject_l = (subject.name or '').lower()
        grade_digits = ''.join(filter(str.isdigit, self.grade or ''))
        grade_number = int(grade_digits) if grade_digits else 0
        is_bachillerato = 'bachillerato' in (self.grade or '').lower()
        
        if 'guitarra' in subject_l:
            return True
        if 'conjunto' in subject_l:
            return grade_number >= 6
        if 'creación' in subject_l or 'arreglo' in subject_l:
            return is_bachillerato and grade_number == 2
        return True  # por defecto permitir si no se reconoce la materia, para no bloquear UX
    
    def get_class_count(self, subject=None):
        """Número de clases del estudiante"""
        from classes.models import Activity
        if subject:
            return self.activities.filter(subject=subject).count()
        return self.activities.count()
    
    def get_subjects(self):
        """Materias que el estudiante está tomando"""
        from subjects.models import Subject
        return Subject.objects.filter(activities__student=self).distinct()
    
    def has_user_account(self):
        """Verifica si el estudiante tiene cuenta de usuario"""
        return self.user is not None

