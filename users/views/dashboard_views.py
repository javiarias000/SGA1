from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg

# Importar decoradores
from users.views.decorators import teacher_required, student_required

# Importar modelos
from classes.models import Clase, Activity, Attendance, CalificacionParcial


# ============================================
# DASHBOARD PRINCIPAL (Redirección)
# ============================================

@login_required
def dashboard(request):
    """Redirige según rol del usuario"""
    user = request.user
    
    # Verificar si es teacher
    if hasattr(user, 'teacher_profile'):
        return redirect('teachers:teacher_dashboard')
    
    # Verificar si es student
    elif hasattr(user, 'student_profile'):
        return redirect('students:student_dashboard')
    
    # Si no tiene ningún perfil
    messages.error(request, 'Tu cuenta no tiene un perfil asignado')
    logout(request)
    return redirect('users:login')


# ============================================
# DASHBOARD DOCENTE
# ============================================

@teacher_required
def teacher_dashboard_view(request):
    """Dashboard para docentes"""
    teacher = request.user.teacher_profile
    clases_teoricas = Clase.objects.filter(teacher=teacher, active=True).order_by('-fecha')
    
    clases_con_datos = []
    clases_registradas_count = 0

    for clase in clases_teoricas:
        # Obtener enrollments activos
        enrollments = clase.enrollments.filter(active=True)
        total_estudiantes = enrollments.count()
        
        # Verificar si tiene actividades registradas
        tiene_actividades = Activity.objects.filter(clase=clase).exists()
        
        clases_con_datos.append({
            'clase': clase,
            'tiene_registro': tiene_actividades,
            'total_estudiantes': total_estudiantes,
        })
        
        if tiene_actividades:
            clases_registradas_count += 1
    
    total_clases = clases_teoricas.count()
    
    context = {
        'teacher': teacher,
        'clases_teoricas': clases_con_datos,
        'total_clases': total_clases,
        'clases_registradas': clases_registradas_count,
        'clases_pendientes': total_clases - clases_registradas_count,
        'total_estudiantes': teacher.students.filter(active=True).count(),
    }
    
    return render(request, 'teachers/dashboard.html', context)


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
        return redirect('users:login')
    
    # Obtener las últimas actividades/clases del estudiante
    mis_actividades = Activity.objects.filter(
        student=estudiante
    ).order_by('-date')[:10]
    
    # Obtener calificaciones
    mis_calificaciones = CalificacionParcial.objects.filter(
        student=estudiante
    ).order_by('-fecha_registro')[:5]
    
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
    promedio = CalificacionParcial.calcular_promedio_general(estudiante)
    
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
