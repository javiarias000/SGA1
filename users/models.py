from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Usuario(models.Model):
    """Usuario unificado del dominio académico (docente / estudiante).

    Nota: NO reemplaza a auth_user (Django User). Si tiene login, se enlaza por OneToOne.
    """

    class Rol(models.TextChoices):
        DOCENTE = 'DOCENTE', 'Docente'
        ESTUDIANTE = 'ESTUDIANTE', 'Estudiante'
        # Add a default or a 'PENDING' role if needed for initial creation
        # For now, let's make ESTUDIANTE the default if not specified
        PENDIENTE = 'PENDIENTE', 'Pendiente' # New role for users who haven't been assigned yet

    nombre = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.PENDIENTE)

    # Datos útiles para matching ETL y búsqueda
    email = models.EmailField(blank=True, null=True, unique=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True, null=True, unique=True)

    auth_user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuario',
        verbose_name='Usuario de login (auth_user)'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    _original_rol = None # To store the original rol for comparison in signals

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_rol = self.rol

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        indexes = [
            models.Index(fields=['rol']),
            models.Index(fields=['nombre']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.rol})"


class Profile(models.Model):
    """Perfil técnico para extender auth_user (solo banderas internas)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Crea o actualiza el perfil técnico Profile para auth_user."""

    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
