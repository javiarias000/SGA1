from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from students.models import Student
from teachers.models import Teacher
from classes.models import Activity

def home_redirect_view(request):
    """Página principal o redirección según autenticación."""
    if not request.user.is_authenticated:
        total_students = Student.objects.filter(active=True).count()
        total_teachers = Teacher.objects.count()
        total_courses = Activity.objects.count()
        context = {
            'total_students': total_students or 150,
            'total_teachers': total_teachers or 25,
            'total_courses': total_courses or 50,
        }
        return render(request, 'home.html', context)

    if hasattr(request.user, 'teacher_profile'):
        return redirect('teacher_dashboard')
    elif hasattr(request.user, 'student_profile'):
        return redirect('student_dashboard')

    logout(request)
    messages.error(request, 'Tu cuenta no tiene un perfil asignado.')
    return redirect('login')
