from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg

from users.views.decorators import student_required
from students.models import Student
from classes.models import (
    Activity, Clase, Enrollment, Deber, DeberEntrega,
    Calificacion, Asistencia, CalificacionParcial,
)


def _usuario(student):
    """Devuelve el Usuario asociado a un Student (Enrollment lo necesita)."""
    return getattr(student, 'usuario', None)


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@login_required
@student_required
def student_dashboard_view(request):
    """Dashboard para estudiantes con inscripción dinámica."""
    try:
        estudiante = request.user.student_profile
    except AttributeError:
        messages.error(request, 'No se encontró tu perfil de estudiante')
        return redirect('users:login')

    usr = _usuario(estudiante)

    mis_clases_ids = (
        Enrollment.objects.filter(estudiante=usr, estado='ACTIVO')
        .values_list('clase_id', flat=True)
        if usr else []
    )

    mis_clases = Clase.objects.filter(id__in=mis_clases_ids)

    clases_disponibles = []
    docente_tutor = None
    if estudiante.grade_level:
        clases_disponibles = Clase.objects.filter(
            active=True,
            grade_level=estudiante.grade_level,
            ciclo_lectivo='2025-2026',
        ).exclude(id__in=mis_clases_ids)
        if estudiante.grade_level.docente_tutor:
            docente_tutor = estudiante.grade_level.docente_tutor

    mis_actividades = Activity.objects.filter(student=estudiante).order_by('-date')[:5]
    mis_calificaciones = (
        CalificacionParcial.objects.filter(student=estudiante)
        .order_by('-fecha_actualizacion')[:5]
    )

    total_clases = mis_clases.count()
    promedio = CalificacionParcial.calcular_promedio_general(estudiante)
    subjects = estudiante.get_subjects()

    return render(request, 'students/dashboard.html', {
        'student': estudiante,
        'docente_tutor': docente_tutor,
        'recent_activities': mis_actividades,
        'recent_grades': mis_calificaciones,
        'promedio': round(promedio, 2),
        'subjects': subjects,
        'total_classes': total_clases,
        'clases_disponibles': clases_disponibles,
        'mis_clases': mis_clases,
    })


# ─── CLASES ───────────────────────────────────────────────────────────────────

@student_required
def student_classes_view(request):
    """Clases del estudiante."""
    student = request.user.student_profile
    usr = _usuario(student)
    subject_filter = request.GET.get('subject', '')

    activities = Activity.objects.filter(student=student).order_by('-date')
    if subject_filter:
        activities = activities.filter(subject=subject_filter)

    activities_by_subject = {}
    for activity in activities:
        activities_by_subject.setdefault(activity.subject, []).append(activity)

    if usr:
        mis_clases = Clase.objects.filter(
            enrollments__estudiante=usr, enrollments__estado='ACTIVO'
        )
        clases_candidatas = Clase.objects.filter(active=True).exclude(
            enrollments__estudiante=usr, enrollments__estado='ACTIVO'
        )
    else:
        mis_clases = Clase.objects.none()
        clases_candidatas = Clase.objects.filter(active=True)

    clases_disponibles = [
        c for c in clases_candidatas
        if student.can_take_subject(c.subject) and c.has_space()
    ]

    return render(request, 'students/classes.html', {
        'student': student,
        'activities': activities,
        'activities_by_subject': activities_by_subject,
        'subject_filter': subject_filter,
        'clases_disponibles': clases_disponibles,
        'mis_clases': mis_clases,
    })


# ─── MATRÍCULA ────────────────────────────────────────────────────────────────

@student_required
def student_enroll_view(request, clase_id):
    """Permite que el estudiante se matricule a una clase."""
    student = request.user.student_profile
    usr = _usuario(student)
    clase = get_object_or_404(Clase, id=clase_id, active=True)

    if not student.can_take_subject(clase.subject):
        messages.error(request, "No cumples los requisitos para esta materia según tu grado.")
    elif usr and Enrollment.objects.filter(estudiante=usr, clase=clase, estado='ACTIVO').exists():
        messages.info(request, "Ya estás matriculado en esta clase.")
    elif not clase.has_space():
        messages.error(request, "Esta clase ya está llena.")
    else:
        Enrollment.objects.create(
            estudiante=usr,
            clase=clase,
            docente=clase.docente_base,
            estado='ACTIVO',
        )
        messages.success(request, f"Te has matriculado correctamente en {clase.name}")

    return redirect('students:student_dashboard')


# ─── CALIFICACIONES ───────────────────────────────────────────────────────────

