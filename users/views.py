from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg

# Modelos que usas
from classes.models import Clase, Activity, Attendance




# ============================================
# DASHBOARD PRINCIPAL
# ============================================

@login_required
def dashboard(request):
    """Redirige según rol del usuario"""
    user = request.user
    if hasattr(user, 'is_teacher') and user.is_teacher:
        return redirect('teacher_dashboard')
    elif hasattr(user, 'is_student') and user.is_student:
        return redirect('student_dashboard')
    return render(request, 'no_permission.html', {'mensaje': 'Rol no identificado'})


# ============================================
# DASHBOARD DOCENTE
# ============================================

@teacher_required
def teacher_dashboard_view(request):
    teacher = request.user.teacher_profile
    clases_teoricas = Clase.objects.filter(teacher=teacher).order_by('-fecha')
    
    clases_con_datos = []
    clases_registradas_count = 0

    for clase in clases_teoricas:
        try:
            registro = clase.registros.get()
            asistencias_count = registro.asistencias.count()
            total_estudiantes = clase.estudiantes.count()
            clases_con_datos.append({
                'clase': clase,
                'tiene_registro': True,
                'asistencias_registradas': asistencias_count,
                'total_estudiantes': total_estudiantes,
                'porcentaje': int((asistencias_count / total_estudiantes * 100)) if total_estudiantes > 0 else 0
            })
        except Activity.DoesNotExist:
            clases_con_datos.append({
                'clase': clase,
                'tiene_registro': False,
                'total_estudiantes': clase.estudiantes.count()
            })
    
    total_clases = clases_teoricas.count()
    clases_number = Activity.objects.filter(clase__teacher=teacher).count()
    
    context = {
        'teacher': teacher,
        'clases_teoricas': clases_con_datos,
        'total_clases': total_clases,
        'clases_registradas': clases_registradas_count,
        'clases_pendientes': total_clases - clases_registradas_count,
        'total_estudiantes': teacher.students.count(),
    }
    
    return render(request, 'dashboard.html', context)
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
    from django.db.models import Avg
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
    
    return render(request, 'classes/student/dashboard.html', context)