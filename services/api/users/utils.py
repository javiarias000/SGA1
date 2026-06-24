import string
import secrets
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile

def generate_temporary_password(length=12):
    """Genera una contraseña alfanumérica aleatoria."""
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def send_welcome_email_with_temporary_password(user: User):
    """
    Genera una contraseña temporal, la asigna al usuario y envía un correo
    de bienvenida.
    """
    if not isinstance(user, User):
        raise TypeError("Se esperaba un objeto User de Django.")

    # Generar contraseña temporal
    temp_password = generate_temporary_password()

    # Obtener o crear el perfil del usuario para evitar errores con usuarios antiguos
    profile, created = Profile.objects.get_or_create(user=user)
    
    # Asignar contraseña y forzar cambio
    user.set_password(temp_password)
    profile.must_change_password = True
    user.save()
    profile.save()

    # Preparar y enviar correo
    subject = "Bienvenido al Sistema de Gestión Académica"
    context = {
        'user': user,
        'username': user.username,
        'password': temp_password,
        'login_url': settings.LOGIN_URL or '/users/login/',
    }
    html_message = render_to_string('emails/welcome_email.html', context)
    plain_message = f"Hola {user.get_full_name() or user.username},\n\n" \
                    f"Bienvenido/a al Sistema de Gestión Académica.\n\n" \
                    f"Tu nombre de usuario es: {user.username}\n" \
                    f"Tu contraseña temporal es: {temp_password}\n\n" \
                    f"Por favor, inicia sesión y cambia tu contraseña.\n"

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message
    )

    print(f"Correo de bienvenida enviado (en consola) a {user.email}")
    return True
