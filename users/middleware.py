from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

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