@login_required
@student_required
def student_grades_view(request):
    """Calificaciones del estudiante."""
    student = request.user.student_profile
    parcial = request.GET.get('parcial', '')
    quimestre = request.GET.get('quimestre', '')

    qs = CalificacionParcial.objects.filter(student=student).select_related('subject', 'tipo_aporte')
    if parcial:
        qs = qs.filter(parcial=parcial)
    if quimestre:
        qs = qs.filter(quimestre=quimestre)
    qs = qs.order_by('subject__name', 'quimestre', 'parcial')

    # Agrupar por materia
    by_subject = {}
    for c in qs:
        sname = c.subject.name if c.subject else 'Sin materia'
        by_subject.setdefault(sname, []).append(c)

    promedio = CalificacionParcial.calcular_promedio_general(student)

    return render(request, 'students/grades.html', {
        'student': student,
        'by_subject': by_subject,
        'promedio': round(promedio, 2),
        'parcial': parcial,
        'quimestre': quimestre,
    })


# ─── ASISTENCIA ───────────────────────────────────────────────────────────────

@login_required
@student_required
def student_attendance_view(request):
    """Asistencia del estudiante."""
    student = request.user.student_profile
    usr = _usuario(student)

    asistencias = (
        Asistencia.objects.filter(inscripcion__estudiante=usr)
        .select_related('inscripcion__clase__subject')
        .order_by('-fecha')
        if usr else Asistencia.objects.none()
    )

    total = asistencias.count()
    presentes = asistencias.filter(estado='Presente').count()
    ausentes = asistencias.filter(estado='Ausente').count()
    justificados = asistencias.filter(estado='Justificado').count()
    porcentaje = round(presentes / total * 100, 1) if total else 0

    return render(request, 'students/attendance.html', {
        'student': student,
        'asistencias': asistencias,
        'total': total,
        # nombres que usa el template
        'presente': presentes,
        'ausente': ausentes,
        'justificado': justificados,
        'presente_pct': porcentaje,
        # nombres alternativos
        'presentes': presentes,
        'ausentes': ausentes,
        'justificados': justificados,
        'porcentaje': porcentaje,
    })


# ─── DEBERES ──────────────────────────────────────────────────────────────────

@login_required
@student_required
def student_homework_view(request):
    """Vista para que los estudiantes vean sus deberes."""
    try:
        student = request.user.student_profile
    except AttributeError:
        messages.error(request, 'No se encontró tu perfil de estudiante')
        return redirect('users:login')

    usr = _usuario(student)

    # Deberes de clases en las que está inscrito (via Usuario)
    enrolled_class_ids = (
        Enrollment.objects.filter(estudiante=usr, estado='ACTIVO')
        .values_list('clase__id', flat=True)
        if usr else []
    )

    homework_clases = Deber.objects.filter(clase__id__in=enrolled_class_ids).distinct()
    homework_directo = (
        Deber.objects.filter(estudiantes_especificos=usr).distinct() if usr else Deber.objects.none()
    )
    all_homework = (homework_clases | homework_directo).order_by('-fecha_entrega')

    homework_with_status = []
    for hw in all_homework:
        submission = (
            DeberEntrega.objects.filter(deber=hw, estudiante=usr).first() if usr else None
        )
        homework_with_status.append({
            'homework': hw,
            'submission': submission,
            'is_submitted': submission is not None,
            'is_graded': submission and submission.calificacion is not None,
            'status': submission.get_estado_display() if submission else 'No entregado',
            'calificacion': submission.calificacion if submission else None,
        })

    return render(request, 'students/homework.html', {
        'student': student,
        'homework_list': homework_with_status,
    })


# ─── PERFIL ───────────────────────────────────────────────────────────────────

@student_required
def student_profile_view(request):
    """Perfil del estudiante."""
    student = request.user.student_profile
    usr = _usuario(student)

    if request.method == 'POST' and request.FILES.get('photo'):
        student.photo = request.FILES['photo']
        student.save()
        messages.success(request, 'Foto de perfil actualizada')
        return redirect('students:profile')

    total_clases = Activity.objects.filter(student=student).count()
    total_asistencias = (
        Asistencia.objects.filter(inscripcion__estudiante=usr).count() if usr else 0
    )
    promedio = CalificacionParcial.calcular_promedio_general(student)
    materias = student.get_subjects()

    clases_matriculadas = (
        Clase.objects.filter(enrollments__estudiante=usr, enrollments__estado='ACTIVO')
        if usr else Clase.objects.none()
    )

    return render(request, 'students/profile.html', {
        'student': student,
        'total_clases': total_clases,
        'total_asistencias': total_asistencias,
        'promedio': round(promedio, 2),
        'materias': materias,
        'clases_matriculadas': clases_matriculadas,
    })
