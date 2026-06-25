from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Avg, Count, Q

from users.models import Usuario
from teachers.models import Teacher
from students.models import Student
from classes.models import Clase, Enrollment, GradeLevel, CalificacionParcial, Asistencia, TipoAporte
from subjects.models import Subject


def _require_docente(request):
    """Returns (usuario, teacher) or None if not a teacher."""
    if not request.user.is_authenticated:
        return None, None
    usuario = getattr(request, 'usuario', None)
    if not usuario:
        try:
            usuario = request.user.usuario
        except Exception:
            return None, None
    teacher = getattr(usuario, 'teacher_profile', None)
    return usuario, teacher


def _docente_ctx(request, section, **extra):
    usuario, teacher = _require_docente(request)
    clases = Clase.objects.filter(
        docente_base=usuario, active=True
    ).select_related('subject', 'grade_level').order_by('subject__name', 'name')
    return {
        'section': section,
        'mi_usuario': usuario,
        'mi_teacher': teacher,
        'mis_clases': clases,
        **extra,
    }


# ─── Decorador ───────────────────────────────────────────────────────────────

def docente_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/users/login/?next={request.path}')
        usuario, teacher = _require_docente(request)
        if not usuario or not teacher:
            messages.error(request, 'Acceso solo para docentes registrados.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─── Dashboard ───────────────────────────────────────────────────────────────

@docente_required
def dashboard(request):
    usuario, teacher = _require_docente(request)
    clases = Clase.objects.filter(docente_base=usuario, active=True).select_related('subject', 'grade_level')

    # Stats por clase
    clases_info = []
    total_estudiantes = 0
    for c in clases:
        activos = c.enrollments.filter(estado='ACTIVO').count()
        total_estudiantes += activos
        # Asistencias hoy
        hoy = date.today()
        presentes_hoy = Asistencia.objects.filter(
            inscripcion__clase=c, fecha=hoy, estado='Presente'
        ).count()
        clases_info.append({
            'clase': c,
            'estudiantes': activos,
            'presentes_hoy': presentes_hoy,
        })

    ctx = _docente_ctx(request, 'dashboard',
        clases_info=clases_info,
        total_clases=len(clases_info),
        total_estudiantes=total_estudiantes,
        hoy=date.today(),
    )
    return render(request, 'docente/panel.html', ctx)


# ─── Detalle de clase ─────────────────────────────────────────────────────────

@docente_required
def clase_detail(request, pk):
    usuario, _ = _require_docente(request)
    clase = get_object_or_404(Clase, pk=pk, docente_base=usuario)
    enrollments = Enrollment.objects.filter(
        clase=clase, estado='ACTIVO'
    ).select_related('estudiante', 'estudiante__student_profile')

    ctx = _docente_ctx(request, 'clase',
        clase=clase,
        enrollments=enrollments,
        clase_pk=pk,
    )
    return render(request, 'docente/panel.html', ctx)


# ─── Calificaciones ───────────────────────────────────────────────────────────

@docente_required
def calificaciones(request, pk):
    usuario, teacher = _require_docente(request)
    clase = get_object_or_404(Clase, pk=pk, docente_base=usuario)

    quimestre = request.GET.get('q', 'Q1')
    parcial = request.GET.get('p', '1P')

    enrollments = Enrollment.objects.filter(
        clase=clase, estado='ACTIVO'
    ).select_related('estudiante', 'estudiante__student_profile').order_by('estudiante__nombre')

    tipos_aporte = TipoAporte.objects.filter(activo=True).order_by('orden', 'nombre')

    # Cargar notas existentes para este quimestre/parcial
    student_ids = [e.estudiante.student_profile.pk for e in enrollments
                   if hasattr(e.estudiante, 'student_profile')]

    califs_existentes = {}
    for cal in CalificacionParcial.objects.filter(
        student__in=student_ids,
        subject=clase.subject,
        quimestre=quimestre,
        parcial=parcial,
    ).select_related('student', 'tipo_aporte'):
        key = (cal.student.pk, cal.tipo_aporte.pk)
        califs_existentes[key] = cal

    if request.method == 'POST':
        with transaction.atomic():
            saved = 0
            for enr in enrollments:
                try:
                    student = enr.estudiante.student_profile
                except Exception:
                    continue
                for tipo in tipos_aporte:
                    field_name = f'nota_{student.pk}_{tipo.pk}'
                    val = request.POST.get(field_name, '').strip()
                    if val:
                        try:
                            nota = float(val.replace(',', '.'))
                            nota = max(0, min(10, nota))
                            cal, _ = CalificacionParcial.objects.update_or_create(
                                student=student,
                                subject=clase.subject,
                                quimestre=quimestre,
                                parcial=parcial,
                                tipo_aporte=tipo,
                                defaults={
                                    'calificacion': nota,
                                    'registrado_por': teacher,
                                }
                            )
                            saved += 1
                        except (ValueError, Exception):
                            pass
        messages.success(request, f'✓ {saved} calificaciones guardadas.')
        return redirect(f'/docente/clase/{pk}/calificaciones/?q={quimestre}&p={parcial}')

    ctx = _docente_ctx(request, 'calificaciones',
        clase=clase,
        clase_pk=pk,
        enrollments=enrollments,
        tipos_aporte=tipos_aporte,
        califs=califs_existentes,
        quimestre=quimestre,
        parcial=parcial,
        quimestre_choices=CalificacionParcial.QUIMESTRE_CHOICES,
        parcial_choices=CalificacionParcial.PARCIAL_CHOICES,
    )
    return render(request, 'docente/panel.html', ctx)


# ─── Asistencia ───────────────────────────────────────────────────────────────

@docente_required
def asistencia(request, pk):
    usuario, _ = _require_docente(request)
    clase = get_object_or_404(Clase, pk=pk, docente_base=usuario)

    fecha_str = request.GET.get('fecha', str(date.today()))
    try:
        fecha = date.fromisoformat(fecha_str)
    except ValueError:
        fecha = date.today()

    enrollments = Enrollment.objects.filter(
        clase=clase, estado='ACTIVO'
    ).select_related('estudiante').order_by('estudiante__nombre')

    asistencias_existentes = {
        a.inscripcion_id: a
        for a in Asistencia.objects.filter(
            inscripcion__in=enrollments,
            fecha=fecha,
        )
    }

    if request.method == 'POST':
        with transaction.atomic():
            for enr in enrollments:
                estado = request.POST.get(f'estado_{enr.pk}', 'Ausente')
                obs = request.POST.get(f'obs_{enr.pk}', '').strip()
                Asistencia.objects.update_or_create(
                    inscripcion=enr,
                    fecha=fecha,
                    defaults={'estado': estado, 'observacion': obs}
                )
        messages.success(request, f'✓ Asistencia del {fecha.strftime("%d/%m/%Y")} guardada.')
        return redirect(f'/docente/clase/{pk}/asistencia/?fecha={fecha}')

    # Últimas 7 fechas con asistencia registrada
    fechas_recientes = (
        Asistencia.objects.filter(inscripcion__clase=clase)
        .values_list('fecha', flat=True)
        .order_by('-fecha')
        .distinct()[:7]
    )

    ctx = _docente_ctx(request, 'asistencia',
        clase=clase,
        clase_pk=pk,
        enrollments=enrollments,
        asistencias=asistencias_existentes,
        fecha=fecha,
        fecha_str=str(fecha),
        fechas_recientes=fechas_recientes,
        estados=Asistencia.Estado.choices,
    )
    return render(request, 'docente/panel.html', ctx)


# ─── Mis estudiantes (resumen global) ────────────────────────────────────────

@docente_required
def mis_estudiantes(request):
    usuario, _ = _require_docente(request)
    enrollments = Enrollment.objects.filter(
        docente=usuario, estado='ACTIVO'
    ).select_related('estudiante', 'clase', 'clase__subject', 'clase__grade_level',
                     'estudiante__student_profile'
    ).order_by('clase__name', 'estudiante__nombre')

    ctx = _docente_ctx(request, 'estudiantes', enrollments=enrollments)
    return render(request, 'docente/panel.html', ctx)
