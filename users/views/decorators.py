from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout

def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión como docente.')
            return redirect('login')
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, 'No tienes permisos de docente.')
            logout(request)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def student_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión como estudiante.')
            return redirect('login')
        if not hasattr(request.user, 'student_profile'):
            messages.error(request, 'No tienes permisos de estudiante.')
            logout(request)
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped
