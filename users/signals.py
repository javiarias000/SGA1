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
    Creates or updates a Usuario instance for every User, ensuring a corresponding
    Usuario profile is linked or created. Handles cases where Usuario might
    exist by email before being linked to a new User instance.
    """
    usuario_defaults = {
        'nombre': f"{instance.first_name} {instance.last_name}".strip() or instance.username,
        'email': instance.email,
    }

    # Determine desired role based on is_staff status
    if instance.is_staff:
        desired_rol = Usuario.Rol.DOCENTE
    else:
        desired_rol = Usuario.Rol.ESTUDIANTE

    # Attempt to get or create the Usuario profile
    if created:
        # For new User instances, try to find an existing Usuario by auth_user or email
        # and link it, or create a new one.
        usuario = Usuario.objects.filter(auth_user=instance).first()
        if not usuario and instance.email:
            usuario = Usuario.objects.filter(email=instance.email).first()

        if usuario:
            # If an existing Usuario was found, update it to link to this new User
            # and update its fields.
            if not usuario.auth_user: # If not already linked
                usuario.auth_user = instance
            usuario.nombre = usuario_defaults['nombre']
            usuario.email = usuario_defaults['email'] # Ensure email is consistent
            # Update role only if it's PENDIENTE or inconsistent with is_staff
            if usuario.rol == Usuario.Rol.PENDIENTE or \
               (instance.is_staff and usuario.rol != Usuario.Rol.DOCENTE) or \
               (not instance.is_staff and usuario.rol != Usuario.Rol.ESTUDIANTE and usuario.rol != Usuario.Rol.DOCENTE):
                usuario.rol = desired_rol
            usuario.save()
        else:
            # No existing Usuario found, create a new one
            Usuario.objects.create(auth_user=instance, rol=desired_rol, **usuario_defaults)
    else:
        # For existing User instances, ensure Usuario exists and is updated
        usuario, created_usuario = Usuario.objects.get_or_create(auth_user=instance, defaults={
            'rol': desired_rol, # Set default role for newly created Usuario via get_or_create
            **usuario_defaults
        })
        if not created_usuario:
            # If Usuario already existed for this auth_user, update its fields
            if usuario.nombre != usuario_defaults['nombre']:
                usuario.nombre = usuario_defaults['nombre']
            
            new_email = usuario_defaults['email']
            if usuario.email != new_email:
                # Check if the new email is already taken by another Usuario
                if Usuario.objects.filter(email=new_email).exclude(pk=usuario.pk).exists():
                    # Optional: Log this event or send a message, but for now, just don't update the email
                    # to prevent the IntegrityError.
                    pass
                else:
                    usuario.email = new_email

            # Update role if it's PENDIENTE or inconsistent with is_staff
            if usuario.rol == Usuario.Rol.PENDIENTE or \
               (instance.is_staff and usuario.rol != Usuario.Rol.DOCENTE) or \
               (not instance.is_staff and usuario.rol != Usuario.Rol.ESTUDIANTE and usuario.rol != Usuario.Rol.DOCENTE):
                usuario.rol = desired_rol
            usuario.save()

@receiver(post_save, sender=Usuario)
def create_or_update_role_profile(sender, instance, created, **kwargs):
    """
    Creates or updates Teacher or Student profile based on Usuario's rol.
    Also handles deletion of old role profiles if rol changes.
    """
    # To safely get the original rol, fetch from DB if not created
    original_rol = None
    if not created:
        try:
            original_rol = Usuario.objects.get(pk=instance.pk).rol
        except Usuario.DoesNotExist:
            pass # Should not happen if not created

    rol_changed = created or (original_rol is not None and original_rol != instance.rol)

    if rol_changed:
        # Handle deletion of old profile if rol has changed
        if original_rol == Usuario.Rol.DOCENTE and hasattr(instance, 'teacher_profile'):
            instance.teacher_profile.delete()
        elif original_rol == Usuario.Rol.ESTUDIANTE and hasattr(instance, 'student_profile'):
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