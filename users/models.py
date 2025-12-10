from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    """
    Modelo de perfil para extender el modelo de usuario de Django.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crea o actualiza el perfil de usuario cada vez que se guarda un usuario.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        # Asegurarse de que el perfil exista si el usuario fue creado antes de este signal
        Profile.objects.get_or_create(user=instance)