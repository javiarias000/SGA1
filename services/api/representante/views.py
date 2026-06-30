from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User

from students.models import Student
from users.models import Usuario
from classes.models import CalificacionParcial, Asistencia, Enrollment, Deber


def representante_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        try:
            u = request.user.usuario
            if u.rol not in ('REPRESENTANTE', ) and not request.user.is_staff:
                messages.error(request, 'Acceso solo para representantes.')
                return redirect('users:login')
        except Exception:
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _hijos(request):
    usuario = request.user.usuario
    return Student.objects.filter(representante_usuario=usuario, active=True).select_related('usuario', 'grade_level')


@representante_required
def rep_dashboard_view(request):
    hijos = _hijos(request)
    return render(request, 'representante/dashboard.html', {'hijos': hijos})


@representante_required
def rep_calificaciones_view(request, student_id):
    hijos = _hijos(request)
    student = get_object_or_404(hijos, pk=student_id)
    quimestre = request.GET.get('q', 'Q1')
    cals = (
        CalificacionParcial.objects.filter(student=student, quimestre=quimestre)
        .select_related('subject', 'tipo_aporte')
        .order_by('subject__name', 'parcial')
    )
    by_subject = {}
    for c in cals:
        by_subject.setdefault(c.subject.name, {})[c.parcial] = float(c.calificacion)
    return render(request, 'representante/calificaciones.html', {
        'student': student, 'by_subject': by_subject, 'quimestre': quimestre, 'hijos': hijos,
    })


@representante_required
def rep_asistencia_view(request, student_id):
    hijos = _hijos(request)
    student = get_object_or_404(hijos, pk=student_id)
    asistencias = (
        Asistencia.objects.filter(inscripcion__estudiante=student.usuario)
        .select_related('inscripcion__clase__subject')
        .order_by('-fecha')[:60]
    )
    total = asistencias.count()
    presentes = asistencias.filter(estado='PRESENTE').count()
    return render(request, 'representante/asistencia.html', {
        'student': student, 'asistencias': asistencias, 'total': total,
        'presentes': presentes, 'tasa': round(presentes / total * 100, 1) if total else 0,
        'hijos': hijos,
    })


@representante_required
def rep_deberes_view(request, student_id):
    hijos = _hijos(request)
    student = get_object_or_404(hijos, pk=student_id)
    deberes = (
        Deber.objects.filter(
            clase__enrollments__estudiante=student.usuario,
            clase__enrollments__estado='ACTIVO',
        )
        .select_related('clase__subject')
        .order_by('-fecha_entrega').distinct()[:30]
    )
    return render(request, 'representante/deberes.html', {
        'student': student, 'deberes': deberes, 'hijos': hijos,
    })


# ── Vista para que el docente vincule un representante ──────────────────────

@login_required
def vincular_representante_view(request, student_id):
    if not request.user.is_staff and not hasattr(request.user, 'teacher_profile'):
        return redirect('teachers:teacher_dashboard')
    student = get_object_or_404(Student, pk=student_id)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        nombre = student.parent_name or f"Representante de {student.name}"
        email = request.POST.get('email', student.parent_email).strip() or None

        if User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe.')
        else:
            auth_user = User.objects.create_user(username=username, password=password, email=email or '')
            usuario = Usuario.objects.create(
                nombre=nombre,
                rol=Usuario.Rol.REPRESENTANTE,
                email=email,
                phone=student.parent_phone or None,
            )
            usuario.auth_user = auth_user
            usuario.save()
            student.representante_usuario = usuario
            student.save()
            messages.success(request, f'Representante vinculado. Usuario: {username}')
        return redirect('teachers:student_detail', student_id=student.id)

    return render(request, 'representante/vincular_form.html', {'student': student})
