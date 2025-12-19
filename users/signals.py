from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Usuario
from teachers.models import Teacher
from students.models import Student

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_usuario_profile(sender, instance, created, **kwargs):
    """
    Creates or updates a Usuario instance for every User.
    Sets the rol based on is_staff status.
    """
    if created:
        # For new users, create a Usuario instance
        usuario_defaults = {
            'nombre': f"{instance.first_name} {instance.last_name}".strip() or instance.username,
            'email': instance.email,
        }
        if instance.is_staff:
            usuario_defaults['rol'] = Usuario.Rol.DOCENTE
        else:
            usuario_defaults['rol'] = Usuario.Rol.ESTUDIANTE # Default for non-staff
        Usuario.objects.create(auth_user=instance, **usuario_defaults)
    else:
        # For existing users, ensure Usuario exists and update its fields
        usuario, created_usuario = Usuario.objects.get_or_create(auth_user=instance)
        if not created_usuario:
            # Update fields if user data changes
            current_name = f"{instance.first_name} {instance.last_name}".strip() or instance.username
            if usuario.nombre != current_name:
                usuario.nombre = current_name
            if usuario.email != instance.email:
                usuario.email = instance.email

            # Update rol if is_staff status changes
            # Only change if the rol is not already explicitly set or a different role
            if instance.is_staff and usuario.rol != Usuario.Rol.DOCENTE:
                usuario.rol = Usuario.Rol.DOCENTE
            elif not instance.is_staff and usuario.rol != Usuario.Rol.ESTUDIANTE:
                # If it's not staff and not already a teacher, default to student
                if usuario.rol != Usuario.Rol.DOCENTE: # Avoid overriding manually set teacher role for non-staff
                    usuario.rol = Usuario.Rol.ESTUDIANTE
            usuario.save()

@receiver(post_save, sender=Usuario)
def create_or_update_role_profile(sender, instance, created, **kwargs):
    """
    Creates or updates Teacher or Student profile based on Usuario's rol.
    Also handles deletion of old role profiles if rol changes.
    """
    # Use instance._original_rol to check for changes
    # This assumes _original_rol is correctly populated from the __init__ method
    rol_changed = created or (hasattr(instance, '_original_rol') and instance._original_rol != instance.rol)

    if rol_changed:
        # Handle deletion of old profile if rol has changed
        if hasattr(instance, '_original_rol') and instance._original_rol == Usuario.Rol.DOCENTE and hasattr(instance, 'teacher_profile'):
            instance.teacher_profile.delete()
        elif hasattr(instance, '_original_rol') and instance._original_rol == Usuario.Rol.ESTUDIANTE and hasattr(instance, 'student_profile'):
            instance.student_profile.delete()

        # Create/update new profile based on current rol
        if instance.rol == Usuario.Rol.DOCENTE:
            Teacher.objects.get_or_create(usuario=instance, defaults={'specialization': ''})
        elif instance.rol == Usuario.Rol.ESTUDIANTE:
            Student.objects.get_or_create(usuario=instance, defaults={'registration_code': ''})
        elif instance.rol == Usuario.Rol.PENDIENTE:
            # If the user is set to PENDING, ensure no specific role profile exists
            if hasattr(instance, 'teacher_profile'):
                instance.teacher_profile.delete()
            if hasattr(instance, 'student_profile'):
                instance.student_profile.delete()

    # After saving, update the _original_rol for the next save event
    # This needs to be handled outside the signal if the instance is saved elsewhere
    # For now, let's assume this signal is the primary point of update for rol
    instance._original_rol = instance.rol