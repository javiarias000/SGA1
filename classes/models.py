# ============================================
# ACTUALIZAR models.py - Agregar StudentUser
# ============================================

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from teachers.models import Teacher
from students.models import Student

class Clase(models.Model):
    """Modelo para Clases/Cursos teóricos donde los estudiantes se matriculan"""
    SUBJECT_CHOICES = [
        ('Guitarra Clásica', '🎸 Guitarra Clásica'),
        ('Conjunto Instrumental', '🎺 Conjunto Instrumental'),
        ('Creación y Arreglos Musicales', '🎵 Creación y Arreglos Musicales'),
    ]
    
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='clases_teoricas', verbose_name="Docente")
    name = models.CharField(max_length=200, verbose_name="Nombre de la clase")
    subject = models.CharField(max_length=100, choices=SUBJECT_CHOICES, verbose_name="Materia")
    description = models.TextField(blank=True, verbose_name="Descripción")
    schedule = models.CharField(max_length=200, blank=True, verbose_name="Horario")
    room = models.CharField(max_length=100, blank=True, verbose_name="Aula/Salón")
    max_students = models.PositiveIntegerField(default=30, verbose_name="Capacidad máxima")
    active = models.BooleanField(default=True, verbose_name="Activa")
    fecha = models.DateField(verbose_name="Fecha", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Clase Teórica"
        verbose_name_plural = "Clases Teóricas"
        ordering = ['subject', 'name']
    
    def __str__(self):
        return f"{self.subject} - {self.name}"
    
    def get_enrolled_count(self):
        """Número de estudiantes matriculados"""
        return self.enrollments.filter(active=True).count()
    
    def has_space(self):
        """Verifica si hay espacio disponible"""
        return self.get_enrolled_count() < self.max_students

#==========================================
#MATRICULA ESTUDIANTES
#==========================================

class Enrollment(models.Model):
    """Matrícula de estudiantes en clases teóricas"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="enrollments")
    date_enrolled = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'clase')
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"

    def __str__(self):
        return f"{self.student.name} en {self.clase.name}"

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
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='activities')
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




