from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings


class AttachUsuarioProfilesMiddleware:
    """Adjunta perfiles compatibilidad a request.user.

    Muchos views/middlewares asumen `request.user.teacher_profile` / `request.user.student_profile`.
    Con el modelo unificado, esos perfiles cuelgan de `request.user.usuario`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            usuario = getattr(user, 'usuario', None)
            if usuario:
                # Exponer usuario en request
                setattr(request, 'usuario', usuario)

                # Adjuntar perfiles (si existen)
                if not hasattr(user, 'teacher_profile'):
                    tp = getattr(usuario, 'teacher_profile', None)
                    if tp is not None:
                        setattr(user, 'teacher_profile', tp)

                if not hasattr(user, 'student_profile'):
                    sp = getattr(usuario, 'student_profile', None)
                    if sp is not None:
                        setattr(user, 'student_profile', sp)

        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """
    Middleware que verifica si un usuario debe cambiar su contraseña.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si el usuario no está autenticado, no hacemos nada.
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Si el usuario no tiene el perfil (por alguna razón), no hacemos nada.
        if not hasattr(request.user, 'profile'):
            return self.get_response(request)

        # Definir las URLs que están permitidas durante el proceso
        allowed_urls = [
            reverse('users:change_password'),
            reverse('users:logout')
        ]
        
        # Permitir acceso al admin
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Si el usuario debe cambiar la contraseña y no está en una URL permitida
        if request.user.profile.must_change_password and request.path not in allowed_urls:
            return redirect(reverse('users:change_password'))

        return self.get_response(request)
