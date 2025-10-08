# ============================================
# ACTUALIZAR models.py - Agregar StudentUser
# ============================================

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Teacher(models.Model):
    """Perfil extendido del docente"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    full_name = models.CharField(max_length=200, verbose_name="Nombre completo")
    specialization = models.CharField(max_length=100, blank=True, verbose_name="Especialización")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"
        ordering = ['full_name']
    
    def __str__(self):
        return self.full_name
    
    def get_total_students(self):
        return self.students.count()
    
    def get_total_classes(self):
        return Activity.objects.filter(student__teacher=self).count()


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
    grade = models.CharField(max_length=50, choices=GRADE_CHOICES, verbose_name="Año escolar")
    parent_name = models.CharField(max_length=200, blank=True, verbose_name="Nombre del padre/madre")
    parent_email = models.EmailField(blank=True, verbose_name="Email del padre/madre")
    parent_phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono del padre/madre")
    notes = models.TextField(blank=True, verbose_name="Notas adicionales")
    active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
    
    def __str__(self):
        return f"{self.name} - {self.grade}"
    
    def can_take_subject(self, subject):
        grade_number = int(''.join(filter(str.isdigit, self.grade)))
        is_bachillerato = 'Bachillerato' in self.grade
        
        if subject == 'Guitarra Clásica':
            return True
        elif subject == 'Conjunto Instrumental':
            return grade_number >= 6
        elif subject == 'Creación y Arreglos Musicales':
            return is_bachillerato and grade_number == 2
        return False
    
    def get_class_count(self, subject=None):
        if subject:
            return self.activities.filter(subject=subject).count()
        return self.activities.count()
    
    def get_subjects(self):
        return self.activities.values_list('subject', flat=True).distinct()
    
    def has_user_account(self):
        """Verifica si el estudiante tiene cuenta de usuario"""
        return self.user is not None


class Activity(models.Model):
    """Modelo de Actividad/Clase"""
    SUBJECT_CHOICES = [
        ('Guitarra Clásica', '🎸 Guitarra Clásica'),
        ('Conjunto Instrumental', '🎺 Conjunto Instrumental'),
        ('Creación y Arreglos Musicales', '🎵 Creación y Arreglos Musicales'),
    ]
    
    PERFORMANCE_CHOICES = [
        ('Excelente', 'Excelente'),
        ('Muy Bueno', 'Muy Bueno'),
        ('Bueno', 'Bueno'),
        ('Regular', 'Regular'),
        ('Necesita mejorar', 'Necesita mejorar'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='activities', verbose_name="Estudiante")
    subject = models.CharField(max_length=100, choices=SUBJECT_CHOICES, verbose_name="Materia")
    class_number = models.PositiveIntegerField(verbose_name="Número de clase")
    date = models.DateField(verbose_name="Fecha de clase")
    
    topics_worked = models.TextField(blank=True, verbose_name="Temas trabajados")
    techniques = models.TextField(blank=True, verbose_name="Técnicas desarrolladas")
    pieces = models.CharField(max_length=500, blank=True, verbose_name="Piezas/Repertorio")
    
    performance = models.CharField(max_length=50, choices=PERFORMANCE_CHOICES, default='Bueno', verbose_name="Desempeño")
    strengths = models.TextField(blank=True, verbose_name="Fortalezas")
    areas_to_improve = models.TextField(blank=True, verbose_name="Áreas a mejorar")
    
    homework = models.TextField(blank=True, verbose_name="Tareas para casa")
    practice_time = models.PositiveIntegerField(
        default=30, 
        validators=[MinValueValidator(15), MaxValueValidator(180)],
        verbose_name="Tiempo de práctica (minutos)"
    )
    
    observations = models.TextField(blank=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-class_number']
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        unique_together = ['student', 'subject', 'class_number']
    
    def __str__(self):
        return f"{self.student.name} - {self.subject} - Clase #{self.class_number}"
    
    def save(self, *args, **kwargs):
        if not self.class_number:
            last_class = Activity.objects.filter(
                student=self.student,
                subject=self.subject
            ).order_by('-class_number').first()
            
            self.class_number = (last_class.class_number + 1) if last_class else 1
        
        super().save(*args, **kwargs)
    
    def get_teacher(self):
        return self.student.teacher


class Grade(models.Model):
    """Modelo para calificaciones/notas"""
    PERIOD_CHOICES = [
        ('Primer Parcial', 'Primer Parcial'),
        ('Segundo Parcial', 'Segundo Parcial'),
        ('Tercer Parcial', 'Tercer Parcial'),
        ('Examen Final', 'Examen Final'),
        ('Quimestre 1', 'Quimestre 1'),
        ('Quimestre 2', 'Quimestre 2'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades', verbose_name="Estudiante")
    subject = models.CharField(max_length=100, choices=Activity.SUBJECT_CHOICES, verbose_name="Materia")
    period = models.CharField(max_length=50, choices=PERIOD_CHOICES, verbose_name="Período")
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10)], verbose_name="Calificación")
    comments = models.TextField(blank=True, verbose_name="Comentarios")
    date = models.DateField(verbose_name="Fecha de calificación")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        unique_together = ['student', 'subject', 'period']
    
    def __str__(self):
        return f"{self.student.name} - {self.subject} - {self.period}: {self.score}"


class Attendance(models.Model):
    """Modelo para control de asistencia"""
    STATUS_CHOICES = [
        ('Presente', '✅ Presente'),
        ('Ausente', '❌ Ausente'),
        ('Tardanza', '⏰ Tardanza'),
        ('Justificado', '📝 Justificado'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances', verbose_name="Estudiante")
    date = models.DateField(verbose_name="Fecha")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Presente', verbose_name="Estado")
    notes = models.TextField(blank=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ['student', 'date']
    
    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"


# ============================================
# SIGNALS - Mantener los mismos
# ============================================
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_teacher_profile(sender, instance, created, **kwargs):
    """Crear perfil de docente automáticamente cuando se crea un usuario"""
    if created and not instance.is_superuser:
        # Solo crear Teacher si no existe student_profile
        if not hasattr(instance, 'student_profile'):
            Teacher.objects.get_or_create(
                user=instance,
                defaults={
                    'full_name': f"{instance.first_name} {instance.last_name}".strip() or instance.username
                }
            )

@receiver(post_save, sender=User)
def save_teacher_profile(sender, instance, **kwargs):
    """Guardar perfil de docente"""
    if not instance.is_superuser and hasattr(instance, 'teacher_profile'):
        instance.teacher_profile.save()