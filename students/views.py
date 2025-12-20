from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg

# Importar decorador de users
from users.views.decorators import student_required

# Importar modelos
from students.models import Student
from classes.models import Activity, Clase, Enrollment, Subject, Deber, DeberEntrega, Calificacion, Asistencia, CalificacionParcial


# ============================================
# DASHBOARD ESTUDIANTE
# ============================================
@login_required
@student_required
def student_dashboard_view(request):
    """Dashboard para estudiantes con inscripción dinámica."""
    try:
        estudiante = request.user.student_profile
    except AttributeError:
        messages.error(request, 'No se encontró tu perfil de estudiante')
        return redirect('users:login')

    # Clases ya matriculadas
    mis_clases_ids = Enrollment.objects.filter(
        estudiante=estudiante,
        estado='ACTIVO'
    ).values_list('clase_id', flat=True)
    
    mis_clases = Clase.objects.filter(id__in=mis_clases_ids)

    # Clases disponibles para el grado del estudiante en el ciclo lectivo actual
    clases_disponibles = []
    if estudiante.grade_level:
        clases_disponibles = Clase.objects.filter(
            active=True,
            grade_level=estudiante.grade_level,
            ciclo_lectivo='2025-2026' # Asumiendo ciclo lectivo actual
        ).exclude(id__in=mis_clases_ids)

    # Últimas actividades y calificaciones
    mis_actividades = Activity.objects.filter(student=estudiante).order_by('-date')[:5]
    mis_calificaciones = CalificacionParcial.objects.filter(student=estudiante).order_by('-fecha_actualizacion')[:5]
    
    # Estadísticas
    total_clases = mis_clases.count()
    promedio = CalificacionParcial.calcular_promedio_general(estudiante)
    subjects = estudiante.get_subjects()

    context = {
        'student': estudiante,
        'recent_activities': mis_actividades,
        'recent_grades': mis_calificaciones,
        'promedio': round(promedio, 2),
        'subjects': subjects,
        'total_classes': total_clases,
        'clases_disponibles': clases_disponibles,
        'mis_clases': mis_clases,
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
    
    # Agrupar por materia
    activities_by_subject = {}
    for activity in activities:
        if activity.subject not in activities_by_subject:
            activities_by_subject[activity.subject] = []
        activities_by_subject[activity.subject].append(activity)
    
    # Obtener clases disponibles para matricularse
    # Clases activas globales (independiente del docente), excluyendo ya matriculadas
    clases_candidatas = Clase.objects.filter(active=True).exclude(
        enrollments__estudiante=student,
        enrollments__estado='ACTIVO'
    )
    # Aptitud por grado y cupo
    clases_disponibles = [c for c in clases_candidatas if student.can_take_subject(c.subject) and c.has_space()]
    
    # Obtener clases matriculadas
    mis_clases = Clase.objects.filter(
        enrollments__estudiante=student,
        enrollments__estado='ACTIVO'
    )
    
    
    return render(request, 'students/classes.html', {
        'student': student,
        'activities': activities,
        'activities_by_subject': activities_by_subject,
        'subject_filter': subject_filter,
        'clases_disponibles': clases_disponibles,
        'mis_clases': mis_clases,
    })


# ============================================
# MATRÍCULA EN CLASES
# ============================================

@student_required
def student_enroll_view(request, clase_id):
    """Permite que el estudiante se matricule a una clase"""
    student = request.user.student_profile
    clase = get_object_or_404(Clase, id=clase_id, active=True)

    # Elegibilidad por materia
    if not student.can_take_subject(clase.subject):
        messages.error(request, "No cumples los requisitos para esta materia según tu grado.")
    # Verificar si ya está matriculado
    elif Enrollment.objects.filter(estudiante=student, clase=clase, estado='ACTIVO').exists():
        messages.info(request, "Ya estás matriculado en esta clase.")
    elif not clase.has_space():
        messages.error(request, "Esta clase ya está llena.")
    else:
        # Asigna el docente_base de la clase al enrollment por defecto
        docente_asignado = clase.docente_base
        Enrollment.objects.create(
            estudiante=student, 
            clase=clase, 
            docente=docente_asignado,
            estado='ACTIVO'
        )
        messages.success(request, f"Te has matriculado correctamente en {clase.name}")

    return redirect('students:student_dashboard') # Redirigir a dashboard para ver los cambios


# ============================================
# CALIFICACIONES DEL ESTUDIANTE
# ============================================

@login_required
@student_required
def student_grades_view(request):
    """Placeholder view for student grades."""
    return render(request, 'students/grades.html')


# ============================================
# DEBERES DEL ESTUDIANTE
# ============================================

@login_required
@student_required
def student_homework_view(request):
    """Vista para que los estudiantes vean sus deberes"""
    try:
        student = request.user.student_profile
    except AttributeError:
        messages.error(request, 'No se encontró tu perfil de estudiante')
        return redirect('users:login')

    # Obtener los IDs de las clases en las que el estudiante está matriculado
    enrolled_class_ids = student.enrollments.filter(estado='ACTIVO').values_list('clase__id', flat=True)

    # Obtener deberes asignados a las clases del estudiante o directamente al estudiante
    homework_assigned_to_classes = Deber.objects.filter(
        clase__id__in=enrolled_class_ids
    ).distinct()
    
    homework_directly_assigned = Deber.objects.filter(
        estudiantes_especificos=student.usuario
    ).distinct()

    # Combinar y eliminar duplicados
    all_homework = (homework_assigned_to_classes | homework_directly_assigned).order_by('-fecha_entrega')

    # Para cada deber, obtener el estado de entrega del estudiante
    homework_with_submission_status = []
    for hw in all_homework:
        submission = DeberEntrega.objects.filter(deber=hw, estudiante=student.usuario).first()
        homework_with_submission_status.append({
            'homework': hw,
            'submission': submission,
            'is_submitted': submission is not None,
            'is_graded': submission and submission.calificacion is not None,
            'status': submission.get_estado_display() if submission else 'No entregado',
            'calificacion': submission.calificacion if submission else None,
        })

    context = {
        'student': student,
        'homework_list': homework_with_submission_status,
    }
    return render(request, 'students/homework.html', context)


# ============================================
# PERFIL DEL ESTUDIANTE
# ============================================

@student_required
def student_profile_view(request):
    """Perfil del estudiante"""
    student = request.user.student_profile

    if request.method == 'POST' and request.FILES.get('photo'):
        student.photo = request.FILES['photo']
        student.save()
        messages.success(request, 'Foto de perfil actualizada')
        return redirect('students:profile')
    
    # Estadísticas generales
    total_clases = Activity.objects.filter(student=student).count()
    total_asistencias = Asistencia.objects.filter(inscripcion__estudiante=student.usuario).count()
    promedio = CalificacionParcial.calcular_promedio_general(student)
    
    # Materias que está cursando
    materias = student.get_subjects()
    
    # Clases matriculadas
    clases_matriculadas = Clase.objects.filter(
        enrollments__estudiante=student,
        enrollments__estado='ACTIVO'
    )
    
    return render(request, 'students/profile.html', {
        'student': student,
        'total_clases': total_clases,
        'total_asistencias': total_asistencias,
        'promedio': round(promedio, 2),
        'materias': materias,
        'clases_matriculadas': clases_matriculadas,
    })