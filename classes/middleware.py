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

        # URLs públicas (si quieres usar nombres, resuélvelos de forma segura)
        public_urls = [
            safe_reverse('login', default='/login/'),
            safe_reverse('logout', default='/logout/'),
            safe_reverse('register', default='/register/'),  # si no existe, usamos '/register/' como fallback
        ]
        # Asegura que public_urls contenga strings válidos
        public_urls = [u for u in public_urls if u]

        # Si la ruta es pública, dejamos pasar
        if path in public_urls:
            return self.get_response(request)

        user = getattr(request, 'user', None)
        is_authenticated = user.is_authenticated if user else False

        # Si no está autenticado, lo puedes redirigir al login (opcional)
        if not is_authenticated:
            login_url = safe_reverse('login', default='/login/')
            return redirect(login_url)

        # Determinar rol (ajusta según tu modelo de usuario)
        # Aquí usamos atributos tipo student_profile / teacher_profile como en tus mensajes previos
        is_student = hasattr(user, 'student_profile')
        is_teacher = hasattr(user, 'teacher_profile')

        # Protección por zonas: si las listas student_paths/teacher_paths contienen prefijos (ej: '/teacher/')
        # comparamos con request.path.startswith(...)
        if is_student:
            # Si estudiante intenta acceder a área de docente => llevar al dashboard del estudiante
            if any(path.startswith(p) for p in teacher_paths):
                student_dashboard = safe_reverse('student:dashboard', default='/student/dashboard/')
                # Evitar bucle: si ya está en el dashboard no redirigir
                if path != student_dashboard:
                    return redirect(student_dashboard)

        if is_teacher:
            # Si docente intenta acceder a área de estudiante => llevar al dashboard del docente
            if any(path.startswith(p) for p in student_paths):
                teacher_dashboard = safe_reverse('teacher:dashboard', default='/teacher/dashboard/')
                if path != teacher_dashboard:
                    return redirect(teacher_dashboard)

        # Si no aplica ninguna regla, continuar
        response = self.get_response(request)
        return response
