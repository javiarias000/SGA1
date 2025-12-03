from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from .routes import student_paths, teacher_paths


def safe_reverse(name, default=None):
    """
    Intenta hacer reverse(name). Si no existe la URL devuelve default.
    Evita que NoReverseMatch rompa la petición.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return default


class RoleBasedAccessMiddleware:
    """Middleware para controlar acceso según rol (robusto frente a nombres de URL ausentes)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Evitar ejecutar lógica para peticiones de archivos estáticos u cosas sin path
        path = request.path or "/"

        # Permitir admin, estáticos, media y las URL de reseteo de contraseña
        if (path.startswith('/admin/') or 
            path.startswith('/static/') or 
            path.startswith('/media/') or
            path.startswith('/reset/')):
            return self.get_response(request)

        # URLs públicas
        public_urls = [
            safe_reverse('home', default='/'),
            safe_reverse('users:login', default='/users/login/'),
            safe_reverse('users:logout', default='/users/logout/'),
            safe_reverse('users:register', default='/users/register/'),
            safe_reverse('users:password_reset', default='/users/password_reset/'),
            safe_reverse('users:password_reset_done', default='/users/password_reset/done/'),
        ]
        # Asegura que public_urls contenga strings válidos
        public_urls = [u for u in public_urls if u]

        # Si la ruta es pública o es admin/static/media, dejamos pasar
        if path in public_urls:
            return self.get_response(request)

        user = getattr(request, 'user', None)
        is_authenticated = user.is_authenticated if user else False

        # Si no está autenticado, lo puedes redirigir al login (opcional)
        if not is_authenticated:
            login_url = safe_reverse('users:login', default='/users/login/')
            return redirect(login_url)

        # Determinar rol (ajusta según tu modelo de usuario)
        # Aquí usamos atributos tipo student_profile / teacher_profile como en tus mensajes previos
        is_student = hasattr(user, 'student_profile')
        is_teacher = hasattr(user, 'teacher_profile')

        # Solo aplicar redirecciones cruzadas cuando el usuario tiene un único rol
        if is_student and not is_teacher:
            # Estudiante no debe entrar a área de docentes
            if any(path.startswith(p) for p in teacher_paths):
                student_dashboard = safe_reverse('students:student_dashboard', default='/students/dashboard/')
                if path != student_dashboard:
                    return redirect(student_dashboard)

        if is_teacher and not is_student:
            # Docente no debe entrar a área de estudiantes
            if any(path.startswith(p) for p in student_paths):
                teacher_dashboard = safe_reverse('teachers:teacher_dashboard', default='/teachers/dashboard/')
                if path != teacher_dashboard:
                    return redirect(teacher_dashboard)

        # Si no aplica ninguna regla, continuar
        response = self.get_response(request)
        return response
