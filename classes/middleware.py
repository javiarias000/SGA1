from django.shortcuts import redirect
from django.urls import reverse

class RoleBasedAccessMiddleware:
    """Middleware para controlar acceso según rol"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # URLs públicas (sin login)
        public_urls = [
            reverse('login'),
            reverse('register'),
            reverse('student_login'),
            reverse('student_register'),
            '/admin/',
        ]
        
        # Si la URL es pública, permitir acceso
        if any(request.path.startswith(url) for url in public_urls):
            response = self.get_response(request)
            return response
        
        # Si el usuario está autenticado
        if request.user.is_authenticated:
            # Verificar si es estudiante
            is_student = hasattr(request.user, 'student_profile')
            # Verificar si es docente
            is_teacher = hasattr(request.user, 'teacher_profile')
            
            # URLs para estudiantes
            student_urls = [
                '/student/dashboard/',
                '/student/classes/',
                '/student/grades/',
                '/student/attendance/',
                '/student/profile/',
            ]
            
            # Si es ESTUDIANTE tratando de acceder a área de DOCENTES
            if is_student and not any(request.path.startswith(url) for url in student_urls):
                return redirect('student_dashboard')
            
            # Si es DOCENTE tratando de acceder a área de ESTUDIANTES
            if is_teacher and any(request.path.startswith(url) for url in student_urls):
                return redirect('dashboard')
        
        response = self.get_response(request)
        return response