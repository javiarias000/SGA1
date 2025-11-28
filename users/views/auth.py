from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from teachers.models import Teacher

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from teachers.models import Teacher
from django.db import IntegrityError


def unified_login_view(request):
    """Login unificado para docentes y estudiantes."""
    # Resolver next (admite GET o POST)
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.user.is_authenticated:
        # Si ya está logueado, respeta "next" si apunta a un área válida
        if next_url and (next_url.startswith('/students/') or next_url.startswith('/teachers/')):
            return redirect(next_url)
        # Por defecto, prioriza el dashboard de estudiante si existe
        if hasattr(request.user, 'student_profile'):
            return redirect('students:student_dashboard')
        elif hasattr(request.user, 'teacher_profile'):
            return redirect('teachers:teacher_dashboard')
        else:
            logout(request)
            messages.warning(request, 'Tu cuenta no tiene un perfil asignado.')
            return redirect('users:login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Si viene desde una URL protegida, respeta ese destino
            if next_url and (next_url.startswith('/students/') or next_url.startswith('/teachers/')):
                return redirect(next_url)
            # Por defecto, prioriza estudiante si existe, luego docente
            if hasattr(user, 'student_profile'):
                return redirect('students:student_dashboard')
            elif hasattr(user, 'teacher_profile'):
                return redirect('teachers:teacher_dashboard')
            else:
                logout(request)
                messages.error(request, 'Tu cuenta no tiene perfil asignado.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'users/login.html')



def unified_register_view(request):
    from students.models import Student
    """Vista de registro unificada para docentes y estudiantes."""
    if request.method == 'POST':
        role = request.POST.get('role')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'users/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya existe.')
            return render(request, 'users/register.html')

        if role == 'teacher':
            phone = request.POST.get('phone', '')
            specialization = request.POST.get('specialization', '')

            user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name
            )
            Teacher.objects.create(user=user, phone=phone, specialization=specialization)
            messages.success(request, 'Docente registrado correctamente.')
            return redirect('users:login')

        elif role == 'student':
            student_code = request.POST.get('student_code', '').strip()
            try:
                student = Student.objects.get(registration_code=student_code, active=True)
            except (Student.DoesNotExist, ValueError):
                messages.error(request, 'Código de estudiante inválido.')
                return render(request, 'users/register.html')

            if student.user:
                messages.error(request, 'Este estudiante ya tiene cuenta.')
                return render(request, 'users/register.html')

            user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name
            )
            student.user = user
            student.save()
            messages.success(request, 'Estudiante registrado correctamente.')
            return redirect('users:login')

        else:
            messages.error(request, 'Debes seleccionar un tipo de registro.')

    return render(request, 'users/register.html')




def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('home')
