from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Avg
from functools import wraps
from django.contrib.auth.models import User

from classes.models import Teacher, Student, Activity, Grade, Attendance, Clase
from classes.forms import StudentForm, ActivityForm, GradeForm, AttendanceForm, TeacherProfileForm


# ============================================
# DECORADOR STUDENT
# ============================================

def student_required(view_func):
    """Decorador para vistas que requieren ser estudiante"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Debes iniciar sesión como estudiante')
            return redirect('student_login')
        
        if not hasattr(request.user, 'student_profile'):
            messages.error(request, '⚠️ No tienes permisos de estudiante')
            logout(request)
            return redirect('student_login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================
# LOGIN ESTUDIANTE
# ============================================

def student_login_view(request):
    """Vista de login para estudiantes"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('student_dashboard')
        elif hasattr(request.user, 'teacher_profile'):
            messages.info(request, 'Ya tienes sesión como docente.')
            return redirect('teacher_dashboard')
        else:
            logout(request)
            messages.warning(request, 'Tu cuenta no tiene perfil asociado.')
            return redirect('student_login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not hasattr(user, 'student_profile'):
                messages.error(request, '⚠️ Esta cuenta no es de estudiante. Usa el login de docentes.')
            else:
                login(request, user)
                messages.success(request, f'¡Bienvenido {user.student_profile.name}!')
                return redirect('student_dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')

    return render(request, 'students/login.html')


def student_register_view(request):
    """Vista para que estudiantes creen su cuenta"""
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('student_dashboard')
        return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        student_code = request.POST.get('student_code')
        
        if not all([username, email, password1, password2, student_code]):
            messages.error(request, 'Por favor completa todos los campos')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden')
        elif len(password1) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres')
        else:
            try:
                student = Student.objects.get(id=int(student_code), active=True)
            except (Student.DoesNotExist, ValueError):
                messages.error(request, 'Código de estudiante inválido.')
                return render(request, 'students/register.html')
            
            if student.user:
                messages.error(request, 'Este estudiante ya tiene una cuenta creada.')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'El nombre de usuario ya está en uso')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'El correo electrónico ya está registrado')
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=student.name.split()[0],
                    last_name=' '.join(student.name.split()[1:]) if len(student.name.split()) > 1 else ''
                )
                student.user = user
                student.save()
                messages.success(request, '¡Cuenta creada exitosamente! Ya puedes iniciar sesión')
                return redirect('student_login')
    
    return render(request, 'students/register.html')


def student_logout_view(request):
    """Cerrar sesión"""
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente')
    return redirect('student_login')


# ============================================
# DASHBOARD ESTUDIANTE
# ============================================

@student_required
def student_dashboard_view(request):
    """Dashboard para estudiantes"""
    try:
        estudiante = request.user.student_profile
    except AttributeError:
        messages.error(request, 'No se encontró tu perfil de estudiante')
        logout(request)
        return redirect('student_login')
    
    # Obtener las últimas actividades/clases del estudiante
    mis_actividades = Activity.objects.filter(
        student=estudiante
    ).order_by('-date')[:10]
    
    # Obtener calificaciones
    mis_calificaciones = Grade.objects.filter(
        student=estudiante
    ).order_by('-date')[:5]
    
    # Obtener asistencias recientes
    mis_asistencias = Attendance.objects.filter(
        student=estudiante
    ).order_by('-date')[:10]
    
    # Calcular estadísticas
    total_clases = Activity.objects.filter(student=estudiante).count()
    total_asistencias = Attendance.objects.filter(student=estudiante).count()
    presente_count = Attendance.objects.filter(
        student=estudiante, 
        status='Presente'
    ).count()
    
    # Calcular promedio de calificaciones
    promedio = Grade.objects.filter(student=estudiante).aggregate(
        promedio=Avg('score')
    )['promedio'] or 0
    
    # Calcular porcentaje de asistencia
    porcentaje_asistencia = 0
    if total_asistencias > 0:
        porcentaje_asistencia = (presente_count / total_asistencias) * 100
    
    # Agrupar actividades por materia
    actividades_por_materia = {}
    for actividad in mis_actividades:
        if actividad.subject not in actividades_por_materia:
            actividades_por_materia[actividad.subject] = []
        actividades_por_materia[actividad.subject].append(actividad)
    
    stats = {
        'total_clases': total_clases,
        'total_asistencias': total_asistencias,
        'promedio': round(promedio, 2),
        'porcentaje_asistencia': round(porcentaje_asistencia, 1),
        'presente_count': presente_count,
    }
    
    context = {
        'estudiante': estudiante,
        'mis_actividades': mis_actividades,
        'mis_calificaciones': mis_calificaciones,
        'mis_asistencias': mis_asistencias,
        'actividades_por_materia': actividades_por_materia,
        'stats': stats,
    }
    
    return render(request, 'students/dashboard.html', context)


