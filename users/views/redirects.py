from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from teachers.models import Teacher  
from classes.models import Activity
from students.models import Student


def home_redirect_view(request):
    if not request.user.is_authenticated:
        total_students = Student.objects.filter(active=True).count()
        total_teachers = Teacher.objects.count()
        total_courses = Activity.objects.count()
        context = {
            'total_students': total_students or 150,
            'total_teachers': total_teachers or 25,
            'total_courses': total_courses or 50,
        }
        return render(request, 'login.html', context)

    # Si tiene ambos perfiles, prioriza vista de estudiante por defecto
    if hasattr(request.user, 'student_profile'):
        return redirect('students:student_dashboard')
    elif hasattr(request.user, 'teacher_profile'):
        return redirect('teachers:teacher_dashboard')

    logout(request)
    messages.error(request, 'Tu cuenta no tiene un perfil asignado.')
    return redirect('users:login')
