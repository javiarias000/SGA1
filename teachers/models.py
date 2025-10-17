from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


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
        """Número total de estudiantes del docente"""
        return self.students.count()
    
    def get_total_classes(self):
        """Número total de clases registradas"""
        from classes.models import Activity
        return Activity.objects.filter(student__teacher=self).count()


# SIGNALS
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