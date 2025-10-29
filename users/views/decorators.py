from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout


def teacher_required(view_func):
    """Decorador para vistas que requieren ser docente"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión como docente')
            return redirect('users:login')
        
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, '⚠️ No tienes permisos de docente')
            logout(request)
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def student_required(view_func):
    """Decorador para vistas que requieren ser estudiante"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión como estudiante')
            return redirect('users:login')
        
        if not hasattr(request.user, 'student_profile'):
            messages.error(request, '⚠️ No tienes permisos de estudiante')
            logout(request)
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
