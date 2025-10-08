from django.shortcuts import redirect
from functools import wraps

def teacher_required(function):
    """Decorador para asegurar que solo docentes accedan"""
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if hasattr(request.user, 'student_profile'):
            messages.error(request, '⚠️ No tienes permiso para acceder a esta área')
            return redirect('student_dashboard')
        
        if not hasattr(request.user, 'teacher_profile'):
            return redirect('login')
        
        return function(request, *args, **kwargs)
    return wrap


def student_required(function):
    """Decorador para asegurar que solo estudiantes accedan"""
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('student_login')
        
        if hasattr(request.user, 'teacher_profile'):
            messages.error(request, '⚠️ No tienes permiso para acceder a esta área')
            return redirect('dashboard')
        
        if not hasattr(request.user, 'student_profile'):
            return redirect('student_login')
        
        return function(request, *args, **kwargs)
    return wrap