# ============================================
# CLASES DEL ESTUDIANTE
# ============================================

@student_required
def student_classes_view(request):
    """Clases del estudiante"""
    student = request.user.student_profile
    subject_filter = request.GET.get('subject', '')
    
    activities = Activity.objects.filter(student=student).order_by('-date')
    
    if subject_filter:
        activities = activities.filter(subject=subject_filter)
    
    activities_by_subject = {}
    for activity in activities:
        if activity.subject not in activities_by_subject:
            activities_by_subject[activity.subject] = []
        activities_by_subject[activity.subject].append(activity)
    
    return render(request, 'students/classes.html', {
        'student': student,
        'activities': activities,
        'activities_by_subject': activities_by_subject,
        'subject_filter': subject_filter,
    })


# ============================================
# CALIFICACIONES DEL ESTUDIANTE
# ============================================

@student_required
def student_grades_view(request):
    """Calificaciones del estudiante"""
    student = request.user.student_profile
    grades = Grade.objects.filter(student=student).order_by('subject', '-date')
    
    grades_by_subject = {}
    for grade in grades:
        if grade.subject not in grades_by_subject:
            grades_by_subject[grade.subject] = {
                'grades': [],
                'average': 0
            }
        grades_by_subject[grade.subject]['grades'].append(grade)
    
    for subject in grades_by_subject:
        subject_grades = grades_by_subject[subject]['grades']
        if subject_grades:
            avg = sum(float(g.score) for g in subject_grades) / len(subject_grades)
            grades_by_subject[subject]['average'] = round(avg, 2)
    
    promedio_general = 0
    if grades:
        promedio_general = sum(float(g.score) for g in grades) / len(grades)
        promedio_general = round(promedio_general, 2)
    
    return render(request, 'students/grades.html', {
        'student': student,
        'grades_by_subject': grades_by_subject,
        'promedio_general': promedio_general,
    })


# ============================================
# ASISTENCIA DEL ESTUDIANTE
# ============================================

@student_required
def student_attendance_view(request):
    """Asistencia del estudiante"""
    student = request.user.student_profile
    attendances = Attendance.objects.filter(student=student).order_by('-date')
    
    total = attendances.count()
    presente = attendances.filter(status='Presente').count()
    ausente = attendances.filter(status='Ausente').count()
    tardanza = attendances.filter(status='Tardanza').count()
    justificado = attendances.filter(status='Justificado').count()
    
    presente_pct = (presente / total * 100) if total > 0 else 0
    
    return render(request, 'students/attendance.html', {
        'student': student,
        'attendances': attendances,
        'total': total,
        'presente': presente,
        'ausente': ausente,
        'tardanza': tardanza,
        'justificado': justificado,
        'presente_pct': round(presente_pct, 1),
    })


# ============================================
# PERFIL DEL ESTUDIANTE
# ============================================

@student_required
def student_profile_view(request):
    """Perfil del estudiante"""
    student = request.user.student_profile
    
    return render(request, 'students/profile.html', {
        'student': student,
    })


# ============================================
# MATRÍCULA EN CLASES
# ============================================

@student_required
def student_enroll_view(request, clase_id):
    """Permite que el estudiante se matricule a una clase"""
    from classes.models import Enrollment
    
    student = request.user.student_profile
    clase = get_object_or_404(Clase, id=clase_id)

    # Verificar si ya está matriculado
    if Enrollment.objects.filter(student=student, clase=clase).exists():
        messages.info(request, "Ya estás matriculado en esta clase.")
    else:
        Enrollment.objects.create(student=student, clase=clase)
        messages.success(request, f"Te has matriculado correctamente en {clase.name}")

    return redirect('student_classes')